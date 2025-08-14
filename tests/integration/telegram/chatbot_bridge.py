"""
Telegram Bot Bridge for OneMinuta Chatbot Testing

Integrates the OneMinuta chatbot with Telegram for real-world testing
with actual users like @rezztelegram.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from telethon import TelegramClient, events
from telethon.tl.types import User

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.chatbot.chatbot_manager import OneMinutaChatbotManager


class TelegramChatbotBridge:
    """Bridge between Telegram and OneMinuta Chatbot for testing"""
    
    def __init__(self, api_id: str, api_hash: str, bot_token: str, 
                 storage_path: str, openai_api_key: str, authorized_users: list = None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.storage_path = Path(storage_path)
        self.authorized_users = authorized_users or []
        
        # Initialize Telegram client
        self.client = TelegramClient('chatbot_test_session', api_id, api_hash)
        
        # Initialize OneMinuta chatbot
        self.chatbot = OneMinutaChatbotManager(str(storage_path), openai_api_key)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Test session directory
        self.test_logs_dir = self.storage_path / "chatbot" / "test_logs"
        self.test_logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("TelegramChatbotBridge initialized")
    
    def setup_logging(self):
        """Setup detailed logging for testing"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.storage_path / "chatbot" / "telegram_bridge.log"),
                logging.StreamHandler()
            ]
        )
    
    async def start_bot(self):
        """Start the Telegram bot for testing"""
        self.logger.info("Starting Telegram Chatbot Bridge...")
        
        # Connect to Telegram
        await self.client.start(bot_token=self.bot_token)
        bot_info = await self.client.get_me()
        self.logger.info(f"Bot started: @{bot_info.username}")
        
        # Register event handlers
        self.register_handlers()
        
        # Send startup notification to authorized users
        await self.notify_authorized_users("🤖 OneMinuta Chatbot Test Bridge is now active!")
        
        self.logger.info("Bot is ready for testing. Send /start to begin.")
        
        # Keep running
        await self.client.run_until_disconnected()
    
    def register_handlers(self):
        """Register Telegram message handlers"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await self.handle_start_command(event)
        
        @self.client.on(events.NewMessage(pattern='/reset'))
        async def reset_handler(event):
            await self.handle_reset_command(event)
        
        @self.client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            await self.handle_stats_command(event)
        
        @self.client.on(events.NewMessage(pattern='/test'))
        async def test_handler(event):
            await self.handle_test_command(event)
        
        # Handle all other messages as chatbot input
        @self.client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            # Skip if it's a command we handle elsewhere
            if event.message.text and event.message.text.startswith('/'):
                return
            
            await self.handle_chatbot_message(event)
    
    async def handle_start_command(self, event):
        """Handle /start command"""
        user = await event.get_sender()
        user_id = self.get_user_identifier(user)
        
        if not self.is_authorized_user(user):
            await event.respond("❌ You are not authorized to use this test bot.")
            return
        
        self.logger.info(f"Start command from authorized user: {user_id}")
        
        welcome_msg = """🤖 OneMinuta Chatbot Test Bridge
        
Welcome to the OneMinuta property chatbot testing environment!

Available commands:
• Send any message to test the chatbot
• /reset - Reset your conversation
• /stats - View your session statistics  
• /test - Run automated test scenarios

The chatbot supports English and Russian languages and will guide you through finding properties.

Try saying: "I'm looking for a condo in Phuket" or "Привет, ищу квартиру"""
        
        await event.respond(welcome_msg)
        
        # Log test session start
        await self.log_test_session(user_id, "session_start", {"command": "/start"})
    
    async def handle_reset_command(self, event):
        """Handle /reset command"""
        user = await event.get_sender()
        user_id = self.get_user_identifier(user)
        
        if not self.is_authorized_user(user):
            return
        
        # Reset chatbot conversation
        success = await self.chatbot.reset_conversation(user_id)
        
        if success:
            await event.respond("🔄 Your conversation has been reset. You can start fresh!")
            await self.log_test_session(user_id, "conversation_reset", {"success": True})
        else:
            await event.respond("❌ Failed to reset conversation. Please try again.")
            await self.log_test_session(user_id, "conversation_reset", {"success": False})
    
    async def handle_stats_command(self, event):
        """Handle /stats command"""
        user = await event.get_sender()
        user_id = self.get_user_identifier(user)
        
        if not self.is_authorized_user(user):
            return
        
        # Get conversation summary
        summary = await self.chatbot.get_conversation_summary(user_id)
        
        if summary:
            stats_msg = f"""📊 Your Chatbot Session Statistics:

🎯 Current Stage: {summary['current_stage']}
📈 Progress: {summary['estimated_completion']:.1f}% complete
💬 Messages: {summary['message_count']}
📅 Last Active: {summary['last_active']}
⚡ Status: {summary['status']}

Data Completeness:"""
            
            if 'data_completeness' in summary:
                for category, data in summary['data_completeness'].items():
                    stats_msg += f"\n  • {category}: {data['percentage']:.1f}% ({data['filled']}/{data['total']})"
            
            await event.respond(stats_msg)
        else:
            await event.respond("📊 No active conversation found. Send a message to start!")
    
    async def handle_test_command(self, event):
        """Handle /test command - run automated test scenarios"""
        user = await event.get_sender()
        user_id = self.get_user_identifier(user)
        
        if not self.is_authorized_user(user):
            return
        
        await event.respond("🧪 Running automated test scenarios...")
        
        # Test scenarios
        test_scenarios = [
            "Hi, I'm looking for a condo in Phuket",
            "My budget is 30,000 THB per month for rent",
            "I need 2 bedrooms and prefer furnished"
        ]
        
        # Reset conversation first
        await self.chatbot.reset_conversation(user_id)
        
        results = []
        for i, test_message in enumerate(test_scenarios, 1):
            await event.respond(f"Test {i}: {test_message}")
            
            # Process through chatbot
            response = await self.chatbot.process_message(user_id, test_message)
            
            # Send bot response
            await event.respond(f"🤖: {response['reply']}")
            
            # Log test result
            test_result = {
                "stage": response['stage'],
                "next_stage": response.get('next_stage'),
                "confidence": response.get('confidence', 0),
                "data_collected": bool(response.get('data_collected')),
                "properties_found": len(response.get('properties_found', []))
            }
            results.append(test_result)
            
            await self.log_test_session(user_id, f"automated_test_{i}", {
                "input": test_message,
                "result": test_result
            })
        
        # Send test summary
        summary_msg = "🧪 Test Summary:\n"
        for i, result in enumerate(results, 1):
            summary_msg += f"\nTest {i}: {result['stage']} → {result.get('next_stage', 'same')}"
            summary_msg += f" (confidence: {result['confidence']:.2f})"
        
        await event.respond(summary_msg)
    
    async def handle_chatbot_message(self, event):
        """Handle regular messages through the chatbot"""
        user = await event.get_sender()
        user_id = self.get_user_identifier(user)
        message_text = event.message.text
        
        if not self.is_authorized_user(user):
            return
        
        if not message_text:
            return
        
        self.logger.info(f"Processing message from {user_id}: {message_text}")
        
        try:
            # Show typing indicator
            async with self.client.action(event.chat_id, 'typing'):
                # Process message through chatbot
                response = await self.chatbot.process_message(user_id, message_text, context={
                    "telegram_user_id": user.id,
                    "username": getattr(user, 'username', None),
                    "first_name": getattr(user, 'first_name', ''),
                    "message_id": event.message.id
                })
            
            # Send bot response
            await event.respond(response['reply'])
            
            # Log the interaction
            await self.log_test_session(user_id, "chatbot_interaction", {
                "user_message": message_text,
                "bot_reply": response['reply'],
                "stage": response['stage'],
                "next_stage": response.get('next_stage'),
                "confidence": response.get('confidence'),
                "data_collected": response.get('data_collected'),
                "properties_found": len(response.get('properties_found', [])),
                "session_complete": response.get('session_complete', False)
            })
            
            # If session complete, show summary
            if response.get('session_complete'):
                summary = await self.chatbot.get_conversation_summary(user_id)
                if summary:
                    completion_msg = f"""✅ Conversation Complete!
                    
📊 Summary:
• Total Messages: {summary['message_count']}
• Completion: {summary['estimated_completion']:.1f}%
• Properties Found: {len(response.get('properties_found', []))}

Type /reset to start a new conversation."""
                    await event.respond(completion_msg)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await event.respond("❌ Sorry, I encountered an error processing your message. Please try again.")
            
            await self.log_test_session(user_id, "error", {
                "user_message": message_text,
                "error": str(e)
            })
    
    def get_user_identifier(self, user: User) -> str:
        """Get consistent user identifier"""
        if user.username:
            return f"@{user.username}"
        return f"user_{user.id}"
    
    def is_authorized_user(self, user: User) -> bool:
        """Check if user is authorized for testing"""
        if not self.authorized_users:
            return True  # Allow all users if no restrictions
        
        user_identifier = self.get_user_identifier(user)
        return user_identifier in self.authorized_users
    
    async def log_test_session(self, user_id: str, event_type: str, data: Dict):
        """Log test session events for analysis"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "event_type": event_type,
            "data": data
        }
        
        # Write to daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.test_logs_dir / f"test_session_{today}.ndjson"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    async def notify_authorized_users(self, message: str):
        """Send notification to authorized users"""
        for username in self.authorized_users:
            if username.startswith('@'):
                try:
                    user = await self.client.get_entity(username)
                    await self.client.send_message(user, message)
                except Exception as e:
                    self.logger.error(f"Failed to notify {username}: {e}")


async def main():
    """Main entry point for Telegram bridge"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OneMinuta Telegram Chatbot Bridge")
    parser.add_argument("--api-id", required=True, help="Telegram API ID")
    parser.add_argument("--api-hash", required=True, help="Telegram API hash")
    parser.add_argument("--bot-token", required=True, help="Telegram bot token")
    parser.add_argument("--storage", default="./storage", help="Storage path")
    parser.add_argument("--openai-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--authorized-users", nargs='+', default=["@rezztelegram"], 
                       help="List of authorized usernames (default: @rezztelegram)")
    
    args = parser.parse_args()
    
    # Get OpenAI API key
    openai_key = args.openai_key or os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --openai-key")
        return
    
    # Create and start bridge
    bridge = TelegramChatbotBridge(
        api_id=args.api_id,
        api_hash=args.api_hash,
        bot_token=args.bot_token,
        storage_path=args.storage,
        openai_api_key=openai_key,
        authorized_users=args.authorized_users
    )
    
    try:
        await bridge.start_bot()
    except KeyboardInterrupt:
        print("\n👋 Telegram bridge stopped")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())