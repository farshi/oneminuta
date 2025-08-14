#!/usr/bin/env python3
"""
Test script to demonstrate 5-day historical analysis
Shows how the system can analyze messages from the last 5 days
"""

import asyncio
import os
from datetime import datetime, timedelta
from services.analytics.telegram_monitor import TelegramPropertyMonitor


async def test_5day_analysis():
    """Test analyzing messages from the last 5 days"""
    
    print("📅 TESTING 5-DAY HISTORICAL ANALYSIS")
    print("=" * 50)
    
    # Get credentials
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ Missing Telegram API credentials in .env")
        return
    
    # Initialize monitor
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    # Your configured channels
    channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
    
    print(f"🎯 Analyzing your channels for last 5 days:")
    for channel in channels:
        print(f"   {channel}")
    
    cutoff_date = datetime.utcnow() - timedelta(days=5)
    print(f"📅 Date range: {cutoff_date.strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')}")
    
    try:
        print(f"\n🔍 Starting analysis...")
        
        total_messages = 0
        total_users = set()
        
        for channel in channels:
            print(f"\n📊 Analyzing {channel}...")
            
            # Get messages from last 5 days
            messages = await monitor.get_channel_history(
                channel=channel, 
                limit=2000,  # Max messages to check
                days_back=5  # Last 5 days
            )
            
            if messages:
                print(f"   ✅ Found {len(messages)} messages from last 5 days")
                total_messages += len(messages)
                
                # Count unique users
                channel_users = set(msg['user_id'] for msg in messages)
                total_users.update(channel_users)
                print(f"   👥 {len(channel_users)} unique users")
                
                # Show sample messages (first 3)
                print(f"   📝 Sample messages:")
                for i, msg in enumerate(messages[:3], 1):
                    date_str = msg['date'].strftime('%Y-%m-%d %H:%M') if msg['date'] else 'Unknown'
                    handle = msg['handle'] or f"user_{msg['user_id'][-6:]}"
                    content = msg['text'][:60] + "..." if len(msg['text']) > 60 else msg['text']
                    print(f"      {i}. [{date_str}] {handle}: {content}")
                
                # Analyze a few messages for hot clients
                print(f"   🔥 Analyzing for hot clients...")
                
                await monitor.analyze_channel_history(
                    channel=channel,
                    limit=min(500, len(messages)),  # Analyze up to 500 messages
                    days_back=5
                )
                
            else:
                print(f"   ⚠️  No messages found (channel may be private or not accessible)")
        
        print(f"\n📊 ANALYSIS SUMMARY")
        print("=" * 30)
        print(f"   📅 Period: Last 5 days")
        print(f"   💬 Total messages: {total_messages}")
        print(f"   👥 Unique users: {len(total_users)}")
        print(f"   📱 Channels analyzed: {len(channels)}")
        
        if total_messages > 0:
            print(f"\n🚀 Hot clients analysis completed!")
            print(f"   📊 Check results with: python -m services.analytics.cli hot-clients")
            print(f"   📈 Generate report with: python -m services.analytics.cli report")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print(f"\n💡 This might be because:")
        print(f"   1. You need to authenticate first (interactive mode required)")
        print(f"   2. Channels are private and bot doesn't have access")
        print(f"   3. API credentials are incorrect")
        
        print(f"\n🔧 To authenticate:")
        print(f"   1. Run in terminal: python test_telegram_channels.py")
        print(f"   2. Enter your phone number when prompted")
        print(f"   3. Enter verification code from Telegram")
        print(f"   4. Run this script again")


def show_usage_examples():
    """Show how to use the 5-day analysis feature"""
    print(f"\n📚 USAGE EXAMPLES")
    print("=" * 30)
    
    print(f"🔍 Analyze last 5 days:")
    print(f"   python -m services.analytics.cli monitor --analyze-history --days-back 5")
    
    print(f"\n🔍 Analyze last 7 days:")
    print(f"   python -m services.analytics.cli monitor --analyze-history --days-back 7")
    
    print(f"\n🔍 Analyze last 1000 messages (no date limit):")
    print(f"   python -m services.analytics.cli monitor --analyze-history --history-limit 1000")
    
    print(f"\n🔍 Analyze last 3 days with 500 message limit:")
    print(f"   python -m services.analytics.cli monitor --analyze-history --days-back 3 --history-limit 500")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_usage_examples()
    else:
        asyncio.run(test_5day_analysis())