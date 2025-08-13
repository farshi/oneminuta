"""
Property Client Analysis System for OneMinuta
Analyzes Telegram users to identify hot property clients based on behavior patterns
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
from enum import Enum

from specs.schemas.models import AssetType, RentOrSale, Location


class ClientHotness(str, Enum):
    """Client hotness levels"""
    COLD = "cold"           # Score 0-30: Passive browsers
    WARM = "warm"           # Score 31-60: Interested but not urgent
    HOT = "hot"             # Score 61-85: Active searchers
    BURNING = "burning"     # Score 86-100: Urgent buyers/renters


class EngagementType(str, Enum):
    """Types of user engagement"""
    MESSAGE = "message"
    QUESTION = "question"
    PRICE_INQUIRY = "price_inquiry"
    VIEWING_REQUEST = "viewing_request"
    CONTACT_REQUEST = "contact_request"
    URGENT_SIGNAL = "urgent_signal"
    BUDGET_MENTION = "budget_mention"
    LOCATION_PREFERENCE = "location_preference"


@dataclass
class ClientSignal:
    """Individual client engagement signal"""
    user_id: str
    signal_type: EngagementType
    content: str
    timestamp: datetime
    channel: str
    message_id: Optional[int] = None
    confidence: float = 1.0  # 0-1 confidence in signal accuracy
    extracted_data: Dict = None  # Parsed data like price, location, etc.


@dataclass
class ClientProfile:
    """Comprehensive client profile"""
    user_id: str
    handle: Optional[str]
    total_score: float
    hotness_level: ClientHotness
    signals: List[ClientSignal]
    first_seen: datetime
    last_active: datetime
    
    # Extracted preferences
    budget_range: Optional[Tuple[float, float]] = None
    preferred_locations: Set[str] = None
    asset_preferences: Set[AssetType] = None
    rent_or_sale: Optional[RentOrSale] = None
    
    # Behavioral metrics
    message_frequency: float = 0.0  # Messages per day
    question_ratio: float = 0.0     # Questions / total messages
    urgency_indicators: int = 0     # Count of urgent keywords
    response_speed: float = 0.0     # Average response time in minutes
    
    # Engagement quality
    engagement_depth: float = 0.0   # Length and detail of messages
    property_specific: float = 0.0  # How property-focused are messages
    
    def __post_init__(self):
        if self.preferred_locations is None:
            self.preferred_locations = set()
        if self.asset_preferences is None:
            self.asset_preferences = set()


class PropertyClientAnalyzer:
    """Main analyzer for identifying hot property clients"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.analytics_path = self.storage_path / "analytics"
        self.analytics_path.mkdir(exist_ok=True)
        
        # Keywords for different signal types
        self.urgency_keywords = {
            'en': ['urgent', 'asap', 'immediately', 'cash ready', 'today', 'this week', 'fast'],
            'ru': ['срочно', 'готов покупать', 'наличные готовы', 'сегодня', 'на этой неделе', 'быстро']
        }
        
        self.budget_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|mil|m|k|thousand|миллион|тысяч)',
            r'budget[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'up\s+to[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'around[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:\$|€|£|руб|рублей)',
            r'бюджет[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'до[:\s]+(\d+(?:,\d{3})*(?:\.\d+)?)'
        ]
        
        self.viewing_keywords = {
            'en': ['viewing', 'visit', 'see the property', 'schedule', 'appointment', 'when can i'],
            'ru': ['посмотреть', 'осмотр', 'показ', 'встреча', 'когда можно', 'договориться']
        }
        
        self.question_indicators = ['?', 'how', 'what', 'when', 'where', 'why', 'can you', 'is it', 'как', 'что', 'когда', 'где', 'почему', 'можете ли']
        
    async def analyze_message(self, user_id: str, message: str, 
                            timestamp: datetime, channel: str, 
                            message_id: Optional[int] = None) -> List[ClientSignal]:
        """Analyze a single message and extract client signals"""
        signals = []
        message_lower = message.lower()
        
        # Basic message signal
        signals.append(ClientSignal(
            user_id=user_id,
            signal_type=EngagementType.MESSAGE,
            content=message,
            timestamp=timestamp,
            channel=channel,
            message_id=message_id
        ))
        
        # Check for questions
        if any(indicator in message_lower for indicator in self.question_indicators):
            signals.append(ClientSignal(
                user_id=user_id,
                signal_type=EngagementType.QUESTION,
                content=message,
                timestamp=timestamp,
                channel=channel,
                message_id=message_id,
                confidence=0.8
            ))
        
        # Check for urgent signals
        for lang, keywords in self.urgency_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                signals.append(ClientSignal(
                    user_id=user_id,
                    signal_type=EngagementType.URGENT_SIGNAL,
                    content=message,
                    timestamp=timestamp,
                    channel=channel,
                    message_id=message_id,
                    confidence=0.9
                ))
                break
        
        # Extract budget mentions
        budget_data = self._extract_budget(message)
        if budget_data:
            signals.append(ClientSignal(
                user_id=user_id,
                signal_type=EngagementType.BUDGET_MENTION,
                content=message,
                timestamp=timestamp,
                channel=channel,
                message_id=message_id,
                confidence=0.85,
                extracted_data=budget_data
            ))
        
        # Check for viewing requests
        for lang, keywords in self.viewing_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                signals.append(ClientSignal(
                    user_id=user_id,
                    signal_type=EngagementType.VIEWING_REQUEST,
                    content=message,
                    timestamp=timestamp,
                    channel=channel,
                    message_id=message_id,
                    confidence=0.95
                ))
                break
        
        # Extract location preferences
        location_data = self._extract_locations(message)
        if location_data:
            signals.append(ClientSignal(
                user_id=user_id,
                signal_type=EngagementType.LOCATION_PREFERENCE,
                content=message,
                timestamp=timestamp,
                channel=channel,
                message_id=message_id,
                confidence=0.7,
                extracted_data=location_data
            ))
        
        return signals
    
    def _extract_budget(self, message: str) -> Optional[Dict]:
        """Extract budget information from message"""
        for pattern in self.budget_patterns:
            match = re.search(pattern, message.lower())
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    
                    # Normalize to THB
                    if 'million' in message.lower() or 'mil' in message.lower() or 'ล้าน' in message:
                        amount *= 1_000_000
                    elif 'k' in message.lower() or 'thousand' in message.lower() or 'พัน' in message:
                        amount *= 1_000
                    
                    return {
                        'amount': amount,
                        'currency': 'THB',
                        'raw_text': match.group(0)
                    }
                except ValueError:
                    continue
        return None
    
    def _extract_locations(self, message: str) -> Optional[Dict]:
        """Extract location preferences from message"""
        # Common Thailand locations
        thai_locations = [
            'bangkok', 'phuket', 'pattaya', 'chiang mai', 'hua hin', 'koh samui',
            'rawai', 'kata', 'patong', 'nai harn', 'bang tao', 'surin',
            'sukhumvit', 'silom', 'sathorn', 'phrom phong', 'thonglor', 'ekkamai',
            'สุขุมวิท', 'สีลม', 'สาทร', 'ภูเก็ต', 'พัทยา', 'หัวหิน'
        ]
        
        found_locations = []
        message_lower = message.lower()
        
        for location in thai_locations:
            if location in message_lower:
                found_locations.append(location)
        
        if found_locations:
            return {'locations': found_locations}
        return None
    
    async def calculate_client_score(self, profile: ClientProfile) -> float:
        """Calculate comprehensive client hotness score (0-100)"""
        score = 0.0
        
        # Recent activity weight (40% max)
        recent_activity = self._calculate_recent_activity_score(profile)
        score += recent_activity * 0.4
        
        # Engagement quality (25% max)
        engagement_score = self._calculate_engagement_score(profile)
        score += engagement_score * 0.25
        
        # Intent signals (20% max)
        intent_score = self._calculate_intent_score(profile)
        score += intent_score * 0.2
        
        # Urgency indicators (15% max)
        urgency_score = self._calculate_urgency_score(profile)
        score += urgency_score * 0.15
        
        return min(100.0, max(0.0, score))
    
    def _calculate_recent_activity_score(self, profile: ClientProfile) -> float:
        """Calculate score based on recent activity (0-100)"""
        now = datetime.utcnow()
        
        # Messages in last 24 hours (handle timezone-aware timestamps)
        recent_messages = []
        for s in profile.signals:
            try:
                # Handle both timezone-aware and naive timestamps
                timestamp = s.timestamp
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    # Convert timezone-aware to UTC naive
                    timestamp = timestamp.replace(tzinfo=None)
                
                if (now - timestamp).total_seconds() < 86400:
                    recent_messages.append(s)
            except (TypeError, AttributeError):
                # Skip signals with invalid timestamps
                continue
        
        if not recent_messages:
            return 0.0
        
        # Base score from message frequency
        daily_frequency = len(recent_messages)
        frequency_score = min(50.0, daily_frequency * 10)  # Max 50 points
        
        # Bonus for consistent activity over multiple days
        days_active = []
        for s in profile.signals[-20:]:
            try:
                timestamp = s.timestamp
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                days_active.append((now - timestamp).days)
            except (TypeError, AttributeError):
                continue
        
        days_active = len(set(days_active))
        consistency_bonus = min(25.0, days_active * 5)  # Max 25 points
        
        # Bonus for very recent activity (last 4 hours)
        very_recent = []
        for s in recent_messages:
            try:
                timestamp = s.timestamp
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                if (now - timestamp).total_seconds() < 14400:
                    very_recent.append(s)
            except (TypeError, AttributeError):
                continue
        recency_bonus = min(25.0, len(very_recent) * 8)  # Max 25 points
        
        return frequency_score + consistency_bonus + recency_bonus
    
    def _get_signal_type(self, signal):
        """Helper to get signal type from both dict and object signals"""
        if hasattr(signal, 'signal_type'):
            return signal.signal_type
        elif isinstance(signal, dict):
            return signal.get('signal_type')
        return None
    
    def _get_signal_content(self, signal):
        """Helper to get signal content from both dict and object signals"""
        if hasattr(signal, 'content'):
            return signal.content or ""
        elif isinstance(signal, dict):
            return signal.get('content', "")
        return ""
    
    def _calculate_engagement_score(self, profile: ClientProfile) -> float:
        """Calculate engagement quality score (0-100)"""
        if not profile.signals:
            return 0.0
        
        # Question ratio (asking questions shows interest)
        questions = [s for s in profile.signals if self._get_signal_type(s) == EngagementType.QUESTION]
        question_ratio = len(questions) / len(profile.signals)
        question_score = min(40.0, question_ratio * 100)  # Max 40 points
        
        # Message length and detail
        avg_length = sum(len(self._get_signal_content(s)) for s in profile.signals) / len(profile.signals)
        detail_score = min(30.0, avg_length / 10)  # Max 30 points
        
        # Property-specific engagement
        property_signals = [s for s in profile.signals 
                           if self._get_signal_type(s) in [EngagementType.BUDGET_MENTION, 
                                                          EngagementType.VIEWING_REQUEST,
                                                          EngagementType.LOCATION_PREFERENCE]]
        property_ratio = len(property_signals) / len(profile.signals)
        property_score = min(30.0, property_ratio * 100)  # Max 30 points
        
        return question_score + detail_score + property_score
    
    def _calculate_intent_score(self, profile: ClientProfile) -> float:
        """Calculate purchase/rental intent score (0-100)"""
        intent_signals = [
            EngagementType.BUDGET_MENTION,
            EngagementType.VIEWING_REQUEST,
            EngagementType.CONTACT_REQUEST
        ]
        
        intent_count = sum(1 for s in profile.signals if self._get_signal_type(s) in intent_signals)
        
        # Strong intent signals get high scores
        base_score = min(60.0, intent_count * 20)  # Max 60 points
        
        # Bonus for budget clarity
        budget_signals = [s for s in profile.signals 
                         if self._get_signal_type(s) == EngagementType.BUDGET_MENTION]
        if budget_signals:
            base_score += 25.0  # Max 25 points bonus
        
        # Bonus for viewing requests
        viewing_signals = [s for s in profile.signals 
                          if self._get_signal_type(s) == EngagementType.VIEWING_REQUEST]
        if viewing_signals:
            base_score += 15.0  # Max 15 points bonus
        
        return min(100.0, base_score)
    
    def _calculate_urgency_score(self, profile: ClientProfile) -> float:
        """Calculate urgency score (0-100)"""
        urgent_signals = [s for s in profile.signals 
                         if self._get_signal_type(s) == EngagementType.URGENT_SIGNAL]
        
        if not urgent_signals:
            return 0.0
        
        # Recent urgency signals are weighted more
        now = datetime.utcnow()
        recent_urgent = []
        for s in urgent_signals:
            try:
                timestamp = s.timestamp
                if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                if (now - timestamp).total_seconds() < 86400:
                    recent_urgent.append(s)
            except (TypeError, AttributeError):
                continue
        
        # Base urgency score
        urgency_count = len(urgent_signals)
        base_score = min(60.0, urgency_count * 30)  # Max 60 points
        
        # Bonus for recent urgency
        if recent_urgent:
            recency_bonus = min(40.0, len(recent_urgent) * 20)  # Max 40 points
            base_score += recency_bonus
        
        return min(100.0, base_score)
    
    def _determine_hotness_level(self, score: float) -> ClientHotness:
        """Determine client hotness level from score"""
        if score >= 86:
            return ClientHotness.BURNING
        elif score >= 61:
            return ClientHotness.HOT
        elif score >= 31:
            return ClientHotness.WARM
        else:
            return ClientHotness.COLD
    
    async def update_client_profile(self, user_id: str, signals: List[ClientSignal]) -> ClientProfile:
        """Update or create client profile with new signals"""
        profile_path = self.analytics_path / f"client_{user_id}.json"
        
        # Load existing profile or create new
        if profile_path.exists():
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                profile = ClientProfile(**data)
        else:
            profile = ClientProfile(
                user_id=user_id,
                handle=None,
                total_score=0.0,
                hotness_level=ClientHotness.COLD,
                signals=[],
                first_seen=datetime.utcnow(),
                last_active=datetime.utcnow()
            )
        
        # Add new signals
        profile.signals.extend(signals)
        profile.last_active = max(s.timestamp for s in signals) if signals else profile.last_active
        
        # Keep only last 100 signals to prevent unlimited growth
        profile.signals = profile.signals[-100:]
        
        # Update extracted preferences
        self._update_preferences(profile)
        
        # Recalculate score and hotness
        profile.total_score = await self.calculate_client_score(profile)
        profile.hotness_level = self._determine_hotness_level(profile.total_score)
        
        # Save updated profile
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(profile), f, default=str, indent=2, ensure_ascii=False)
        
        return profile
    
    def _update_preferences(self, profile: ClientProfile):
        """Update client preferences based on signals"""
        # Extract budget range (handle both dict and object signals)
        budget_signals = []
        for s in profile.signals:
            try:
                # Handle both ClientSignal objects and dict data
                signal_type = s.signal_type if hasattr(s, 'signal_type') else s.get('signal_type')
                extracted_data = s.extracted_data if hasattr(s, 'extracted_data') else s.get('extracted_data')
                
                if signal_type == EngagementType.BUDGET_MENTION and extracted_data:
                    budget_signals.append({'extracted_data': extracted_data})
            except (AttributeError, TypeError):
                continue
        
        if budget_signals:
            amounts = [s['extracted_data']['amount'] for s in budget_signals]
            profile.budget_range = (min(amounts), max(amounts))
        
        # Extract preferred locations (handle both dict and object signals)
        for s in profile.signals:
            try:
                signal_type = s.signal_type if hasattr(s, 'signal_type') else s.get('signal_type')
                extracted_data = s.extracted_data if hasattr(s, 'extracted_data') else s.get('extracted_data')
                
                if signal_type == EngagementType.LOCATION_PREFERENCE and extracted_data:
                    if 'locations' in extracted_data:
                        profile.preferred_locations.update(extracted_data['locations'])
            except (AttributeError, TypeError):
                continue
    
    async def get_hot_clients(self, min_score: float = 61.0, limit: int = 50) -> List[ClientProfile]:
        """Get list of hot clients sorted by score"""
        hot_clients = []
        
        for profile_file in self.analytics_path.glob("client_*.json"):
            with open(profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                profile = ClientProfile(**data)
                
                if profile.total_score >= min_score:
                    hot_clients.append(profile)
        
        # Sort by score descending
        hot_clients.sort(key=lambda p: p.total_score, reverse=True)
        
        return hot_clients[:limit]
    
    async def generate_daily_report(self) -> Dict:
        """Generate daily analytics report"""
        all_clients = []
        
        for profile_file in self.analytics_path.glob("client_*.json"):
            with open(profile_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_clients.append(ClientProfile(**data))
        
        # Statistics by hotness level
        stats_by_level = {}
        for level in ClientHotness:
            clients_at_level = [c for c in all_clients if c.hotness_level == level]
            stats_by_level[level.value] = {
                'count': len(clients_at_level),
                'avg_score': sum(c.total_score for c in clients_at_level) / len(clients_at_level) if clients_at_level else 0
            }
        
        # Top locations
        all_locations = []
        for client in all_clients:
            all_locations.extend(client.preferred_locations)
        
        location_counts = {}
        for loc in all_locations:
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Budget ranges
        budget_ranges = [c.budget_range for c in all_clients if c.budget_range]
        avg_min_budget = sum(r[0] for r in budget_ranges) / len(budget_ranges) if budget_ranges else 0
        avg_max_budget = sum(r[1] for r in budget_ranges) / len(budget_ranges) if budget_ranges else 0
        
        return {
            'total_clients': len(all_clients),
            'stats_by_level': stats_by_level,
            'top_locations': top_locations,
            'avg_budget_range': {
                'min': avg_min_budget,
                'max': avg_max_budget
            },
            'generated_at': datetime.utcnow().isoformat()
        }