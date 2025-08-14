#!/usr/bin/env python3
"""
Test if we can access the configured channels
"""

import asyncio
import os
from services.analytics.telegram_monitor import TelegramPropertyMonitor

async def test_channels():
    """Test access to configured channels"""
    
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    # Your configured channels
    channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
    
    print("🔍 Testing Channel Access")
    print("=" * 40)
    
    for channel in channels:
        print(f"\n📱 Testing {channel}...")
        
        try:
            # Test without date filtering first
            messages = await monitor.get_channel_history(channel, limit=10)
            print(f"   ✅ Accessible - found {len(messages)} recent messages")
            
            if messages:
                # Show sample message
                sample = messages[0]
                date_str = sample['date'].strftime('%Y-%m-%d %H:%M') if sample['date'] else 'Unknown'
                print(f"   📝 Latest: [{date_str}] {sample['text'][:60]}...")
                
                # Test with 5-day filter
                recent_messages = await monitor.get_channel_history(channel, limit=100, days_back=5)
                print(f"   📅 Last 5 days: {len(recent_messages)} messages")
                
            else:
                print(f"   ⚠️  No messages found (might be empty or private)")
                
        except Exception as e:
            error_msg = str(e)
            if "No such peer" in error_msg or "USERNAME_NOT_OCCUPIED" in error_msg:
                print(f"   ❌ Channel doesn't exist: {channel}")
            elif "CHANNEL_PRIVATE" in error_msg:
                print(f"   🔒 Channel is private: {channel}")
            elif "AUTH_KEY_UNREGISTERED" in error_msg:
                print(f"   🔐 Authentication required")
            else:
                print(f"   ❌ Error: {error_msg}")
    
    print(f"\n💡 Solutions:")
    print(f"   • If channels don't exist: Update channel names in config.py")
    print(f"   • If private: Join channels first or use public channels")
    print(f"   • If auth required: Run 'python authenticate_telegram.py'")
    print(f"   • If no recent activity: Try longer time period (--days-back 30)")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_channels())