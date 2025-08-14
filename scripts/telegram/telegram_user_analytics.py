#!/usr/bin/env python3
"""
Telegram User API Analytics with Telethon
Provides advanced channel analytics using TELEGRAM_API_ID (User API) instead of Bot API
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        Channel, Chat, User, PeerChannel, PeerChat,
        ChatParticipantAdmin, ChatParticipantCreator
    )
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.types import ChannelParticipantsRecent
except ImportError:
    print("❌ Telethon not installed. Installing now...")
    os.system("pip install telethon")
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        Channel, Chat, User, PeerChannel, PeerChat,
        ChatParticipantAdmin, ChatParticipantCreator
    )
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.types import ChannelParticipantsRecent

from services.analytics.channel_analytics import ChannelAnalytics, MemberEventType

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramUserAnalytics:
    """Advanced Telegram analytics using User API (Telethon)"""
    
    def __init__(self, api_id: str, api_hash: str, storage_path: str = "./storage"):
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.storage_path = Path(storage_path)
        
        # Initialize analytics
        self.analytics = ChannelAnalytics(storage_path)
        
        # Session file
        session_file = self.storage_path / "telegram_sessions" / "user_analytics.session"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Telethon client
        self.client = TelegramClient(str(session_file), self.api_id, self.api_hash)
        
        # Track channels we're monitoring
        self.monitored_channels: Dict[int, Dict] = {}
    
    async def start(self):
        """Start the Telethon client"""
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Connected as {me.first_name} (@{me.username})")
    
    async def stop(self):
        """Stop the Telethon client"""
        await self.client.disconnect()
    
    async def scan_all_channels(self) -> List[Dict]:
        """Scan all channels/groups the user is in"""
        logger.info("Scanning all channels and groups...")
        
        all_channels = []
        
        async for dialog in self.client.iter_dialogs():
            if hasattr(dialog.entity, 'id'):
                entity = dialog.entity
                
                # Skip private chats
                if isinstance(entity, User):
                    continue
                
                channel_info = {
                    "id": entity.id,
                    "title": getattr(entity, 'title', 'Unknown'),
                    "username": getattr(entity, 'username', None),
                    "type": "channel" if isinstance(entity, Channel) else "group",
                    "participants_count": getattr(entity, 'participants_count', 0),
                    "is_broadcast": getattr(entity, 'broadcast', False),
                    "is_megagroup": getattr(entity, 'megagroup', False),
                    "created_date": getattr(entity, 'date', None),
                    "admin_rights": getattr(entity, 'admin_rights', None) is not None,
                    "creator": getattr(entity, 'creator', False)
                }
                
                all_channels.append(channel_info)
                logger.info(f"Found: {channel_info['title']} ({channel_info['id']}) - {channel_info['participants_count']} members")
        
        logger.info(f"Total channels/groups found: {len(all_channels)}")
        return all_channels
    
    async def get_channel_members(self, channel_id: int, limit: int = 1000) -> List[Dict]:
        """Get detailed member list for a channel"""
        try:
            entity = await self.client.get_entity(PeerChannel(channel_id))
            
            participants = []
            offset = 0
            
            while len(participants) < limit:
                batch_size = min(200, limit - len(participants))
                
                result = await self.client(GetParticipantsRequest(
                    channel=entity,
                    filter=ChannelParticipantsRecent(),
                    offset=offset,
                    limit=batch_size,
                    hash=0
                ))
                
                if not result.participants:
                    break
                
                for participant in result.participants:
                    user = next((u for u in result.users if u.id == participant.user_id), None)
                    if user:
                        member_info = {
                            "user_id": user.id,
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "is_bot": user.bot,
                            "is_premium": getattr(user, 'premium', False),
                            "joined_date": getattr(participant, 'date', None),
                            "is_admin": isinstance(participant, (ChatParticipantAdmin, ChatParticipantCreator)),
                            "is_creator": isinstance(participant, ChatParticipantCreator)
                        }
                        participants.append(member_info)
                
                offset += batch_size
                
                # Rate limiting
                await asyncio.sleep(1)
            
            logger.info(f"Retrieved {len(participants)} members from channel {channel_id}")
            return participants
            
        except Exception as e:
            logger.error(f"Error getting members for channel {channel_id}: {e}")
            return []
    
    async def analyze_channel_growth(self, channel_id: int, days: int = 30) -> Dict:
        """Analyze channel growth over time by checking member join dates"""
        try:
            # Get current members
            members = await self.get_channel_members(channel_id, limit=5000)
            
            if not members:
                return {}
            
            # Analyze join patterns
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days)
            
            recent_joins = []
            join_dates = []
            
            for member in members:
                if member.get('joined_date'):
                    join_date = member['joined_date']
                    if hasattr(join_date, 'replace'):
                        # Convert to UTC if needed
                        if join_date.tzinfo is None:
                            join_date = join_date.replace(tzinfo=timezone.utc)
                        
                        join_dates.append(join_date)
                        
                        if join_date >= cutoff_date:
                            recent_joins.append(member)
            
            # Calculate statistics
            total_members = len(members)
            recent_joins_count = len(recent_joins)
            
            # Daily join distribution
            daily_joins = {}
            hourly_joins = {}
            
            for join_date in join_dates:
                if join_date >= cutoff_date:
                    day_key = join_date.strftime('%Y-%m-%d')
                    hour_key = join_date.hour
                    
                    daily_joins[day_key] = daily_joins.get(day_key, 0) + 1
                    hourly_joins[hour_key] = hourly_joins.get(hour_key, 0) + 1
            
            # Calculate growth rate
            growth_rate = (recent_joins_count / total_members * 100) if total_members > 0 else 0
            
            # Find peak times
            peak_hour = max(hourly_joins, key=hourly_joins.get) if hourly_joins else None
            avg_daily_joins = recent_joins_count / days if days > 0 else 0
            
            analysis = {
                "channel_id": channel_id,
                "analysis_period_days": days,
                "total_members": total_members,
                "recent_joins": recent_joins_count,
                "growth_rate_percent": round(growth_rate, 2),
                "avg_daily_joins": round(avg_daily_joins, 1),
                "peak_join_hour": peak_hour,
                "daily_distribution": daily_joins,
                "hourly_distribution": hourly_joins,
                "bot_percentage": len([m for m in members if m.get('is_bot')]) / total_members * 100 if total_members > 0 else 0,
                "premium_percentage": len([m for m in members if m.get('is_premium')]) / total_members * 100 if total_members > 0 else 0,
                "analyzed_at": now.isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing channel {channel_id}: {e}")
            return {}
    
    async def monitor_channel_realtime(self, channel_id: int, channel_name: str = None):
        """Set up real-time monitoring for a channel"""
        try:
            entity = await self.client.get_entity(PeerChannel(channel_id))
            channel_name = channel_name or entity.title
            
            logger.info(f"Starting real-time monitoring for: {channel_name} ({channel_id})")
            
            @self.client.on(events.ChatAction)
            async def handler(event):
                if event.chat_id != channel_id:
                    return
                
                # Handle member joins
                if event.user_joined or event.user_added:
                    user = await event.get_user()
                    
                    await self.analytics.track_member_event(
                        channel_id=str(channel_id),
                        channel_name=channel_name,
                        user_id=str(user.id),
                        event_type=MemberEventType.JOINED,
                        username=user.username,
                        metadata={
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "is_premium": getattr(user, 'premium', False),
                            "is_bot": user.bot
                        }
                    )
                    
                    logger.info(f"👋 {user.first_name or user.username or user.id} joined {channel_name}")
                
                # Handle member leaves
                elif event.user_left or event.user_kicked:
                    user = await event.get_user()
                    
                    event_type = MemberEventType.BANNED if event.user_kicked else MemberEventType.LEFT
                    
                    await self.analytics.track_member_event(
                        channel_id=str(channel_id),
                        channel_name=channel_name,
                        user_id=str(user.id),
                        event_type=event_type,
                        username=user.username
                    )
                    
                    logger.info(f"👋 {user.first_name or user.username or user.id} left {channel_name}")
            
            # Store monitoring info
            self.monitored_channels[channel_id] = {
                "name": channel_name,
                "handler": handler,
                "started_at": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error setting up monitoring for channel {channel_id}: {e}")
    
    async def generate_comprehensive_report(self, channel_id: int) -> Dict:
        """Generate comprehensive analytics report for a channel"""
        try:
            # Get basic channel info
            entity = await self.client.get_entity(PeerChannel(channel_id))
            
            # Get current analytics
            current_metrics = await self.analytics.get_channel_metrics(str(channel_id), entity.title)
            
            # Analyze growth using Telegram data
            growth_analysis = await self.analyze_channel_growth(channel_id, days=30)
            
            # Get member sample for analysis
            members_sample = await self.get_channel_members(channel_id, limit=1000)
            
            # Combine all data
            report = {
                "channel_info": {
                    "id": channel_id,
                    "title": entity.title,
                    "username": entity.username,
                    "description": getattr(entity, 'about', ''),
                    "participants_count": entity.participants_count,
                    "is_megagroup": entity.megagroup,
                    "is_broadcast": entity.broadcast,
                    "created_date": entity.date.isoformat() if entity.date else None
                },
                
                "current_metrics": {
                    "total_members": current_metrics.total_members,
                    "active_members": current_metrics.active_members,
                    "new_today": current_metrics.new_members_today,
                    "new_week": current_metrics.new_members_week,
                    "growth_rate": current_metrics.daily_growth_rate,
                    "health_score": current_metrics.channel_health_score,
                    "hot_leads": current_metrics.hot_leads_generated
                },
                
                "telegram_analysis": growth_analysis,
                
                "member_insights": {
                    "sample_size": len(members_sample),
                    "bot_count": len([m for m in members_sample if m.get('is_bot')]),
                    "premium_count": len([m for m in members_sample if m.get('is_premium')]),
                    "admin_count": len([m for m in members_sample if m.get('is_admin')]),
                    "with_username": len([m for m in members_sample if m.get('username')])
                },
                
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report for channel {channel_id}: {e}")
            return {}
    
    async def export_member_list(self, channel_id: int, output_file: str):
        """Export complete member list to file"""
        try:
            members = await self.get_channel_members(channel_id, limit=10000)
            
            # Clean up data for export
            export_data = []
            for member in members:
                export_data.append({
                    "user_id": member["user_id"],
                    "username": member.get("username"),
                    "first_name": member.get("first_name"),
                    "last_name": member.get("last_name"),
                    "is_bot": member.get("is_bot", False),
                    "is_premium": member.get("is_premium", False),
                    "joined_date": member.get("joined_date").isoformat() if member.get("joined_date") else None,
                    "is_admin": member.get("is_admin", False)
                })
            
            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "channel_id": channel_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "total_members": len(export_data),
                    "members": export_data
                }, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(export_data)} members to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting members: {e}")
            return False


async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Telegram Analytics with User API")
    parser.add_argument("--storage", default="./storage", help="Storage directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scan channels
    scan_parser = subparsers.add_parser("scan", help="Scan all channels you're in")
    
    # Channel analytics
    analyze_parser = subparsers.add_parser("analyze", help="Analyze specific channel")
    analyze_parser.add_argument("channel_id", type=int, help="Channel ID (with minus sign)")
    analyze_parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    analyze_parser.add_argument("--export", help="Export member list to file")
    
    # Monitor channels
    monitor_parser = subparsers.add_parser("monitor", help="Monitor channels in real-time")
    monitor_parser.add_argument("channel_ids", nargs="+", type=int, help="Channel IDs to monitor")
    
    # Generate report
    report_parser = subparsers.add_parser("report", help="Generate comprehensive report")
    report_parser.add_argument("channel_id", type=int, help="Channel ID")
    report_parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Get credentials
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ TELEGRAM_API_ID and TELEGRAM_API_HASH required in .env file")
        return
    
    # Create analytics client
    analytics = TelegramUserAnalytics(api_id, api_hash, args.storage)
    
    try:
        await analytics.start()
        
        if args.command == "scan":
            channels = await analytics.scan_all_channels()
            
            print("\n" + "="*80)
            print("📱 YOUR TELEGRAM CHANNELS & GROUPS")
            print("="*80)
            
            if not channels:
                print("No channels found.")
                return
            
            print(f"{'Title':<30} {'ID':<15} {'Members':<10} {'Type':<10} {'Admin':<8}")
            print("-" * 80)
            
            for ch in sorted(channels, key=lambda x: x.get('participants_count', 0), reverse=True):
                title = ch['title'][:29]
                channel_id = str(ch['id'])
                members = ch.get('participants_count', 0)
                ch_type = ch['type']
                is_admin = "✅" if ch.get('admin_rights') or ch.get('creator') else "❌"
                
                print(f"{title:<30} {channel_id:<15} {members:<10,} {ch_type:<10} {is_admin:<8}")
        
        elif args.command == "analyze":
            print(f"📊 Analyzing channel {args.channel_id}...")
            
            analysis = await analytics.analyze_channel_growth(args.channel_id, args.days)
            
            if not analysis:
                print("❌ Failed to analyze channel")
                return
            
            # Print analysis
            print(f"\n" + "="*60)
            print(f"📈 CHANNEL GROWTH ANALYSIS ({args.days} days)")
            print("="*60)
            
            print(f"Total Members: {analysis['total_members']:,}")
            print(f"Recent Joins: {analysis['recent_joins']:,}")
            print(f"Growth Rate: {analysis['growth_rate_percent']}%")
            print(f"Avg Daily Joins: {analysis['avg_daily_joins']}")
            print(f"Peak Join Hour: {analysis['peak_join_hour']}:00")
            print(f"Bot Percentage: {analysis['bot_percentage']:.1f}%")
            print(f"Premium Users: {analysis['premium_percentage']:.1f}%")
            
            # Export members if requested
            if args.export:
                success = await analytics.export_member_list(args.channel_id, args.export)
                if success:
                    print(f"✅ Members exported to {args.export}")
        
        elif args.command == "monitor":
            print(f"🔍 Starting real-time monitoring for {len(args.channel_ids)} channels...")
            
            for channel_id in args.channel_ids:
                await analytics.monitor_channel_realtime(channel_id)
            
            print("✅ Monitoring started. Press Ctrl+C to stop.")
            
            try:
                await analytics.client.run_until_disconnected()
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
        
        elif args.command == "report":
            print(f"📋 Generating comprehensive report for channel {args.channel_id}...")
            
            report = await analytics.generate_comprehensive_report(args.channel_id)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Report saved to {args.output}")
            else:
                print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    
    finally:
        await analytics.stop()


if __name__ == "__main__":
    asyncio.run(main())