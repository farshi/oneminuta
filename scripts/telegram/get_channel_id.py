#!/usr/bin/env python3
"""
Get Channel ID for OneMinuta Property Channel
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

try:
    from telegram import Bot
except ImportError:
    os.system("pip install python-telegram-bot")
    from telegram import Bot

async def get_channel_info():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        return
    
    bot = Bot(token=bot_token)
    
    print("🔍 Getting channel information...")
    print("=" * 50)
    
    try:
        # Get recent updates to find channel messages
        updates = await bot.get_updates(limit=100)
        
        channels_found = set()
        
        for update in updates:
            if update.message and update.message.chat:
                chat = update.message.chat
                if chat.type in ['channel', 'supergroup']:
                    channels_found.add((chat.id, chat.title or chat.username or "Unknown"))
        
        if channels_found:
            print("📢 Found these channels/groups:")
            for channel_id, channel_name in channels_found:
                print(f"   ID: {channel_id}")
                print(f"   Name: {channel_name}")
                print("-" * 30)
        else:
            print("❌ No channel activity found in recent updates")
            print("\n💡 To get your channel ID:")
            print("1. Send a message in @oneminuta_property channel")
            print("2. Run this script again")
            print("3. Or forward any channel message to @userinfobot")
            
        # Try to get info about the specific channel
        try:
            # This might work if bot has been added to channel
            chat_info = await bot.get_chat("@oneminuta_property")
            print(f"\n✅ Direct channel info:")
            print(f"   ID: {chat_info.id}")
            print(f"   Title: {chat_info.title}")
            print(f"   Username: @{chat_info.username}")
            print(f"   Type: {chat_info.type}")
            
            return chat_info.id
            
        except Exception as e:
            print(f"\n⚠️ Could not get direct channel info: {e}")
            print("This is normal if bot hasn't posted in channel yet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🤖 Alternative method:")
    print(f"1. Post a message in @oneminuta_property channel")
    print(f"2. Forward that message to @userinfobot") 
    print(f"3. It will show you the channel ID")

if __name__ == "__main__":
    asyncio.run(get_channel_info())