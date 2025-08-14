#!/usr/bin/env python3
"""
One-time Telegram authentication setup
Run this once to authenticate, then you can use the monitoring commands
"""

import asyncio
import os
from pathlib import Path
from telethon import TelegramClient


async def authenticate():
    """Authenticate with Telegram for the first time"""
    
    # Get credentials from environment
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    print("🔐 OneMinuta Telegram Authentication")
    print("=" * 40)
    print("This is a one-time setup to authenticate with Telegram.")
    print("After this, you can use the analytics commands without re-authenticating.")
    print()
    
    # Create persistent session in sessions folder
    session_path = Path('sessions') / 'oneminuta_prod'
    session_path.parent.mkdir(exist_ok=True)
    client = TelegramClient(str(session_path), api_id, api_hash)
    
    try:
        print("📱 Starting authentication...")
        print("You will be asked for:")
        print("  1. Your phone number (international format, e.g., +1234567890)")
        print("  2. Verification code sent to your Telegram app")
        print()
        
        await client.start()
        
        print("✅ Authentication successful!")
        print("📁 Session saved as 'oneminuta_session.session'")
        print()
        print("🚀 Now you can run:")
        print("   python -m services.analytics.cli monitor --analyze-history --days-back 7")
        print("   python -m services.analytics.cli hot-clients")
        print()
        
        # Test channel access
        print("🔍 Testing access to your channels...")
        channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
        
        for channel in channels:
            try:
                entity = await client.get_entity(channel)
                if hasattr(entity, 'participants_count'):
                    member_count = entity.participants_count
                else:
                    member_count = "Unknown"
                
                print(f"   ✅ {channel} - {getattr(entity, 'title', 'No title')} ({member_count} members)")
            except Exception as e:
                print(f"   ⚠️  {channel} - {str(e)[:50]}...")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check your API credentials in .env file")
        print("   2. Make sure you have internet connection")
        print("   3. Use international phone format (+country_code + number)")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ Missing Telegram API credentials!")
        print("Please add TELEGRAM_API_ID and TELEGRAM_API_HASH to your .env file")
    else:
        asyncio.run(authenticate())