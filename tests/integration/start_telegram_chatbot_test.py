#!/usr/bin/env python3
"""
Quick setup script for Telegram chatbot testing with @rezztelegram
Loads configuration from .env file
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    print("🤖 OneMinuta Telegram Chatbot Test Setup")
    print("=" * 50)
    
    # Check environment variables (now loaded from .env)
    required_env = {
        'TELEGRAM_API_ID': 'Telegram API ID',
        'TELEGRAM_API_HASH': 'Telegram API Hash', 
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'OPENAI_API_KEY': 'OpenAI API Key'
    }
    
    missing_env = []
    for env_var, description in required_env.items():
        value = os.getenv(env_var)
        if not value:
            missing_env.append(f"  {env_var} - {description}")
    
    if missing_env:
        print("❌ Missing required environment variables:")
        for var in missing_env:
            print(var)
        print("\nPlease add these to your .env file and try again.")
        print("\nExample .env entries:")
        print("TELEGRAM_API_ID=your_api_id")
        print("TELEGRAM_API_HASH=your_api_hash") 
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("OPENAI_API_KEY=your_openai_key")
        return False
    
    print("✅ All environment variables loaded from .env")
    
    # Check if we can import required modules
    try:
        import telethon
        print("✅ Telethon library available")
    except ImportError:
        print("❌ Telethon not installed. Run: pip install telethon")
        return False
    
    try:
        import openai
        print("✅ OpenAI library available")
    except ImportError:
        print("❌ OpenAI not installed. Run: pip install openai")
        return False
    
    # Show configuration (partially masked for security)
    print(f"\n📋 Configuration:")
    print(f"  API ID: {os.getenv('TELEGRAM_API_ID')}")
    print(f"  API Hash: {os.getenv('TELEGRAM_API_HASH')[:10]}...")
    print(f"  Bot Token: {os.getenv('TELEGRAM_BOT_TOKEN')[:20]}...")
    print(f"  OpenAI Key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print(f"  Authorized User: @rezztelegram")
    print(f"  Storage Path: {os.getenv('STORAGE_PATH', './storage')}")
    
    # Start the bot
    print(f"\n🚀 Starting Telegram Chatbot Bridge...")
    print(f"Send /start to the bot from @rezztelegram to begin testing")
    
    # Import and run the bridge
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    try:
        import asyncio
        from tests.integration.telegram.chatbot_bridge import TelegramChatbotBridge
        
        bridge = TelegramChatbotBridge(
            api_id=os.getenv('TELEGRAM_API_ID'),
            api_hash=os.getenv('TELEGRAM_API_HASH'),
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            storage_path=os.getenv('STORAGE_PATH', './storage'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            authorized_users=["@rezztelegram"]
        )
        
        asyncio.run(bridge.start_bot())
        
    except KeyboardInterrupt:
        print("\n👋 Chatbot bridge stopped")
        return True
    except Exception as e:
        print(f"❌ Error starting bridge: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)