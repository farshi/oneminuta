#!/usr/bin/env python3
"""
OneMinuta Chatbot CLI

Command-line interface for testing and managing the smart chatbot system.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.chatbot.chatbot_manager import OneMinutaChatbotManager
from libs.config_loader import get_openai_api_key


async def interactive_chat_session(storage_path: str, openai_api_key: str):
    """Run an interactive chat session for testing"""
    
    print("🤖 OneMinuta Smart Chatbot - Interactive Test Session")
    print("=" * 60)
    print("Type 'quit' to exit, 'reset' to restart conversation")
    print()
    
    # Initialize chatbot
    chatbot = OneMinutaChatbotManager(storage_path, openai_api_key)
    
    # Get test user ID
    user_id = input("Enter test user ID (or press Enter for 'test_user'): ").strip()
    if not user_id:
        user_id = "test_user"
    
    print(f"Starting conversation with user: {user_id}")
    print("-" * 40)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{user_id}: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                await chatbot.reset_conversation(user_id)
                print("🔄 Conversation reset")
                continue
            
            # Process message through chatbot
            print("🤖 OneMinuta: ", end="", flush=True)
            response = await chatbot.process_message(user_id, user_input)
            
            # Print bot response
            print(response['reply'])
            
            # Show debug info if requested
            if os.getenv('CHATBOT_DEBUG', '').lower() == 'true':
                print(f"\n[DEBUG] Stage: {response['stage']} -> {response.get('next_stage', 'same')}")
                if response.get('data_collected'):
                    print(f"[DEBUG] Data collected: {json.dumps(response['data_collected'], indent=2)}")
                if response.get('properties_found'):
                    print(f"[DEBUG] Properties found: {len(response['properties_found'])}")
                print(f"[DEBUG] Confidence: {response.get('confidence', 0):.2f}")
            
            # Check if conversation is complete
            if response.get('session_complete'):
                print("\n✅ Conversation completed!")
                
                # Show summary
                summary = await chatbot.get_conversation_summary(user_id)
                if summary:
                    print(f"\n📊 Summary:")
                    print(f"   Messages exchanged: {summary['message_count']}")
                    print(f"   Completion: {summary['estimated_completion']:.1f}%")
                
                # Ask if user wants to continue
                continue_chat = input("\nStart a new conversation? (y/n): ").strip().lower()
                if continue_chat != 'y':
                    print("👋 Goodbye!")
                    break
                else:
                    await chatbot.reset_conversation(user_id)
                    print("🔄 Starting new conversation...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Type 'reset' to restart or 'quit' to exit")


async def batch_test_conversations(storage_path: str, openai_api_key: str):
    """Test chatbot with predefined conversation scenarios"""
    
    print("🧪 OneMinuta Chatbot - Batch Testing")
    print("=" * 50)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "English Buyer - Condo Search",
            "user_id": "test_buyer_en",
            "messages": [
                "Hi, I'm looking for a condo in Phuket",
                "I need 2 bedrooms and my budget is around 30,000 THB per month", 
                "I prefer something furnished in Rawai area"
            ]
        },
        {
            "name": "Russian Investor - Villa Purchase", 
            "user_id": "test_investor_ru",
            "messages": [
                "Привет, ищу виллу для инвестиций в Таиланде",
                "Бюджет до 10 миллионов батов, предпочитаю Пхукет",
                "Хочу купить, не арендовать"
            ]
        },
        {
            "name": "English Seller - House Listing",
            "user_id": "test_seller_en", 
            "messages": [
                "I want to sell my house in Bangkok",
                "It's a 3-bedroom townhouse, asking 8 million THB"
            ]
        }
    ]
    
    chatbot = OneMinutaChatbotManager(storage_path, openai_api_key)
    
    for scenario in test_scenarios:
        print(f"\n🎯 Testing: {scenario['name']}")
        print("-" * 40)
        
        user_id = scenario['user_id']
        
        # Reset conversation
        await chatbot.reset_conversation(user_id)
        
        for i, message in enumerate(scenario['messages'], 1):
            print(f"\nMessage {i}: {message}")
            
            response = await chatbot.process_message(user_id, message)
            
            print(f"Bot Reply: {response['reply']}")
            print(f"Stage: {response['stage']} -> {response.get('next_stage', 'same')}")
            
            # Show properties if found
            if response.get('properties_found'):
                print(f"Properties Found: {len(response['properties_found'])}")
        
        # Show final summary
        summary = await chatbot.get_conversation_summary(user_id)
        if summary:
            print(f"\n📊 Final Summary:")
            print(f"   Completion: {summary['estimated_completion']:.1f}%") 
            print(f"   Status: {summary['status']}")
    
    print(f"\n✅ Batch testing completed!")


async def show_session_stats(storage_path: str, openai_api_key: str):
    """Show chatbot session statistics"""
    
    print("📈 OneMinuta Chatbot - Session Statistics")
    print("=" * 50)
    
    chatbot = OneMinutaChatbotManager(storage_path, openai_api_key)
    
    # Get session statistics
    stats = await chatbot.session_manager.get_session_stats()
    
    if not stats:
        print("No session data available")
        return
    
    print(f"Total Sessions: {stats['total_sessions']}")
    print(f"Total Messages: {stats['total_messages']}") 
    print(f"Average Messages per Session: {stats['avg_messages']}")
    print()
    
    if stats['by_stage']:
        print("Sessions by Stage:")
        for stage, count in stats['by_stage'].items():
            print(f"  {stage}: {count}")
        print()
    
    if stats['by_status']:
        print("Sessions by Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")


async def cleanup_old_sessions(storage_path: str, days: int = 30):
    """Clean up old inactive sessions"""
    
    print(f"🧹 Cleaning up sessions inactive for {days}+ days...")
    
    from services.chatbot.session_manager import ChatbotSessionManager
    session_manager = ChatbotSessionManager(storage_path)
    
    cleaned_count = await session_manager.cleanup_inactive_sessions(days)
    print(f"✅ Cleaned up {cleaned_count} inactive sessions")


def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OneMinuta Chatbot CLI")
    parser.add_argument("--storage", default="./storage", help="Storage directory path")
    parser.add_argument("--openai-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Interactive chat command
    interactive_parser = subparsers.add_parser("chat", help="Start interactive chat session")
    
    # Batch test command
    test_parser = subparsers.add_parser("test", help="Run batch conversation tests")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show session statistics")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old sessions")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Days of inactivity before cleanup")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Get OpenAI API key
    openai_api_key = args.openai_key or get_openai_api_key(required=False)
    if not openai_api_key and args.command in ['chat', 'test']:
        print("❌ Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --openai-key")
        return
    
    # Run appropriate command
    try:
        if args.command == "chat":
            asyncio.run(interactive_chat_session(args.storage, openai_api_key))
        elif args.command == "test":
            asyncio.run(batch_test_conversations(args.storage, openai_api_key))
        elif args.command == "stats":
            asyncio.run(show_session_stats(args.storage, openai_api_key))
        elif args.command == "cleanup":
            asyncio.run(cleanup_old_sessions(args.storage, args.days))
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()