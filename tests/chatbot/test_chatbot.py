#!/usr/bin/env python3
"""
Quick test for OneMinuta Smart Chatbot
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project to path
# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_chatbot():
    """Test chatbot with sample conversation"""
    
    # Check if OpenAI key is available
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        from services.chatbot.chatbot_manager import OneMinutaChatbotManager
        
        print("🧪 Testing OneMinuta Smart Chatbot")
        print("=" * 50)
        
        # Initialize chatbot
        storage_path = "./storage"
        chatbot = OneMinutaChatbotManager(storage_path, openai_key)
        
        # Test conversation
        test_user = "test_user_001"
        test_messages = [
            "Hi, I'm looking for a condo in Phuket",
            "I need 2 bedrooms and my budget is 30,000 THB per month",
            "Preferably something furnished near the beach"
        ]
        
        print(f"Testing with user: {test_user}")
        print("-" * 30)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\nMessage {i}: {message}")
            
            response = await chatbot.process_message(test_user, message)
            
            print(f"Bot Reply: {response['reply']}")
            print(f"Stage: {response['stage']} -> {response.get('next_stage', 'same')}")
            print(f"Confidence: {response.get('confidence', 0):.2f}")
            
            if response.get('properties_found'):
                print(f"Properties found: {len(response['properties_found'])}")
            
            if response.get('session_complete'):
                print("\n✅ Conversation completed!")
                break
        
        # Show final summary
        summary = await chatbot.get_conversation_summary(test_user)
        if summary:
            print(f"\n📊 Final Summary:")
            print(f"   Completion: {summary['estimated_completion']:.1f}%")
            print(f"   Status: {summary['status']}")
            print(f"   Messages: {summary['message_count']}")
        
        print("\n✅ Chatbot test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Install dependencies: pip install openai")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_chatbot())
    sys.exit(0 if success else 1)