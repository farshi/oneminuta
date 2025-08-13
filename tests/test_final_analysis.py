#!/usr/bin/env python3
"""
Final test of the complete 5-day analysis system
Uses the channels we know have data
"""

import asyncio
import os
from datetime import datetime, timedelta
from services.analytics.telegram_monitor import TelegramPropertyMonitor

async def final_test():
    """Test the complete analysis pipeline"""
    
    print("🎯 FINAL 5-DAY ANALYSIS TEST")
    print("=" * 50)
    
    # Get credentials
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
    
    print(f"📊 Analyzing last 5 days from your channels...")
    
    total_messages = 0
    total_analyses = 0
    
    for channel in channels:
        print(f"\n🔍 {channel}:")
        
        try:
            # Analyze channel history
            await monitor.analyze_channel_history(channel, limit=20, days_back=5)
            
            # Get messages to count
            messages = await monitor.get_channel_history(channel, limit=20, days_back=5)
            total_messages += len(messages)
            
            if messages:
                print(f"   ✅ Analyzed {len(messages)} messages")
                total_analyses += len(messages)
                
                # Show sample
                sample = messages[0]
                content = sample['text'][:60] + "..." if len(sample['text']) > 60 else sample['text']
                print(f"   📝 Sample: {content}")
            else:
                print(f"   📭 No messages in last 5 days")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print(f"\n📊 ANALYSIS COMPLETE")
    print("=" * 30)
    print(f"   💬 Total messages: {total_messages}")
    print(f"   🔍 Messages analyzed: {total_analyses}")
    
    # Check for hot clients
    if total_analyses > 0:
        print(f"\n🔥 Checking for hot clients...")
        
        # Import and run CLI command programmatically
        from services.analytics.cli import list_hot_clients
        from argparse import Namespace
        
        args = Namespace(min_score=50.0, limit=10, verbose=True)
        await list_hot_clients(args)
        
    else:
        print(f"\n💡 No messages to analyze. This could mean:")
        print(f"   • Channels have no activity in last 5 days")
        print(f"   • Need to try longer period (--days-back 30)")
        print(f"   • May need authentication for full access")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(final_test())