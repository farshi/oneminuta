#!/usr/bin/env python3
"""
Debug Telegram connection issues
"""

import asyncio
import os
from services.analytics.telegram_monitor import TelegramPropertyMonitor

async def debug_telegram():
    """Debug telegram connection"""
    
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    print(f"🔑 API ID: {api_id}")
    print(f"🔑 API Hash: {api_hash[:10]}...")
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    print("✅ Monitor created")
    
    # Test get_channel_history directly
    try:
        print("🔍 Testing channel history...")
        messages = await monitor.get_channel_history('@phuketgidsell', limit=5, days_back=5)
        print(f"📊 Got {len(messages)} messages")
        
        if messages:
            for msg in messages[:2]:
                print(f"   📝 {msg['user_id']}: {msg['text'][:50]}...")
        else:
            print("   ⚠️  No messages returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(debug_telegram())