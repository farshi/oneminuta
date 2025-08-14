#!/usr/bin/env python3
"""
One-time Telegram authentication for production
Run this once to create a persistent session
"""

import asyncio
import os
import sys
from services.analytics.session_manager import TelegramSessionManager

async def authenticate():
    """Perform one-time authentication"""
    
    print("🔐 TELEGRAM AUTHENTICATION SETUP")
    print("=" * 50)
    print("\nThis will create a persistent session for your Telegram account.")
    print("You only need to do this ONCE.\n")
    
    # Get API credentials
    api_id = int(os.getenv('TELEGRAM_API_ID', 0))
    api_hash = os.getenv('TELEGRAM_API_HASH', '')
    
    if not api_id or not api_hash:
        print("❌ Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env file")
        return False
    
    print(f"📱 Using API ID: {api_id}")
    print(f"🔑 API Hash: {api_hash[:10]}...")
    print()
    
    # Create session manager
    manager = TelegramSessionManager(api_id, api_hash)
    
    # Check if already authenticated
    try:
        client = await manager.get_client()
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Already authenticated as: {me.first_name} (@{me.username})")
            print(f"📁 Session file: {manager.session_name}.session")
            print("\nNo need to authenticate again!")
            await manager.disconnect()
            return True
    except:
        pass
    
    # Perform authentication
    print("📲 Starting authentication process...")
    print("You will receive a verification code on your Telegram app.\n")
    
    success = await manager.authenticate_interactive()
    
    if success:
        print("\n✅ Authentication successful!")
        print("You can now run the monitoring scripts without authentication prompts.")
        print("\nNext steps:")
        print("1. Run: python analyze_channels_only.py")
        print("2. Or: python test_realtime_monitor.py")
    else:
        print("\n❌ Authentication failed. Please try again.")
    
    await manager.disconnect()
    return success

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(authenticate())
    sys.exit(0 if success else 1)