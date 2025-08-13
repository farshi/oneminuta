"""
Telegram Channel Monitor for Property Client Analysis
Monitors Telegram channels and extracts client signals in real-time
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import User, Channel
except ImportError:
    # Fallback for when Telethon is not installed
    TelegramClient = None
    events = None

from .client_analyzer import PropertyClientAnalyzer, ClientSignal, EngagementType


class TelegramPropertyMonitor:
    """Monitors Telegram channels for property client activity"""
    
    def __init__(self, api_id: int, api_hash: str, storage_path: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.storage_path = Path(storage_path)
        self.analyzer = PropertyClientAnalyzer(storage_path)
        
        self.client = None
        self.monitored_channels: Set[str] = set()
        self.running = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config_path = self.storage_path / "config" / "monitor_config.json"
        self.load_config()
    
    def is_likely_owner_message(self, text: str) -> bool:
        """Detect if message is likely from channel owner/admin based on content patterns"""
        text_lower = text.lower()
        
        # Promotional/channel content indicators
        promotional_indicators = [
            'подписывайтесь', 'subscribe', 'смотрим', 'watch', 'youtube', 'видео',
            'ролик', 'выпуск', '➡️', '✅', '✔️', '#', 'hashtag', 'канал',
            'channel', 'новый выпуск', 'рассказываем', 'разбираемся'
        ]
        
        # Property listing indicators (owner behavior)
        listing_indicators = [
            'for sale', 'for rent', 'available', 'price:', '฿', 'thb', 'baht',
            'bedroom', 'bathroom', 'sqm', 'sq.m', 'square meter',
            'contact:', 'call:', 'line:', 'whatsapp:', 'tel:', 'phone:',
            'продается', 'сдается', 'цена:', 'спальн', 'ванн', 'кв.м',
            'контакт:', 'звонить:', 'телефон:'
        ]
        
        # Marketing/promotional content indicators
        marketing_indicators = [
            'ипотеку', 'рассрочку', 'financing', 'mortgage', 'installment',
            'документы', 'documents', 'как купить', 'how to buy',
            'инвестиции', 'investment'
        ]
        
        # Check for promotional content (contains links, hashtags, formatting)
        has_promo = any(promo in text_lower for promo in promotional_indicators)
        has_hashtag = '#' in text
        has_link = any(link in text_lower for link in ['http', 'youtube', 'vk.com', 't.me'])
        has_formatting = any(fmt in text for fmt in ['**', '✅', '➡️', '✔️'])
        
        if has_promo or has_hashtag or (has_link and len(text) > 100) or has_formatting:
            return True
        
        # Check if message contains multiple listing indicators
        indicator_count = sum(1 for indicator in listing_indicators if indicator in text_lower)
        marketing_count = sum(1 for indicator in marketing_indicators if indicator in text_lower)
        
        # Long messages with multiple indicators are likely listings/promotional
        if len(text) > 200 and (indicator_count >= 2 or marketing_count >= 1):
            return True
        
        # Messages with price and contact info are likely listings  
        has_price = any(price_word in text_lower for price_word in ['price:', '฿', 'thb', 'million', 'цена:'])
        has_contact = any(contact_word in text_lower for contact_word in ['contact:', 'call:', 'line:', 'tel:', 'контакт:'])
        
        if has_price and has_contact:
            return True
        
        # Very short messages are likely member comments
        if len(text.strip()) < 50:
            return False
            
        return False
    
    def load_config(self):
        """Load monitoring configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.monitored_channels = set(config.get('channels', []))
        else:
            # Use default channels from config
            from .config import AnalyticsConfig
            self.monitored_channels = set(AnalyticsConfig.DEFAULT_CHANNELS)
            self.save_config()
    
    def save_config(self):
        """Save monitoring configuration"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            'channels': list(self.monitored_channels),
            'last_updated': datetime.utcnow().isoformat()
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    async def start_monitoring(self):
        """Start monitoring Telegram channels"""
        if TelegramClient is None:
            self.logger.error("Telethon not installed. Run: pip install telethon")
            return
        
        # Use persistent session from sessions folder
        session_path = Path('sessions') / 'oneminuta_prod'
        if not session_path.parent.exists():
            session_path.parent.mkdir(exist_ok=True)
        session_name = str(session_path)
        self.client = TelegramClient(session_name, self.api_id, self.api_hash)
        
        try:
            await self.client.start()
            self.logger.info("Telegram client started successfully")
            
            # Register event handlers
            self.client.add_event_handler(self.handle_new_message, events.NewMessage())
            
            # Join monitored channels
            await self.join_channels()
            
            self.running = True
            self.logger.info(f"Monitoring {len(self.monitored_channels)} channels")
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            self.logger.error(f"Error starting monitor: {e}")
        finally:
            self.running = False
    
    async def join_channels(self):
        """Join all monitored channels"""
        for channel in self.monitored_channels:
            try:
                await self.client.get_entity(channel)
                self.logger.info(f"Monitoring channel: {channel}")
            except Exception as e:
                self.logger.warning(f"Could not access channel {channel}: {e}")
    
    async def handle_new_message(self, event):
        """Handle new message in monitored channels"""
        try:
            # Get message details
            message = event.message
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # Skip if not from monitored channel
            if hasattr(chat, 'username') and f"@{chat.username}" not in self.monitored_channels:
                return
            
            # Skip bot messages
            if hasattr(sender, 'bot') and sender.bot:
                return
            
            # Skip owner/admin promotional messages
            if message.text and self.is_likely_owner_message(message.text):
                self.logger.debug(f"Filtered owner/promotional message from {sender.id}")
                return
            
            # Extract user information
            user_id = str(sender.id) if sender else None
            handle = f"@{sender.username}" if hasattr(sender, 'username') and sender.username else None
            
            if not user_id:
                return
            
            # Get channel information
            channel_username = f"@{chat.username}" if hasattr(chat, 'username') else str(chat.id)
            
            # Analyze message for client signals
            signals = await self.analyzer.analyze_message(
                user_id=user_id,
                message=message.text or "",
                timestamp=message.date or datetime.utcnow(),
                channel=channel_username,
                message_id=message.id
            )
            
            # Update client profile
            if signals:
                profile = await self.analyzer.update_client_profile(user_id, signals)
                
                # Log high-value signals
                if profile.hotness_level.value in ['hot', 'burning']:
                    self.logger.info(f"Hot client detected: {handle or user_id} "
                                   f"(Score: {profile.total_score:.1f}, Level: {profile.hotness_level.value})")
                
                # Save interaction for further analysis
                await self.save_interaction(user_id, handle, message, channel_username, profile)
        
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def save_interaction(self, user_id: str, handle: Optional[str], 
                             message, channel: str, profile):
        """Save interaction details for analysis"""
        interaction_log = self.storage_path / "analytics" / "interactions.ndjson"
        interaction_log.parent.mkdir(parents=True, exist_ok=True)
        
        interaction = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'handle': handle,
            'message_id': message.id,
            'channel': channel,
            'message_text': message.text[:500] if message.text else "",  # Truncate long messages
            'client_score': profile.total_score,
            'hotness_level': profile.hotness_level.value,
            'signal_types': [s.signal_type.value for s in profile.signals[-5:]]  # Last 5 signals
        }
        
        with open(interaction_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(interaction, ensure_ascii=False) + '\n')
    
    async def add_channel(self, channel: str):
        """Add a new channel to monitor"""
        if not channel.startswith('@'):
            channel = f"@{channel}"
        
        self.monitored_channels.add(channel)
        self.save_config()
        
        if self.client and self.running:
            try:
                await self.client.get_entity(channel)
                self.logger.info(f"Added channel to monitoring: {channel}")
            except Exception as e:
                self.logger.error(f"Could not add channel {channel}: {e}")
    
    async def remove_channel(self, channel: str):
        """Remove a channel from monitoring"""
        if not channel.startswith('@'):
            channel = f"@{channel}"
        
        self.monitored_channels.discard(channel)
        self.save_config()
        self.logger.info(f"Removed channel from monitoring: {channel}")
    
    async def get_channel_history(self, channel: str, limit: int = 100, days_back: int = None):
        """Get recent messages from a channel for analysis"""
        if TelegramClient is None:
            self.logger.error("Telethon not installed")
            return []
        
        if not self.client:
            # Use persistent session from sessions folder
            session_path = Path('sessions') / 'oneminuta_prod'
            if not session_path.parent.exists():
                session_path.parent.mkdir(exist_ok=True)
            session_name = str(session_path)
            self.client = TelegramClient(session_name, self.api_id, self.api_hash)
            
            # Start without prompting for auth - use existing session
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    self.logger.error("Not authorized! Run: ./telegram_analytics auth")
                    return []
            except Exception as e:
                self.logger.error(f"Session error: {e}. Run: ./telegram_analytics auth")
                return []
        
        try:
            entity = await self.client.get_entity(channel)
            messages = []
            
            # Calculate cutoff date if days_back is specified
            cutoff_date = None
            if days_back:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                self.logger.info(f"Filtering messages from last {days_back} days (since {cutoff_date.strftime('%Y-%m-%d')})")
            
            message_count = 0
            filtered_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text and message.sender:
                    # Check if message is within date range
                    if cutoff_date and message.date and message.date.replace(tzinfo=None) < cutoff_date:
                        self.logger.info(f"Reached cutoff date, stopping at {message.date.strftime('%Y-%m-%d %H:%M')}")
                        break
                    
                    # Filter out likely owner/listing messages - we only want member messages
                    if self.is_likely_owner_message(message.text):
                        filtered_count += 1
                        continue
                    
                    messages.append({
                        'user_id': str(message.sender.id),
                        'handle': f"@{message.sender.username}" if message.sender.username else None,
                        'text': message.text,
                        'date': message.date,
                        'message_id': message.id,
                        'is_member': True  # Mark as member message
                    })
                    message_count += 1
            
            if cutoff_date:
                self.logger.info(f"Collected {message_count} member messages from last {days_back} days (filtered out {filtered_count} listing messages)")
            else:
                self.logger.info(f"Collected {message_count} member messages (filtered out {filtered_count} listing messages)")
            
            return messages
        
        except Exception as e:
            self.logger.error(f"Error getting channel history: {e}")
            return []
    
    async def get_channel_all_messages(self, channel: str, limit: int = 100, days_back: int = None):
        """Get ALL messages from a channel (including owner/listing messages) for property collection"""
        if TelegramClient is None:
            self.logger.error("Telethon not installed")
            return []
        
        if not self.client:
            # Use persistent session from sessions folder
            session_path = Path('sessions') / 'oneminuta_prod'
            if not session_path.parent.exists():
                session_path.parent.mkdir(exist_ok=True)
            session_name = str(session_path)
            self.client = TelegramClient(session_name, self.api_id, self.api_hash)
            
            # Start without prompting for auth - use existing session
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    self.logger.error("Not authorized! Run: ./telegram_analytics auth")
                    return []
            except Exception as e:
                self.logger.error(f"Session error: {e}. Run: ./telegram_analytics auth")
                return []
        
        try:
            entity = await self.client.get_entity(channel)
            messages = []
            
            # Calculate cutoff date if days_back is specified
            cutoff_date = None
            if days_back:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                self.logger.info(f"Collecting ALL messages from last {days_back} days (since {cutoff_date.strftime('%Y-%m-%d')})")
            
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text and message.sender:
                    # Check if message is within date range
                    if cutoff_date and message.date and message.date.replace(tzinfo=None) < cutoff_date:
                        self.logger.info(f"Reached cutoff date, stopping at {message.date.strftime('%Y-%m-%d %H:%M')}")
                        break
                    
                    # Include ALL messages (no filtering for property collection)
                    messages.append({
                        'user_id': str(message.sender.id),
                        'handle': f"@{message.sender.username}" if message.sender.username else None,
                        'text': message.text,
                        'date': message.date,
                        'message_id': message.id,
                        'is_owner': self.is_likely_owner_message(message.text)  # Tag but don't filter
                    })
                    message_count += 1
            
            if cutoff_date:
                self.logger.info(f"Collected {message_count} total messages from last {days_back} days (no filtering)")
            else:
                self.logger.info(f"Collected {message_count} total messages (no filtering)")
            
            return messages
        
        except Exception as e:
            self.logger.error(f"Error getting all channel messages for {channel}: {e}")
            return []
    
    async def analyze_channel_history(self, channel: str, limit: int = 1000, days_back: int = None):
        """Analyze historical messages from a channel"""
        if days_back:
            self.logger.info(f"Analyzing history for {channel} (last {days_back} days, max {limit} messages)")
        else:
            self.logger.info(f"Analyzing history for {channel} (limit: {limit})")
        
        messages = await self.get_channel_history(channel, limit, days_back)
        
        for msg in messages:
            signals = await self.analyzer.analyze_message(
                user_id=msg['user_id'],
                message=msg['text'],
                timestamp=msg['date'],
                channel=channel,
                message_id=msg['message_id']
            )
            
            if signals:
                await self.analyzer.update_client_profile(msg['user_id'], signals)
        
        self.logger.info(f"Analyzed {len(messages)} messages from {channel}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self.client:
            self.client.disconnect()
        self.logger.info("Monitoring stopped")


class ClientAlertSystem:
    """Alert system for hot property clients"""
    
    def __init__(self, storage_path: str, webhook_url: Optional[str] = None):
        self.storage_path = Path(storage_path)
        self.webhook_url = webhook_url
        self.analyzer = PropertyClientAnalyzer(storage_path)
        
        # Alert thresholds
        self.hot_threshold = 70.0
        self.burning_threshold = 85.0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def check_for_alerts(self):
        """Check for clients that need immediate attention"""
        hot_clients = await self.analyzer.get_hot_clients(min_score=self.hot_threshold)
        
        alerts = []
        
        for client in hot_clients:
            # Check if this is a new hot client (first time crossing threshold)
            if await self.is_new_hot_client(client):
                alert = await self.create_alert(client)
                alerts.append(alert)
        
        return alerts
    
    async def is_new_hot_client(self, client) -> bool:
        """Check if client recently became hot"""
        # Look at previous scores in signal history
        recent_signals = [s for s in client.signals[-10:] 
                         if s.signal_type.value in ['urgent_signal', 'viewing_request', 'budget_mention']]
        
        # If they have multiple high-value signals in last few messages, they're newly hot
        return len(recent_signals) >= 2
    
    async def create_alert(self, client) -> Dict:
        """Create alert for hot client"""
        alert = {
            'alert_id': f"alert_{client.user_id}_{datetime.utcnow().timestamp()}",
            'user_id': client.user_id,
            'handle': client.handle,
            'score': client.total_score,
            'hotness_level': client.hotness_level.value,
            'alert_type': 'burning_client' if client.total_score >= self.burning_threshold else 'hot_client',
            'timestamp': datetime.utcnow().isoformat(),
            'key_signals': [
                {
                    'type': s.signal_type.value,
                    'content': s.content[:100],  # Truncate
                    'timestamp': s.timestamp.isoformat()
                }
                for s in client.signals[-3:]  # Last 3 signals
            ],
            'preferences': {
                'budget_range': client.budget_range,
                'locations': list(client.preferred_locations),
                'message_frequency': client.message_frequency
            },
            'recommended_actions': self.get_recommended_actions(client)
        }
        
        # Save alert
        alert_path = self.storage_path / "analytics" / "alerts.ndjson"
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(alert_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')
        
        # Send webhook notification if configured
        if self.webhook_url:
            await self.send_webhook_alert(alert)
        
        return alert
    
    def get_recommended_actions(self, client) -> List[str]:
        """Get recommended actions for engaging with hot client"""
        actions = []
        
        if client.total_score >= self.burning_threshold:
            actions.append("🔥 URGENT: Contact within 1 hour")
            actions.append("📞 Call directly if phone number available")
        elif client.total_score >= self.hot_threshold:
            actions.append("⚡ High priority: Contact within 4 hours")
            actions.append("💬 Send personalized message")
        
        # Specific recommendations based on signals
        signal_types = [s.signal_type.value for s in client.signals[-5:]]
        
        if 'viewing_request' in signal_types:
            actions.append("🏠 Schedule property viewing ASAP")
        
        if 'budget_mention' in signal_types:
            actions.append("💰 Prepare properties matching their budget")
        
        if 'urgent_signal' in signal_types:
            actions.append("⏰ Emphasize immediate availability")
        
        if client.preferred_locations:
            actions.append(f"📍 Focus on: {', '.join(list(client.preferred_locations)[:3])}")
        
        return actions
    
    async def send_webhook_alert(self, alert: Dict):
        """Send alert via webhook (e.g., to Slack, Discord, etc.)"""
        try:
            import aiohttp
            
            payload = {
                'text': f"🚨 Hot Property Client Alert",
                'attachments': [{
                    'color': 'danger' if alert['alert_type'] == 'burning_client' else 'warning',
                    'fields': [
                        {'title': 'Client', 'value': alert['handle'] or alert['user_id'], 'short': True},
                        {'title': 'Score', 'value': f"{alert['score']:.1f}", 'short': True},
                        {'title': 'Level', 'value': alert['hotness_level'].upper(), 'short': True},
                        {'title': 'Actions', 'value': '\n'.join(alert['recommended_actions'][:3]), 'short': False}
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert sent via webhook for {alert['user_id']}")
                    else:
                        self.logger.error(f"Webhook failed: {response.status}")
        
        except Exception as e:
            self.logger.error(f"Error sending webhook: {e}")


# CLI functions for testing and management
async def main():
    """Main function for testing the monitor"""
    import os
    
    # Get credentials from environment
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    storage_path = os.getenv('STORAGE_PATH', './storage')
    
    if not api_id or not api_hash:
        print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables")
        return
    
    monitor = TelegramPropertyMonitor(int(api_id), api_hash, storage_path)
    
    # For testing, analyze some channel history first
    await monitor.analyze_channel_history('@thailand_property', limit=100)
    
    # Get hot clients
    hot_clients = await monitor.analyzer.get_hot_clients(min_score=50.0)
    print(f"Found {len(hot_clients)} hot clients")
    
    for client in hot_clients[:5]:  # Show top 5
        print(f"Client: {client.handle or client.user_id}")
        print(f"Score: {client.total_score:.1f}")
        print(f"Level: {client.hotness_level.value}")
        print(f"Locations: {list(client.preferred_locations)}")
        print(f"Budget: {client.budget_range}")
        print("---")


if __name__ == "__main__":
    asyncio.run(main())