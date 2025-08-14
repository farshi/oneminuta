#!/usr/bin/env python3
"""
Test script to check what property channels are available for monitoring
"""

import asyncio
import sys
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError


async def test_channels():
    """Test which property channels are accessible"""
    
    # Get credentials from environment
    import os
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Test channels to check
    test_channels = [
        '@thailand_property',
        '@phuket_property', 
        '@bangkok_real_estate',
        '@pattaya_condos',
        '@property_thailand',
        '@thai_property',
        '@realestate_thailand',
        '@bangkok_property',
        '@phuket_condos',
        '@property_th'
    ]
    
    print("🔍 Testing Property Channel Availability")
    print("=" * 50)
    
    # Create Telegram client
    client = TelegramClient('test_session', api_id, api_hash)
    
    try:
        print("📱 Connecting to Telegram...")
        await client.start()
        print("✅ Connected successfully!")
        
        accessible_channels = []
        
        for channel in test_channels:
            try:
                print(f"\n🔍 Testing {channel}...")
                entity = await client.get_entity(channel)
                
                # Get basic info
                if hasattr(entity, 'participants_count'):
                    member_count = entity.participants_count
                else:
                    member_count = "Unknown"
                
                if hasattr(entity, 'title'):
                    title = entity.title
                else:
                    title = "No title"
                
                print(f"✅ {channel} - '{title}' ({member_count} members)")
                accessible_channels.append({
                    'username': channel,
                    'title': title,
                    'members': member_count
                })
                
                # Try to get a few recent messages
                messages = []
                async for message in client.iter_messages(entity, limit=3):
                    if message.text:
                        messages.append(message.text[:100] + "...")
                
                if messages:
                    print(f"   📝 Recent messages:")
                    for i, msg in enumerate(messages, 1):
                        print(f"      {i}. {msg}")
                else:
                    print(f"   📝 No recent text messages found")
                    
            except UsernameNotOccupiedError:
                print(f"❌ {channel} - Channel does not exist")
            except UsernameInvalidError:
                print(f"❌ {channel} - Invalid username format")
            except Exception as e:
                print(f"⚠️  {channel} - Error: {str(e)[:50]}...")
        
        print(f"\n📊 SUMMARY")
        print("=" * 30)
        print(f"✅ Accessible channels: {len(accessible_channels)}")
        
        if accessible_channels:
            print("\n🎯 RECOMMENDED CHANNELS FOR MONITORING:")
            for channel in accessible_channels:
                print(f"   {channel['username']} - {channel['title']}")
            
            print(f"\n🚀 TO START MONITORING:")
            print(f"   python -m services.analytics.cli monitor --analyze-history")
        else:
            print("\n💡 TRY THESE POPULAR CHANNELS:")
            print("   1. Search for 'thailand property' in Telegram")
            print("   2. Join some public property channels")
            print("   3. Use channel usernames starting with @")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Check your API credentials in .env")
        print("   2. Make sure you have internet connection")
        print("   3. Try running the script again")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_channels())