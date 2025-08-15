#!/usr/bin/env python3
"""
CLI for OneMinuta Analytics System
Easy-to-use command line interface for property client analysis
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse

from .config import AnalyticsConfig
from .llm_analyzer import LLMPropertyAnalyzer, LLMClientMonitor
from .telegram_monitor import TelegramPropertyMonitor


async def analyze_client(args):
    """Analyze a specific client"""
    config = AnalyticsConfig()
    
    if not config.validate():
        sys.exit(1)
    
    analyzer = LLMPropertyAnalyzer(
        model=config.LLM_MODEL,
        storage_path=config.STORAGE_PATH
    )
    
    # Load client messages
    messages_file = Path(config.STORAGE_PATH) / "analytics" / "user_messages" / f"{args.user_id}.json"
    
    if not messages_file.exists():
        print(f"❌ No messages found for user {args.user_id}")
        return
    
    with open(messages_file, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    print(f"🔍 Analyzing {len(messages)} messages for user {args.user_id}...")
    
    analysis = await analyzer.analyze_client_messages(
        user_id=args.user_id,
        messages=messages,
        username=args.username
    )
    
    # Display results
    print("\n" + "="*60)
    print(f"📊 CLIENT ANALYSIS REPORT")
    print("="*60)
    print(f"User ID: {analysis.user_id}")
    print(f"Language: {analysis.language_detected}")
    print(f"Hotness Score: {analysis.hotness_score}/100 ({analysis.hotness_level.upper()})")
    print(f"Primary Intent: {analysis.primary_intent} (confidence: {analysis.intent_confidence:.2f})")
    print(f"Urgency Level: {analysis.urgency_level}")
    
    if analysis.budget_min or analysis.budget_max:
        budget = f"${analysis.budget_min:,.0f}" if analysis.budget_min else "?"
        if analysis.budget_max and analysis.budget_max != analysis.budget_min:
            budget += f" - ${analysis.budget_max:,.0f}"
        print(f"Budget: {budget} {analysis.currency}")
    
    if analysis.preferred_locations:
        print(f"Locations: {', '.join(analysis.preferred_locations)}")
    
    if analysis.asset_types:
        print(f"Property Types: {', '.join(analysis.asset_types)}")
    
    if analysis.bedrooms:
        print(f"Bedrooms: {analysis.bedrooms}")
    
    print(f"\n🎯 Key Signals:")
    print(f"  💰 Financing Ready: {'✅' if analysis.financing_ready else '❌'}")
    print(f"  🏠 Wants Viewing: {'✅' if analysis.wants_viewing else '❌'}")
    print(f"  📞 Wants Contact: {'✅' if analysis.wants_contact else '❌'}")
    
    if analysis.timeline:
        print(f"  ⏰ Timeline: {analysis.timeline}")
    
    if analysis.key_phrases:
        print(f"\n💡 Key Phrases: {', '.join(analysis.key_phrases[:5])}")
    
    print(f"\n🤖 AI Reasoning:")
    print(f"  {analysis.reasoning}")
    
    print(f"\n📈 Analysis Confidence: {analysis.confidence:.2f}")


async def list_hot_clients(args):
    """List hot clients"""
    config = AnalyticsConfig()
    
    if not config.validate():
        sys.exit(1)
    
    analyzer = LLMPropertyAnalyzer(
        storage_path=config.STORAGE_PATH
    )
    
    hot_clients = await analyzer.get_hot_clients(min_score=args.min_score)
    
    if not hot_clients:
        print(f"🔍 No clients found with score >= {args.min_score}")
        return
    
    print(f"\n🔥 HOT CLIENTS (Score >= {args.min_score})")
    print("="*80)
    
    for i, client in enumerate(hot_clients[:args.limit], 1):
        emoji = "🔥" if client.hotness_score >= 85 else "⚡" if client.hotness_score >= 70 else "🌡️"
        
        budget_str = ""
        if client.budget_min:
            budget_str = f" | Budget: ${client.budget_min:,.0f}"
            if client.budget_max and client.budget_max != client.budget_min:
                budget_str += f"-${client.budget_max:,.0f}"
        
        locations_str = ""
        if client.preferred_locations:
            locations_str = f" | {', '.join(client.preferred_locations[:2])}"
        
        print(f"{i:2d}. {emoji} {client.user_id} | Score: {client.hotness_score:.0f} | "
              f"{client.primary_intent.title()}{budget_str}{locations_str}")
        
        if args.verbose:
            print(f"     Intent confidence: {client.intent_confidence:.2f} | "
                  f"Urgency: {client.urgency_level} | Lang: {client.language_detected}")
            if client.financing_ready or client.wants_viewing or client.wants_contact:
                signals = []
                if client.financing_ready: signals.append("💰 Financing")
                if client.wants_viewing: signals.append("🏠 Viewing")
                if client.wants_contact: signals.append("📞 Contact")
                print(f"     Signals: {' '.join(signals)}")
            print()


async def generate_report(args):
    """Generate analytics report"""
    config = AnalyticsConfig()
    
    if not config.validate():
        sys.exit(1)
    
    analyzer = LLMPropertyAnalyzer(
        storage_path=config.STORAGE_PATH
    )
    
    print("📊 Generating analytics report...")
    
    report = await analyzer.generate_summary_report()
    
    if "error" in report:
        print(f"❌ {report['error']}")
        return
    
    print("\n" + "="*60)
    print("📈 ANALYTICS SUMMARY REPORT")
    print("="*60)
    
    print(f"Total Clients Analyzed: {report['total_clients']}")
    print(f"High-Value Clients (Score ≥61): {report['high_value_clients']}")
    print(f"Average Hotness Score: {report['average_hotness_score']:.1f}")
    print(f"Average Confidence: {report['average_confidence']:.2f}")
    
    print(f"\n🌡️ Hotness Distribution:")
    hotness = report['hotness_distribution']
    print(f"  🔥 Burning (86-100): {hotness['burning']}")
    print(f"  ⚡ Hot (61-85): {hotness['hot']}")
    print(f"  🌡️  Warm (31-60): {hotness['warm']}")
    print(f"  ❄️  Cold (0-30): {hotness['cold']}")
    
    print(f"\n🎯 Intent Distribution:")
    for intent, count in report['intent_distribution'].items():
        print(f"  {intent.title()}: {count}")
    
    print(f"\n🌍 Language Distribution:")
    for lang, count in report['language_distribution'].items():
        flag = "🇺🇸" if lang == "en" else "🇷🇺" if lang == "ru" else "🌐"
        print(f"  {flag} {lang.upper()}: {count}")
    
    print(f"\n📍 Top Locations:")
    for location, count in report['top_locations'][:5]:
        print(f"  {location}: {count} clients")
    
    print(f"\n💰 Client Readiness:")
    print(f"  Financing Ready: {report['financing_ready_count']}")
    print(f"  Wants Viewing: {report['wants_viewing_count']}")
    
    print(f"\n📅 Generated: {report['generated_at']}")
    
    # Save report if requested
    if args.save:
        report_file = Path(config.STORAGE_PATH) / "analytics" / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {report_file}")


async def monitor_channels(args):
    """Start monitoring Telegram channels"""
    config = AnalyticsConfig()
    
    if not config.validate():
        sys.exit(1)
    
    try:
        api_id, api_hash = config.get_telegram_config()
    except ValueError as e:
        print(f"❌ {e}")
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables")
        sys.exit(1)
    
    monitor = TelegramPropertyMonitor(api_id, api_hash, config.STORAGE_PATH)
    
    if args.analyze_history:
        print("📚 Analyzing channel history first...")
        for channel in config.DEFAULT_CHANNELS:
            if args.days_back:
                print(f"  Analyzing {channel} (last {args.days_back} days)...")
                await monitor.analyze_channel_history(channel, limit=args.history_limit, days_back=args.days_back)
            else:
                print(f"  Analyzing {channel} (last {args.history_limit} messages)...")
                await monitor.analyze_channel_history(channel, limit=args.history_limit)
    
    print("🚀 Starting real-time monitoring...")
    print("Press Ctrl+C to stop")
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped")
        monitor.stop_monitoring()


async def test_analysis(args):
    """Test analysis with sample messages"""
    config = AnalyticsConfig()
    
    if not config.validate():
        sys.exit(1)
    
    # Sample test messages
    test_messages = [
        {
            "content": "Hi, I'm looking for a 2-bedroom condo in Phuket, budget around $200k. Need urgent!",
            "timestamp": "2024-01-15T10:30:00Z",
            "channel": "@phuket_property"
        },
        {
            "content": "Cash ready, can view this weekend. Please contact me ASAP",
            "timestamp": "2024-01-15T11:45:00Z",
            "channel": "@phuket_property"
        }
    ]
    
    if args.language == "ru":
        test_messages = [
            {
                "content": "Срочно ищу квартиру в Паттайе до $150k, готов покупать сегодня",
                "timestamp": "2024-01-15T10:30:00Z",
                "channel": "@pattaya_russian"
            },
            {
                "content": "Наличные готовы, можно посмотреть в выходные. Свяжитесь срочно!",
                "timestamp": "2024-01-15T11:45:00Z",
                "channel": "@pattaya_russian"
            }
        ]
    
    analyzer = LLMPropertyAnalyzer(
        model=config.LLM_MODEL,
        storage_path=config.STORAGE_PATH
    )
    
    print(f"🧪 Testing analysis with {args.language.upper()} messages...")
    
    analysis = await analyzer.analyze_client_messages(
        user_id=f"test_user_{args.language}",
        messages=test_messages,
        username=f"@test_user_{args.language}"
    )
    
    print(f"\n✅ Test completed!")
    print(f"Hotness Score: {analysis.hotness_score}/100")
    print(f"Intent: {analysis.primary_intent}")
    print(f"Language Detected: {analysis.language_detected}")
    print(f"Reasoning: {analysis.reasoning}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="OneMinuta Property Client Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze user123 --username @property_hunter
  %(prog)s hot-clients --min-score 70 --limit 10
  %(prog)s report --save
  %(prog)s monitor --analyze-history --days-back 5
  %(prog)s test --language ru
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze specific client')
    analyze_parser.add_argument('user_id', help='User ID to analyze')
    analyze_parser.add_argument('--username', help='Username (optional)')
    
    # Hot clients command
    hot_parser = subparsers.add_parser('hot-clients', help='List hot clients')
    hot_parser.add_argument('--min-score', type=float, default=61.0, help='Minimum hotness score (default: 61)')
    hot_parser.add_argument('--limit', type=int, default=20, help='Maximum number of clients to show (default: 20)')
    hot_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate analytics report')
    report_parser.add_argument('--save', action='store_true', help='Save report to file')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor Telegram channels')
    monitor_parser.add_argument('--analyze-history', action='store_true', help='Analyze channel history first')
    monitor_parser.add_argument('--history-limit', type=int, default=1000, help='Number of historical messages to analyze')
    monitor_parser.add_argument('--days-back', type=int, help='Analyze messages from last N days (e.g., 5 for last 5 days)')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test analysis with sample data')
    test_parser.add_argument('--language', choices=['en', 'ru'], default='en', help='Test language')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run appropriate command
    if args.command == 'analyze':
        asyncio.run(analyze_client(args))
    elif args.command == 'hot-clients':
        asyncio.run(list_hot_clients(args))
    elif args.command == 'report':
        asyncio.run(generate_report(args))
    elif args.command == 'monitor':
        asyncio.run(monitor_channels(args))
    elif args.command == 'test':
        asyncio.run(test_analysis(args))


if __name__ == "__main__":
    main()