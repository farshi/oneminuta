#!/usr/bin/env python3
"""
Analyze channels without starting real-time monitoring
Avoids database lock issues by only doing historical analysis
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics.telegram_monitor import TelegramPropertyMonitor

async def analyze_channels_historical(days_back: int = 3):
    """Analyze channel history without real-time monitoring"""
    
    print(f"🔍 HISTORICAL ANALYSIS ({days_back} days)")
    print("=" * 50)
    
    # Get credentials
    api_id = int(os.getenv('TELEGRAM_API_ID', '26818131'))
    api_hash = os.getenv('TELEGRAM_API_HASH', '85b2edabf016108450eb958ac80fa2d7')
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, './storage')
    
    channels = ['@phuketgidsell', '@phuketgid', '@sabay_property']
    
    print(f"📊 Analyzing last {days_back} days from channels...")
    
    total_messages = 0
    total_analyses = 0
    
    for channel in channels:
        print(f"\n🔍 {channel}:")
        
        try:
            # Get messages first to count
            messages = await monitor.get_channel_history(channel, limit=50, days_back=days_back)
            
            if messages:
                print(f"   📱 Found {len(messages)} messages from last {days_back} days")
                total_messages += len(messages)
                
                # Analyze channel history
                await monitor.analyze_channel_history(channel, limit=50, days_back=days_back)
                total_analyses += len(messages)
                
                # Show sample
                sample = messages[0]
                content = sample['text'][:60] + "..." if len(sample['text']) > 60 else sample['text']
                date_str = sample['date'].strftime('%Y-%m-%d %H:%M') if sample['date'] else 'Unknown'
                print(f"   📝 Latest: [{date_str}] {content}")
                
            else:
                print(f"   📭 No messages in last {days_back} days")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:80]}...")
    
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
        
        # Generate summary report
        print(f"\n📈 Generating summary report...")
        from services.analytics.client_analyzer import PropertyClientAnalyzer
        analyzer = PropertyClientAnalyzer('./storage')
        
        # Get all hot clients for summary
        hot_clients = await analyzer.get_hot_clients(min_score=50.0)
        
        if hot_clients:
            print(f"\n🌟 SUMMARY")
            print("=" * 20)
            print(f"Hot clients found: {len(hot_clients)}")
            
            # Group by hotness level
            burning = [c for c in hot_clients if c.total_score >= 86]
            hot = [c for c in hot_clients if 61 <= c.total_score < 86]
            warm = [c for c in hot_clients if 31 <= c.total_score < 61]
            
            if burning:
                print(f"🔥 Burning (86-100): {len(burning)} clients")
            if hot:
                print(f"🌡️  Hot (61-85): {len(hot)} clients")
            if warm:
                print(f"🟡 Warm (31-60): {len(warm)} clients")
            
            # Show average score
            avg_score = sum(c.total_score for c in hot_clients) / len(hot_clients)
            print(f"📊 Average score: {avg_score:.1f}")
            
            # Show top client
            top_client = hot_clients[0]
            print(f"⭐ Top client: {top_client.user_id} (Score: {top_client.total_score:.1f})")
        
    else:
        print(f"\n💡 No messages to analyze. Try:")
        print(f"   • Longer period: --days-back 7 or 30")
        print(f"   • Check if channels are accessible")
        print(f"   • Verify Telegram authentication")

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Analyze channel history without real-time monitoring')
    parser.add_argument('--days-back', type=int, default=3, help='Number of days to analyze (default: 3)')
    
    args = parser.parse_args()
    
    asyncio.run(analyze_channels_historical(args.days_back))