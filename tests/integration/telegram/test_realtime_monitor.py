#!/usr/bin/env python3
"""
Test real-time Telegram monitoring
Monitors channels for new messages and analyzes them in real-time
"""

import asyncio
import os
import sys
from datetime import datetime
from services.analytics.telegram_monitor import TelegramPropertyMonitor
from services.analytics.config import AnalyticsConfig

async def start_realtime_monitor():
    """Start real-time monitoring of configured channels"""
    
    print("🚀 STARTING REAL-TIME MONITOR")
    print("=" * 50)
    
    # Get credentials
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    # Clear any existing session locks
    session_file = 'oneminuta_session.session'
    if os.path.exists(session_file):
        print(f"⚠️  Removing existing session file to avoid locks...")
        try:
            os.remove(session_file)
        except:
            pass
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    # Use channels from config
    channels = AnalyticsConfig.DEFAULT_CHANNELS
    print(f"📱 Monitoring channels: {', '.join(channels)}")
    print()
    
    # Add channels to monitor
    for channel in channels:
        monitor.add_channel(channel)
        print(f"✅ Added {channel} to monitoring list")
    
    print("\n📡 Starting real-time monitoring...")
    print("Press Ctrl+C to stop\n")
    print("-" * 50)
    
    try:
        # Create monitoring task
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        # Keep alive and show status
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            # Show heartbeat
            now = datetime.now().strftime("%H:%M:%S")
            print(f"💓 [{now}] Monitor active - watching for new messages...")
            
            # Check for hot clients periodically
            from services.analytics.client_analyzer import PropertyClientAnalyzer
            analyzer = PropertyClientAnalyzer('./storage')
            hot_clients = await analyzer.get_hot_clients(min_score=70.0, limit=3)
            
            if hot_clients:
                print(f"🔥 Current hot clients: {len(hot_clients)}")
                for client in hot_clients[:3]:
                    print(f"   • {client.user_id}: Score {client.total_score:.0f}")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping monitor...")
        monitor.stop_monitoring()
        await asyncio.sleep(1)
        print("✅ Monitor stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        monitor.stop_monitoring()

async def test_with_sample_message():
    """Test monitor with a sample message first"""
    
    print("🧪 TESTING MONITOR WITH SAMPLE")
    print("=" * 40)
    
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    # Test analyzing a recent message first
    channels = AnalyticsConfig.DEFAULT_CHANNELS
    
    for channel in channels[:1]:  # Test with first channel
        print(f"\n📱 Testing with {channel}...")
        
        try:
            # Get one recent message
            messages = await monitor.get_channel_history(channel, limit=1)
            
            if messages:
                msg = messages[0]
                print(f"✅ Got message from {msg['user_id']}")
                print(f"   Date: {msg['date']}")
                print(f"   Text: {msg['text'][:100]}...")
                
                # Now try real-time monitoring
                print(f"\n🚀 Starting real-time monitor for {channel}...")
                monitor.add_channel(channel)
                
                # Run for 60 seconds as test
                monitor_task = asyncio.create_task(monitor.start_monitoring())
                await asyncio.sleep(60)
                
                print("✅ Test completed successfully!")
                monitor.stop_monitoring()
                
            else:
                print("⚠️  No recent messages found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        asyncio.run(test_with_sample_message())
    else:
        asyncio.run(start_realtime_monitor())