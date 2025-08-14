"""
Telegram Channel Analytics System for OneMinuta
Tracks channel growth, member activity, and engagement metrics
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from collections import defaultdict, Counter
from enum import Enum


class MemberEventType(str, Enum):
    """Types of member events"""
    JOINED = "joined"
    LEFT = "left"
    BANNED = "banned"
    UNBANNED = "unbanned"
    PROMOTED = "promoted"
    DEMOTED = "demoted"
    ACTIVE = "active"
    INACTIVE = "inactive"


class GrowthPeriod(str, Enum):
    """Time periods for analytics"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class MemberEvent:
    """Individual member event in channel"""
    user_id: str
    username: Optional[str]
    event_type: MemberEventType
    timestamp: datetime
    channel_id: str
    channel_name: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class ChannelMetrics:
    """Channel performance metrics"""
    channel_id: str
    channel_name: str
    
    # Current stats
    total_members: int
    active_members: int  # Active in last 7 days
    inactive_members: int
    
    # Growth metrics
    new_members_today: int
    new_members_week: int
    new_members_month: int
    
    # Churn metrics
    left_members_today: int
    left_members_week: int
    left_members_month: int
    
    # Engagement metrics
    messages_today: int
    messages_week: int
    avg_messages_per_member: float
    
    # Retention metrics
    retention_rate_7d: float  # % still active after 7 days
    retention_rate_30d: float  # % still active after 30 days
    churn_rate: float
    
    # Growth rates
    daily_growth_rate: float
    weekly_growth_rate: float
    monthly_growth_rate: float
    
    # Bot interaction metrics
    bot_interactions_today: int
    bot_welcome_sent: int
    bot_queries_answered: int
    
    # Lead generation metrics
    hot_leads_generated: int
    warm_leads_generated: int
    total_leads_value: float  # Estimated commission value
    
    # Time series data
    hourly_joins: List[int] = field(default_factory=list)  # Last 24 hours
    daily_joins: List[int] = field(default_factory=list)   # Last 30 days
    daily_leaves: List[int] = field(default_factory=list)  # Last 30 days
    
    # Peak times
    peak_join_hour: Optional[int] = None  # 0-23
    peak_join_day: Optional[str] = None   # Monday-Sunday
    
    # Quality metrics
    member_quality_score: float = 0.0  # Based on engagement
    channel_health_score: float = 0.0  # Overall channel health


@dataclass
class MemberProfile:
    """Detailed member analytics profile"""
    user_id: str
    username: Optional[str]
    join_date: datetime
    last_active: datetime
    
    # Activity metrics
    total_messages: int = 0
    total_reactions: int = 0
    total_replies: int = 0
    
    # Engagement scoring
    engagement_score: float = 0.0
    activity_streak: int = 0  # Days of consecutive activity
    
    # Property interest
    property_searches: int = 0
    property_inquiries: int = 0
    lead_score: Optional[float] = None
    lead_status: Optional[str] = None  # cold, warm, hot, burning
    
    # Behavior patterns
    most_active_hour: Optional[int] = None
    avg_response_time: Optional[float] = None  # in minutes
    preferred_language: str = "en"
    
    # Channel participation
    channels_joined: List[str] = field(default_factory=list)
    referral_source: Optional[str] = None


class ChannelAnalytics:
    """Main analytics system for Telegram channels"""
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.analytics_path = self.storage_path / "analytics" / "channels"
        self.analytics_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Cache for performance
        self.member_cache: Dict[str, MemberProfile] = {}
        self.metrics_cache: Dict[str, ChannelMetrics] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = datetime.now(timezone.utc)
    
    async def track_member_event(self, channel_id: str, channel_name: str,
                                user_id: str, event_type: MemberEventType,
                                username: Optional[str] = None,
                                metadata: Dict = None) -> None:
        """Track a member event (join, leave, etc.)"""
        
        event = MemberEvent(
            user_id=user_id,
            username=username,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            channel_id=channel_id,
            channel_name=channel_name,
            metadata=metadata or {}
        )
        
        # Store event
        await self._store_event(event)
        
        # Update member profile
        await self._update_member_profile(event)
        
        # Update channel metrics
        await self._update_channel_metrics(channel_id, channel_name, event)
        
        # Trigger alerts if needed
        await self._check_growth_alerts(channel_id, event)
    
    async def _store_event(self, event: MemberEvent) -> None:
        """Store member event to disk"""
        
        # Daily event log per channel
        date_str = event.timestamp.strftime("%Y-%m-%d")
        event_file = self.analytics_path / event.channel_id / "events" / f"{date_str}.ndjson"
        event_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Append event as newline-delimited JSON
        event_data = asdict(event)
        event_data["timestamp"] = event.timestamp.isoformat()
        
        with open(event_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
    
    async def _update_member_profile(self, event: MemberEvent) -> None:
        """Update or create member profile"""
        
        profile_file = self.analytics_path / "members" / f"{event.user_id}.json"
        profile_file.parent.mkdir(parents=True, exist_ok=True)
        
        if profile_file.exists():
            with open(profile_file, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
                profile = MemberProfile(**profile_data)
        else:
            profile = MemberProfile(
                user_id=event.user_id,
                username=event.username,
                join_date=event.timestamp,
                last_active=event.timestamp
            )
        
        # Update based on event type
        if event.event_type == MemberEventType.JOINED:
            if event.channel_id not in profile.channels_joined:
                profile.channels_joined.append(event.channel_id)
        elif event.event_type == MemberEventType.LEFT:
            if event.channel_id in profile.channels_joined:
                profile.channels_joined.remove(event.channel_id)
        elif event.event_type == MemberEventType.ACTIVE:
            profile.last_active = event.timestamp
            profile.total_messages += event.metadata.get("message_count", 1)
        
        # Save updated profile
        profile_data = asdict(profile)
        profile_data["join_date"] = profile.join_date.isoformat()
        profile_data["last_active"] = profile.last_active.isoformat()
        
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        # Update cache
        self.member_cache[event.user_id] = profile
    
    async def _update_channel_metrics(self, channel_id: str, channel_name: str, 
                                     event: MemberEvent) -> None:
        """Update channel metrics with new event"""
        
        metrics = await self.get_channel_metrics(channel_id, channel_name)
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Update counters based on event type
        if event.event_type == MemberEventType.JOINED:
            metrics.total_members += 1
            
            # Update time-based counters
            if event.timestamp >= today_start:
                metrics.new_members_today += 1
            if event.timestamp >= week_start:
                metrics.new_members_week += 1
            if event.timestamp >= month_start:
                metrics.new_members_month += 1
            
            # Update hourly distribution
            hour = event.timestamp.hour
            if len(metrics.hourly_joins) <= hour:
                metrics.hourly_joins.extend([0] * (hour - len(metrics.hourly_joins) + 1))
            metrics.hourly_joins[hour] += 1
            
        elif event.event_type == MemberEventType.LEFT:
            metrics.total_members = max(0, metrics.total_members - 1)
            
            if event.timestamp >= today_start:
                metrics.left_members_today += 1
            if event.timestamp >= week_start:
                metrics.left_members_week += 1
            if event.timestamp >= month_start:
                metrics.left_members_month += 1
        
        # Calculate growth rates
        metrics.daily_growth_rate = self._calculate_growth_rate(
            metrics.new_members_today, metrics.left_members_today, metrics.total_members
        )
        metrics.weekly_growth_rate = self._calculate_growth_rate(
            metrics.new_members_week, metrics.left_members_week, metrics.total_members
        )
        metrics.monthly_growth_rate = self._calculate_growth_rate(
            metrics.new_members_month, metrics.left_members_month, metrics.total_members
        )
        
        # Calculate retention and churn
        if metrics.total_members > 0:
            metrics.churn_rate = (metrics.left_members_month / metrics.total_members) * 100
        
        # Update channel health score
        metrics.channel_health_score = self._calculate_health_score(metrics)
        
        # Save metrics
        await self._save_channel_metrics(channel_id, metrics)
    
    def _calculate_growth_rate(self, new_members: int, left_members: int, 
                              total: int) -> float:
        """Calculate growth rate percentage"""
        if total == 0:
            return 0.0
        net_growth = new_members - left_members
        return (net_growth / total) * 100
    
    def _calculate_health_score(self, metrics: ChannelMetrics) -> float:
        """Calculate overall channel health score (0-100)"""
        score = 50.0  # Base score
        
        # Growth bonus (up to +30)
        if metrics.daily_growth_rate > 0:
            score += min(30, metrics.daily_growth_rate * 10)
        else:
            score += max(-20, metrics.daily_growth_rate * 5)
        
        # Engagement bonus (up to +20)
        if metrics.total_members > 0:
            engagement_rate = metrics.active_members / metrics.total_members
            score += engagement_rate * 20
        
        # Retention bonus (up to +20)
        score += metrics.retention_rate_7d * 0.2
        
        # Churn penalty (up to -20)
        if metrics.churn_rate > 10:
            score -= min(20, metrics.churn_rate - 10)
        
        return max(0, min(100, score))
    
    async def _save_channel_metrics(self, channel_id: str, metrics: ChannelMetrics) -> None:
        """Save channel metrics to disk"""
        
        metrics_file = self.analytics_path / channel_id / "metrics.json"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        metrics_data = asdict(metrics)
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Update cache
        self.metrics_cache[channel_id] = metrics
        
        # Also save historical snapshot
        await self._save_historical_snapshot(channel_id, metrics)
    
    async def _save_historical_snapshot(self, channel_id: str, metrics: ChannelMetrics) -> None:
        """Save historical snapshot for trend analysis"""
        
        now = datetime.now(timezone.utc)
        snapshot_file = self.analytics_path / channel_id / "history" / f"{now.strftime('%Y-%m')}.ndjson"
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        
        snapshot = {
            "timestamp": now.isoformat(),
            "total_members": metrics.total_members,
            "active_members": metrics.active_members,
            "new_members_today": metrics.new_members_today,
            "left_members_today": metrics.left_members_today,
            "growth_rate_daily": metrics.daily_growth_rate,
            "health_score": metrics.channel_health_score,
            "hot_leads": metrics.hot_leads_generated
        }
        
        with open(snapshot_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot) + "\n")
    
    async def get_channel_metrics(self, channel_id: str, 
                                 channel_name: str = None, telegram_bot=None) -> ChannelMetrics:
        """Get or create channel metrics with real member count from Telegram API"""
        
        # Check cache first
        if channel_id in self.metrics_cache:
            cache_age = (datetime.now(timezone.utc) - self.last_cache_update).seconds
            if cache_age < self.cache_ttl:
                return self.metrics_cache[channel_id]
        
        metrics_file = self.analytics_path / channel_id / "metrics.json"
        
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
                metrics = ChannelMetrics(**metrics_data)
        else:
            # Create new metrics with real member count from Telegram
            real_member_count = await self._get_real_member_count(channel_id, telegram_bot)
            
            metrics = ChannelMetrics(
                channel_id=channel_id,
                channel_name=channel_name or channel_id,
                total_members=real_member_count,  # Use real count from Telegram
                active_members=0,
                inactive_members=real_member_count,  # Assume all inactive until tracked
                new_members_today=0,
                new_members_week=0,
                new_members_month=0,
                left_members_today=0,
                left_members_week=0,
                left_members_month=0,
                messages_today=0,
                messages_week=0,
                avg_messages_per_member=0.0,
                retention_rate_7d=100.0,
                retention_rate_30d=100.0,
                churn_rate=0.0,
                daily_growth_rate=0.0,
                weekly_growth_rate=0.0,
                monthly_growth_rate=0.0,
                bot_interactions_today=0,
                bot_welcome_sent=0,
                bot_queries_answered=0,
                hot_leads_generated=0,
                warm_leads_generated=0,
                total_leads_value=0.0
            )
            
            # Save the newly created metrics
            await self._save_channel_metrics(channel_id, metrics)
            self.logger.info(f"Initialized channel {channel_id} with {real_member_count} real members")
        
        self.metrics_cache[channel_id] = metrics
        return metrics
    
    async def _check_growth_alerts(self, channel_id: str, event: MemberEvent) -> None:
        """Check for significant growth events and trigger alerts"""
        
        metrics = self.metrics_cache.get(channel_id)
        if not metrics:
            return
        
        alerts = []
        
        # Rapid growth alert
        if metrics.new_members_today >= 50:
            alerts.append({
                "type": "rapid_growth",
                "message": f"🚀 Channel {channel_id} gained {metrics.new_members_today} members today!",
                "severity": "info"
            })
        
        # High churn alert
        if metrics.churn_rate > 20:
            alerts.append({
                "type": "high_churn",
                "message": f"⚠️ Channel {channel_id} has {metrics.churn_rate:.1f}% churn rate",
                "severity": "warning"
            })
        
        # Milestone alerts
        if metrics.total_members in [100, 500, 1000, 5000, 10000, 50000, 100000]:
            alerts.append({
                "type": "milestone",
                "message": f"🎉 Channel {channel_id} reached {metrics.total_members} members!",
                "severity": "success"
            })
        
        # Save alerts
        if alerts:
            await self._save_alerts(channel_id, alerts)
    
    async def _save_alerts(self, channel_id: str, alerts: List[Dict]) -> None:
        """Save growth alerts"""
        
        alerts_file = self.analytics_path / channel_id / "alerts.ndjson"
        alerts_file.parent.mkdir(parents=True, exist_ok=True)
        
        for alert in alerts:
            alert["timestamp"] = datetime.now(timezone.utc).isoformat()
            alert["channel_id"] = channel_id
            
            with open(alerts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert) + "\n")
            
            self.logger.info(f"{alert['severity'].upper()}: {alert['message']}")
    
    async def generate_growth_report(self, channel_id: str, 
                                    period: GrowthPeriod = GrowthPeriod.WEEKLY) -> Dict:
        """Generate comprehensive growth report for a channel"""
        
        metrics = await self.get_channel_metrics(channel_id)
        
        # Calculate period-specific data
        now = datetime.now(timezone.utc)
        
        if period == GrowthPeriod.DAILY:
            period_start = now - timedelta(days=1)
            period_name = "24 Hours"
        elif period == GrowthPeriod.WEEKLY:
            period_start = now - timedelta(days=7)
            period_name = "7 Days"
        elif period == GrowthPeriod.MONTHLY:
            period_start = now - timedelta(days=30)
            period_name = "30 Days"
        else:
            period_start = now - timedelta(days=7)
            period_name = "7 Days"
        
        # Load events for period
        events = await self._load_events_for_period(channel_id, period_start, now)
        
        # Analyze events
        joins_by_hour = defaultdict(int)
        joins_by_day = defaultdict(int)
        top_referrers = Counter()
        
        for event in events:
            if event["event_type"] == "joined":
                hour = datetime.fromisoformat(event["timestamp"]).hour
                day = datetime.fromisoformat(event["timestamp"]).strftime("%A")
                joins_by_hour[hour] += 1
                joins_by_day[day] += 1
                
                if "referrer" in event.get("metadata", {}):
                    top_referrers[event["metadata"]["referrer"]] += 1
        
        # Find peak times
        peak_hour = max(joins_by_hour, key=lambda k: joins_by_hour[k]) if joins_by_hour else None
        peak_day = max(joins_by_day, key=lambda k: joins_by_day[k]) if joins_by_day else None
        
        report = {
            "channel_id": channel_id,
            "channel_name": metrics.channel_name,
            "period": period_name,
            "generated_at": now.isoformat(),
            
            "summary": {
                "total_members": metrics.total_members,
                "net_growth": metrics.new_members_week - metrics.left_members_week,
                "growth_rate": f"{metrics.weekly_growth_rate:.1f}%",
                "health_score": f"{metrics.channel_health_score:.0f}/100"
            },
            
            "growth_metrics": {
                "new_members": {
                    "today": metrics.new_members_today,
                    "this_week": metrics.new_members_week,
                    "this_month": metrics.new_members_month
                },
                "lost_members": {
                    "today": metrics.left_members_today,
                    "this_week": metrics.left_members_week,
                    "this_month": metrics.left_members_month
                },
                "growth_rates": {
                    "daily": f"{metrics.daily_growth_rate:.2f}%",
                    "weekly": f"{metrics.weekly_growth_rate:.2f}%",
                    "monthly": f"{metrics.monthly_growth_rate:.2f}%"
                }
            },
            
            "engagement_metrics": {
                "active_members": metrics.active_members,
                "inactive_members": metrics.inactive_members,
                "messages_today": metrics.messages_today,
                "messages_this_week": metrics.messages_week,
                "avg_messages_per_member": metrics.avg_messages_per_member,
                "bot_interactions": metrics.bot_interactions_today
            },
            
            "quality_metrics": {
                "retention_7d": f"{metrics.retention_rate_7d:.1f}%",
                "retention_30d": f"{metrics.retention_rate_30d:.1f}%",
                "churn_rate": f"{metrics.churn_rate:.1f}%",
                "member_quality_score": f"{metrics.member_quality_score:.1f}/100"
            },
            
            "lead_generation": {
                "hot_leads": metrics.hot_leads_generated,
                "warm_leads": metrics.warm_leads_generated,
                "estimated_value": f"${metrics.total_leads_value:,.2f}",
                "bot_welcomes_sent": metrics.bot_welcome_sent
            },
            
            "peak_activity": {
                "peak_join_hour": f"{peak_hour}:00" if peak_hour is not None else "N/A",
                "peak_join_day": peak_day or "N/A",
                "hourly_distribution": dict(joins_by_hour),
                "daily_distribution": dict(joins_by_day)
            },
            
            "top_referrers": dict(top_referrers.most_common(5)),
            
            "recommendations": self._generate_recommendations(metrics)
        }
        
        # Save report
        report_file = self.analytics_path / channel_id / "reports" / f"{now.strftime('%Y-%m-%d')}_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    async def _load_events_for_period(self, channel_id: str, 
                                     start: datetime, end: datetime) -> List[Dict]:
        """Load events for a specific period"""
        
        events = []
        events_dir = self.analytics_path / channel_id / "events"
        
        if not events_dir.exists():
            return events
        
        # Iterate through daily event files
        current = start.date()
        while current <= end.date():
            event_file = events_dir / f"{current.strftime('%Y-%m-%d')}.ndjson"
            
            if event_file.exists():
                with open(event_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line)
                            event_time = datetime.fromisoformat(event["timestamp"])
                            if start <= event_time <= end:
                                events.append(event)
                        except (json.JSONDecodeError, KeyError):
                            continue
            
            current += timedelta(days=1)
        
        return events
    
    async def _get_real_member_count(self, channel_id: str, telegram_bot=None) -> int:
        """Get actual member count from Telegram API"""
        if not telegram_bot:
            self.logger.warning(f"No Telegram bot provided for channel {channel_id}, using 0 as member count")
            return 0
            
        try:
            # Convert string channel_id to int if needed
            chat_id = int(channel_id) if channel_id.lstrip('-').isdigit() else channel_id
            
            # Get chat member count from Telegram
            member_count = await telegram_bot.get_chat_member_count(chat_id)
            self.logger.info(f"Channel {channel_id} has {member_count} real members from Telegram API")
            return member_count
            
        except Exception as e:
            self.logger.error(f"Failed to get real member count for channel {channel_id}: {e}")
            return 0
    
    async def sync_real_member_count(self, channel_id: str, telegram_bot=None):
        """Sync channel metrics with real Telegram member count"""
        try:
            real_count = await self._get_real_member_count(channel_id, telegram_bot)
            
            metrics = await self.get_channel_metrics(channel_id, telegram_bot=telegram_bot)
            old_count = metrics.total_members
            
            # Update total member count to real count
            metrics.total_members = real_count
            
            # Log the difference
            difference = real_count - old_count
            if difference != 0:
                self.logger.info(f"Synced channel {channel_id}: {old_count} -> {real_count} members (diff: {difference:+d})")
            
            # Save updated metrics
            await self._save_channel_metrics(channel_id, metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to sync member count for channel {channel_id}: {e}")
            return None
    
    def _generate_recommendations(self, metrics: ChannelMetrics) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        
        recommendations = []
        
        # Growth recommendations
        if metrics.daily_growth_rate < 0:
            recommendations.append("📉 Channel is losing members. Consider more engaging content.")
        elif metrics.daily_growth_rate < 1:
            recommendations.append("📊 Growth is slow. Try cross-promotion with partner channels.")
        elif metrics.daily_growth_rate > 10:
            recommendations.append("🚀 Rapid growth detected! Ensure bot can handle increased load.")
        
        # Engagement recommendations
        if metrics.active_members < metrics.total_members * 0.3:
            recommendations.append("💤 Low engagement. Send targeted property alerts to re-engage members.")
        
        # Retention recommendations
        if metrics.churn_rate > 15:
            recommendations.append("⚠️ High churn rate. Review welcome message and initial experience.")
        
        # Lead generation recommendations
        if metrics.hot_leads_generated < metrics.total_members * 0.01:
            recommendations.append("🎯 Low lead conversion. Optimize bot responses for better qualification.")
        
        # Peak time recommendations
        if metrics.peak_join_hour is not None:
            recommendations.append(f"⏰ Schedule important announcements around {metrics.peak_join_hour}:00.")
        
        return recommendations
    
    async def get_multi_channel_dashboard(self, channel_ids: List[str], 
                                         partner_id: str = None, 
                                         include_official: bool = True) -> Dict:
        """Generate dashboard data for multiple channels, optionally filtered by partner"""
        
        # Separate official vs partner channels
        official_channels = []
        partner_channels = []
        
        # OneMinuta official channel ID
        oneminuta_official_id = "-1002875386834"
        
        for channel_id in channel_ids:
            if channel_id == oneminuta_official_id:
                official_channels.append(channel_id)
            else:
                partner_channels.append(channel_id)
        
        dashboard = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_channels": len(channel_ids),
            "partner_id": partner_id,
            "official_channels": len(official_channels),
            "partner_channels": len(partner_channels),
            "include_official": include_official,
            "channels": [],
            "aggregate_metrics": {
                "total_members_all": 0,
                "total_new_today": 0,
                "total_new_week": 0,
                "avg_growth_rate": 0.0,
                "total_hot_leads": 0,
                "total_estimated_value": 0.0
            }
        }
        
        for channel_id in channel_ids:
            metrics = await self.get_channel_metrics(channel_id)
            
            # Determine channel type
            channel_type = "official" if channel_id == oneminuta_official_id else "partner"
            
            channel_summary = {
                "channel_id": channel_id,
                "channel_name": metrics.channel_name,
                "channel_type": channel_type,
                "members": metrics.total_members,
                "new_today": metrics.new_members_today,
                "growth_rate": metrics.daily_growth_rate,  # Keep as number
                "growth_rate_display": f"{metrics.daily_growth_rate:.1f}%",
                "health_score": metrics.channel_health_score,
                "hot_leads": metrics.hot_leads_generated,
                "status": "🟢 Healthy" if metrics.channel_health_score > 70 else
                         "🟡 Normal" if metrics.channel_health_score > 40 else "🔴 Needs Attention"
            }
            
            # Only include in aggregates if appropriate
            if channel_type == "official" and not include_official and partner_id:
                # Skip official channel in partner-specific reports
                continue
            
            dashboard["channels"].append(channel_summary)
            
            # Update aggregates
            dashboard["aggregate_metrics"]["total_members_all"] += metrics.total_members
            dashboard["aggregate_metrics"]["total_new_today"] += metrics.new_members_today
            dashboard["aggregate_metrics"]["total_new_week"] += metrics.new_members_week
            dashboard["aggregate_metrics"]["total_hot_leads"] += metrics.hot_leads_generated
            dashboard["aggregate_metrics"]["total_estimated_value"] += metrics.total_leads_value
        
        # Calculate average growth rate
        if dashboard["channels"]:
            total_growth = sum(
                c["growth_rate"] 
                for c in dashboard["channels"] 
                if isinstance(c["growth_rate"], (int, float))
            )
            dashboard["aggregate_metrics"]["avg_growth_rate"] = f"{total_growth / len(dashboard['channels']):.1f}%"
        
        return dashboard
    
    async def get_official_channel_dashboard(self) -> Dict:
        """Generate dashboard for OneMinuta's official channel only"""
        oneminuta_official_id = "-1002875386834"
        
        dashboard = await self.get_multi_channel_dashboard(
            [oneminuta_official_id], 
            partner_id=None, 
            include_official=True
        )
        
        # Add official channel specific metrics
        dashboard["dashboard_type"] = "official"
        dashboard["company_metrics"] = {
            "brand_reach": dashboard["aggregate_metrics"]["total_members_all"],
            "engagement_rate": self._calculate_overall_engagement_rate(dashboard["channels"]),
            "conversion_to_users": self._calculate_user_conversion_rate(dashboard["channels"]),
        }
        
        return dashboard
    
    async def get_partner_dashboard(self, partner_channels: List[str], partner_name: str = None) -> Dict:
        """Generate partner-specific dashboard across all their channels"""
        # Exclude official channel from partner dashboards
        dashboard = await self.get_multi_channel_dashboard(
            partner_channels, 
            partner_id="custom", 
            include_official=False
        )
        
        # Add partner-specific metrics
        dashboard["dashboard_type"] = "partner"
        dashboard["partner_name"] = partner_name
        dashboard["channel_performance"] = {}
        
        # Calculate per-channel performance for the partner
        for channel in dashboard["channels"]:
            channel_id = channel["channel_id"]
            dashboard["channel_performance"][channel_id] = {
                "lead_conversion_rate": self._calculate_lead_conversion(channel),
                "avg_member_value": self._calculate_member_value(channel),
                "growth_trend": self._calculate_growth_trend(channel)
            }
        
        return dashboard
    
    def _calculate_lead_conversion(self, channel: Dict) -> float:
        """Calculate lead conversion rate for a channel"""
        # Placeholder - implement based on actual lead tracking
        hot_leads = channel.get("hot_leads", 0)
        total_members = channel.get("members", 0)
        return (hot_leads / total_members * 100) if total_members > 0 else 0.0
    
    def _calculate_member_value(self, channel: Dict) -> float:
        """Calculate average member value for a channel based on property activity"""
        try:
            # Calculate based on property messages and member count
            property_messages = channel.get("property_messages", 0)
            members = channel.get("members", 1)  # Avoid division by zero
            
            if property_messages == 0:
                return 0.0
            
            # Estimate value based on property message activity per member
            # Higher property messages per member indicates more valuable channel
            activity_ratio = property_messages / members
            
            # Scale to reasonable currency value (THB)
            # This is a heuristic based on property market activity
            base_value = activity_ratio * 1000  # Base value in THB
            
            # Cap the maximum value to prevent unrealistic numbers
            return min(base_value, 50000.0)  # Max 50k THB per member
            
        except (ZeroDivisionError, KeyError, TypeError):
            return 0.0
    
    def _calculate_overall_engagement_rate(self, channels: List[Dict]) -> float:
        """Calculate overall engagement rate across all channels"""
        try:
            total_messages = 0
            total_members = 0
            
            for channel in channels:
                total_messages += channel.get("total_messages", 0)
                total_members += channel.get("members", 0)
            
            if total_members == 0:
                return 0.0
            
            # Engagement rate as messages per member (normalized to percentage)
            engagement = (total_messages / total_members) * 100
            
            # Cap at reasonable maximum (e.g., 500% for very active channels)
            return min(engagement, 500.0)
            
        except (ZeroDivisionError, KeyError, TypeError):
            return 0.0
    
    def _calculate_user_conversion_rate(self, channels: List[Dict]) -> int:
        """Calculate number of users converted from channels to bot users"""
        try:
            # This would require tracking users who move from channel to bot
            # For now, estimate based on hot leads as potential conversions
            total_conversions = 0
            
            for channel in channels:
                hot_leads = channel.get("hot_leads", 0)
                # Assume 20% of hot leads convert to bot users (industry estimate)
                estimated_conversions = int(hot_leads * 0.2)
                total_conversions += estimated_conversions
            
            return total_conversions
            
        except (KeyError, TypeError):
            return 0
    
    def _calculate_growth_trend(self, channel: Dict) -> str:
        """Calculate growth trend for a channel"""
        growth_rate = channel.get("growth_rate", 0)
        if growth_rate > 2.0:
            return "🚀 Excellent"
        elif growth_rate > 0.5:
            return "📈 Good"
        elif growth_rate > 0:
            return "➡️ Stable"
        else:
            return "📉 Needs Attention"


    async def track_partner_event(self, partner_id: str, channel_id: str, 
                                 event_type: MemberEventType, metadata: Dict = None) -> None:
        """Track events at partner level for multi-channel analytics"""
        
        # Store partner-level event
        partner_event = {
            "partner_id": partner_id,
            "channel_id": channel_id,
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # Store in partner-specific analytics
        partner_dir = self.analytics_path / "partners" / partner_id
        partner_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        events_file = partner_dir / f"events_{date_str}.ndjson"
        
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(partner_event) + "\n")


# Integration with Telegram bot
async def track_telegram_event(channel_id: str, channel_name: str,
                              user_id: str, event_type: str,
                              username: str = None, partner_id: str = None) -> None:
    """Helper function to track Telegram events with partner support"""
    
    analytics = ChannelAnalytics()
    
    event_type_map = {
        "join": MemberEventType.JOINED,
        "leave": MemberEventType.LEFT,
        "message": MemberEventType.ACTIVE,
        "ban": MemberEventType.BANNED
    }
    
    # Track channel-level event
    await analytics.track_member_event(
        channel_id=channel_id,
        channel_name=channel_name,
        user_id=user_id,
        event_type=event_type_map.get(event_type, MemberEventType.ACTIVE),
        username=username
    )
    
    # Track partner-level event if partner_id provided
    if partner_id:
        await analytics.track_partner_event(
            partner_id=partner_id,
            channel_id=channel_id,
            event_type=event_type_map.get(event_type, MemberEventType.ACTIVE),
            metadata={"username": username, "user_id": user_id}
        )