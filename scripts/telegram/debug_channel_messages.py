#!/usr/bin/env python3
"""
Debug channel messages to see what's being filtered
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def debug_messages():
    """Debug what messages are in the channel"""
    
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    # Use the existing authenticated session
    session_path = Path('sessions') / 'oneminuta_prod'
    if not session_path.parent.exists():
        # Try from parent directory if running from scripts/
        session_path = Path('..') / 'sessions' / 'oneminuta_prod'
    
    client = TelegramClient(str(session_path), api_id, api_hash)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Not authorized! Run: ./telegram_analytics auth")
            return
    except Exception as e:
        print(f"❌ Session error: {e}")
        return
    
    channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
    
    for channel in channels:
        print(f"\n{'='*60}")
        print(f"📱 CHANNEL: {channel}")
        print(f"{'='*60}")
        
        try:
            entity = await client.get_entity(channel)
            
            # Get last 10 messages without any filtering
            print(f"\n📊 Last 10 messages (NO FILTERING):")
            print("-" * 40)
            
            count = 0
            owner_count = 0
            member_count = 0
            
            async for message in client.iter_messages(entity, limit=10):
                if message.text:
                    count += 1
                    
                    # Get sender info
                    sender_name = "Unknown"
                    if message.sender:
                        if hasattr(message.sender, 'username'):
                            sender_name = f"@{message.sender.username}" if message.sender.username else f"ID:{message.sender.id}"
                        else:
                            sender_name = f"ID:{message.sender.id}"
                    
                    # Check if it would be filtered
                    from services.analytics.telegram_monitor import TelegramPropertyMonitor
                    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
                    is_owner = monitor.is_likely_owner_message(message.text)
                    
                    # Display message info
                    date_str = message.date.strftime('%Y-%m-%d %H:%M') if message.date else 'Unknown'
                    text_preview = message.text[:100].replace('\n', ' ')
                    if len(message.text) > 100:
                        text_preview += "..."
                    
                    status = "🏢 OWNER/LISTING" if is_owner else "👤 MEMBER"
                    
                    if is_owner:
                        owner_count += 1
                    else:
                        member_count += 1
                    
                    print(f"\nMessage #{count}:")
                    print(f"  Status: {status}")
                    print(f"  From: {sender_name}")
                    print(f"  Date: {date_str}")
                    print(f"  Length: {len(message.text)} chars")
                    print(f"  Text: {text_preview}")
                    
                    # Show why it was filtered (if owner)
                    if is_owner:
                        text_lower = message.text.lower()
                        reasons = []
                        
                        if '#' in message.text:
                            reasons.append("Has hashtags")
                        if any(link in text_lower for link in ['http', 'youtube', 'vk.com']):
                            reasons.append("Contains links")
                        if any(fmt in message.text for fmt in ['**', '✅', '➡️', '✔️']):
                            reasons.append("Has formatting")
                        if any(word in text_lower for word in ['подписывайтесь', 'subscribe', 'смотрим']):
                            reasons.append("Promotional language")
                        if len(message.text) > 200:
                            listing_words = ['for sale', 'for rent', 'price:', 'bedroom', 'bathroom']
                            if sum(1 for word in listing_words if word in text_lower) >= 2:
                                reasons.append("Multiple listing indicators")
                        
                        if reasons:
                            print(f"  ❌ Filtered because: {', '.join(reasons)}")
            
            print(f"\n📊 SUMMARY for {channel}:")
            print(f"  Total messages checked: {count}")
            print(f"  🏢 Owner/Listing messages: {owner_count}")
            print(f"  👤 Member messages: {member_count}")
            
            if member_count == 0:
                print(f"\n💡 No member messages found. Possible reasons:")
                print(f"  • All recent messages are from channel owner")
                print(f"  • Channel has no recent member activity")
                print(f"  • Filter might be too aggressive")
            
        except Exception as e:
            print(f"❌ Error accessing {channel}: {e}")
    
    await client.disconnect()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(debug_messages())