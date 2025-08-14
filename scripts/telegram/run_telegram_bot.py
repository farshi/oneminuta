#!/usr/bin/env python3
"""
Simple Telegram Bot for OneMinuta Chatbot Testing
Uses python-telegram-bot library for easier bot implementation
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError:
    print("❌ python-telegram-bot not installed. Installing now...")
    os.system("pip install python-telegram-bot")
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from services.chatbot.chatbot_manager import OneMinutaChatbotManager

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneMinutaTelegramBot:
    def __init__(self, token: str, openai_api_key: str, storage_path: str = "./storage"):
        self.token = token
        self.storage_path = storage_path
        
        # Initialize OneMinuta chatbot
        self.chatbot = OneMinutaChatbotManager(storage_path, openai_api_key)
        
        # Initialize Telegram bot
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Message handler for chatbot conversation
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """🏠 Welcome to OneMinuta Property Chatbot!

I'm here to help you find the perfect property in Thailand.

Available commands:
• /start - Start or restart the conversation
• /reset - Reset your conversation history
• /stats - View your session statistics
• /help - Show this help message

You can communicate in English or Russian. Try saying:
• "I'm looking for a condo in Phuket"
• "Привет, ищу квартиру в Бангкоке"
• "I need a 2-bedroom apartment under 30,000 THB"

Let's find your dream property! 🌴"""
        
        await update.message.reply_text(welcome_msg)
        
        # Reset conversation for clean start
        user_id = str(update.effective_user.id)
        await self.chatbot.reset_conversation(user_id)
        
        logger.info(f"User {update.effective_user.username or user_id} started conversation")
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command"""
        user_id = str(update.effective_user.id)
        success = await self.chatbot.reset_conversation(user_id)
        
        if success:
            await update.message.reply_text("🔄 Your conversation has been reset. You can start fresh!")
        else:
            await update.message.reply_text("❌ Failed to reset conversation. Please try again.")
        
        logger.info(f"User {update.effective_user.username or user_id} reset conversation")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = str(update.effective_user.id)
        stats = await self.chatbot.get_user_stats(user_id)
        
        if stats:
            stats_msg = f"""📊 Your OneMinuta Statistics:
            
🗣️ Messages: {stats.get('message_count', 0)}
📍 Current stage: {stats.get('current_stage', 'Not started')}
⏰ Session duration: {stats.get('session_duration', 'N/A')}
💾 Data collected: {len(stats.get('collected_data', {}))} items
📅 Last activity: {stats.get('last_activity', 'N/A')}"""
        else:
            stats_msg = "No conversation data found. Send a message to start chatting!"
        
        await update.message.reply_text(stats_msg)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """🤖 OneMinuta Chatbot Help

**How to use:**
1. Start with /start
2. Tell me what property you're looking for
3. I'll guide you through the process step by step

**Supported languages:** English, Russian

**Property types:** Condos, Villas, Houses, Apartments
**Locations:** Phuket, Bangkok, Pattaya, Koh Samui, and more
**Services:** Rent, Sale, Investment advice

**Commands:**
• /start - Begin conversation
• /reset - Clear conversation history  
• /stats - View your statistics
• /help - Show this message

**Example messages:**
• "Looking for a 2-bedroom condo in Phuket under 30,000 THB"
• "Ищу квартиру в Бангкоке для аренды"
• "I want to invest in Thai real estate"

Start chatting to find your perfect property! 🏡"""
        
        await update.message.reply_text(help_msg)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = str(update.effective_user.id)
        user_message = update.message.text
        username = update.effective_user.username or update.effective_user.first_name or user_id
        
        logger.info(f"Processing message from {username}: {user_message[:50]}...")
        
        try:
            # Send typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Process message through chatbot
            result = await self.chatbot.process_message(user_id, user_message)
            
            # Send response
            if result and result.get('reply'):
                await update.message.reply_text(result['reply'])
                
                # Log successful interaction
                logger.info(f"Response sent to {username}: {result['reply'][:50]}...")
                
                # If conversation is complete, show summary
                if result.get('session_complete'):
                    completion_msg = """✅ Property search completed!
                    
Thank you for using OneMinuta. Your requirements have been collected and our team will be in touch soon.

Use /start to begin a new search or /stats to view your session details."""
                    await update.message.reply_text(completion_msg)
            else:
                # Fallback response
                await update.message.reply_text(
                    "I apologize, but I couldn't process your request right now. Please try again or use /reset to start over."
                )
                
        except Exception as e:
            logger.error(f"Error processing message from {username}: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your message. Please try again later or contact support."
            )
    
    async def start_bot(self):
        """Start the bot"""
        logger.info("🤖 Starting OneMinuta Telegram Bot...")
        logger.info(f"Bot token: {self.token[:10]}...")
        logger.info(f"Storage path: {self.storage_path}")
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("✅ Bot started successfully! Send /start to @OneMinutaBot to test")
        logger.info("Press Ctrl+C to stop the bot")
        
        # Keep running until interrupted
        import signal
        
        def signal_handler(sig, frame):
            logger.info("Received interrupt signal, stopping bot...")
            
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Keep the application running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    
    async def stop_bot(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        await self.application.stop()

async def main():
    """Main function"""
    # Check environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    storage_path = os.getenv('STORAGE_PATH', './storage')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print(f"🤖 OneMinuta Telegram Bot Starting...")
    print(f"📁 Storage: {storage_path}")
    print(f"🔑 OpenAI Model: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    print("=" * 50)
    
    # Create and start bot
    bot = OneMinutaTelegramBot(bot_token, openai_key, storage_path)
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        await bot.stop_bot()
        print("✅ Bot stopped successfully")

if __name__ == "__main__":
    asyncio.run(main())