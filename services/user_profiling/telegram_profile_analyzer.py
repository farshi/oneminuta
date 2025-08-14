"""
Telegram Profile Analyzer - Smart User Profiling from Telegram Bio/Profile
Detects language, nationality, communication style from user's Telegram profile
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class UserProfile:
    """User profile detected from Telegram data"""
    user_id: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    
    # Detected characteristics
    primary_language: str  # en, ru, th
    secondary_languages: List[str]
    nationality: Optional[str]  # RU, US, UK, TH, etc.
    communication_style: str  # formal, casual, business
    
    # Profile analysis
    bio_text: Optional[str]
    name_language: str  # Language detected from name
    profile_completeness: float  # 0-1 score
    
    # Behavioral indicators
    likely_investor: bool
    likely_local: bool
    likely_expat: bool
    
    # Metadata
    analyzed_at: datetime
    confidence_score: float  # 0-1 overall confidence


class TelegramProfileAnalyzer:
    """Analyzes Telegram user profiles for smart personalization"""
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.profiles_path = self.storage_path / "user_profiles"
        self.profiles_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Language detection patterns
        self.language_patterns = {
            "ru": [
                r"[а-яё]",  # Cyrillic characters
                r"\b(привет|здравствуйте|спасибо|пожалуйста|хорошо|недвижимость|квартира|дом)\b",
                r"[А-ЯЁ][а-яё]+"  # Capitalized Cyrillic words
            ],
            "th": [
                r"[\u0e00-\u0e7f]",  # Thai characters
                r"\b(สวัสดี|ขอบคุณ|บ้าน|คอนโด)\b"
            ],
            "en": [
                r"\b(hello|hi|thank|please|good|property|house|condo|apartment)\b",
                r"^[A-Za-z\s]+$"  # Only Latin characters and spaces
            ]
        }
        
        # Name patterns for nationality detection
        self.name_patterns = {
            "RU": [
                r"(ov|ova|ev|eva|in|ina|sky|skaya|enko|uk)$",  # Russian surnames
                r"^(Александр|Владимир|Анна|Елена|Ирина|Сергей|Николай|Мария)",  # Russian first names
                r"[а-яё]"  # Any Cyrillic
            ],
            "UK": [
                r"\b(Smith|Johnson|Williams|Brown|Jones|Miller|Davis|Wilson|Taylor|Clark)\b",
                r"^(James|John|Robert|Michael|William|David|Richard|Thomas|Sarah|Emma|Emma)\b"
            ],
            "DE": [
                r"(mann|berg|stein|haus|muller|schmidt)$",
                r"^(Hans|Klaus|Wolfgang|Greta|Ingrid|Helga)\b"
            ],
            "TH": [
                r"[\u0e00-\u0e7f]",  # Thai script
                r"\b(Somchai|Siriporn|Wichai|Malee|Prasert)\b"
            ]
        }
        
        # Communication style indicators
        self.style_indicators = {
            "formal": [
                r"\b(please|kindly|would|could|may i|thank you|regards)\b",
                r"[.]{2,}|!{2,}",  # Multiple punctuation
                r"\b(sir|madam|mr|mrs|ms)\b"
            ],
            "casual": [
                r"\b(hey|hi|thanks|thx|gonna|wanna|yeah|yep|cool|awesome)\b",
                r"[😀-🙏]",  # Emoji ranges
                r"\b(lol|omg|btw|fyi)\b"
            ],
            "business": [
                r"\b(investment|roi|portfolio|profit|revenue|business|opportunity)\b",
                r"\b(meeting|schedule|proposal|contract|deal)\b"
            ]
        }
    
    async def analyze_user_profile(self, user, bio: str = None, 
                                  conversation_history: List[str] = None) -> UserProfile:
        """Analyze user profile from Telegram user object and optional data"""
        
        user_id = str(user.id)
        
        # Check cache first
        cached_profile = await self._load_cached_profile(user_id)
        if cached_profile:
            self.logger.info(f"Using cached profile for user {user_id}")
            return cached_profile
        
        # Analyze name
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        name_language = self._detect_language_from_text(full_name)
        nationality = self._detect_nationality_from_name(full_name)
        
        # Analyze bio if available
        bio_text = bio or ""
        bio_language = self._detect_language_from_text(bio_text) if bio_text else name_language
        
        # Determine primary language (bio takes precedence over name)
        primary_language = bio_language if bio_text else name_language
        
        # Analyze conversation history if available
        conversation_language = None
        if conversation_history:
            combined_text = " ".join(conversation_history[-5:])  # Last 5 messages
            conversation_language = self._detect_language_from_text(combined_text)
            primary_language = conversation_language  # Most recent and accurate
        
        # Detect communication style
        style_text = f"{full_name} {bio_text} {' '.join(conversation_history or [])}"
        communication_style = self._detect_communication_style(style_text)
        
        # Detect behavioral indicators
        behavioral_indicators = self._analyze_behavioral_indicators(style_text)
        
        # Calculate confidence and completeness
        confidence_score = self._calculate_confidence(user, bio_text, conversation_history)
        completeness = self._calculate_completeness(user, bio_text)
        
        profile = UserProfile(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            
            primary_language=primary_language,
            secondary_languages=self._detect_secondary_languages(style_text, primary_language),
            nationality=nationality,
            communication_style=communication_style,
            
            bio_text=bio_text,
            name_language=name_language,
            profile_completeness=completeness,
            
            likely_investor=behavioral_indicators["investor"],
            likely_local=behavioral_indicators["local"],
            likely_expat=behavioral_indicators["expat"],
            
            analyzed_at=datetime.now(timezone.utc),
            confidence_score=confidence_score
        )
        
        # Cache the profile
        await self._cache_profile(profile)
        
        self.logger.info(f"Analyzed profile for {user_id}: {primary_language} speaker, {communication_style} style, {confidence_score:.2f} confidence")
        
        return profile
    
    def _detect_language_from_text(self, text: str) -> str:
        """Detect primary language from text"""
        if not text:
            return "en"  # Default to English
        
        text_lower = text.lower()
        scores = {"en": 0, "ru": 0, "th": 0}
        
        for lang, patterns in self.language_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                scores[lang] += matches
        
        # Return language with highest score
        detected = max(scores, key=scores.get)
        
        # If no clear winner, check character composition
        if scores[detected] == 0:
            if re.search(r"[а-яё]", text_lower):
                return "ru"
            elif re.search(r"[\u0e00-\u0e7f]", text_lower):
                return "th"
            else:
                return "en"
        
        return detected
    
    def _detect_nationality_from_name(self, name: str) -> Optional[str]:
        """Detect likely nationality from name patterns"""
        if not name:
            return None
        
        for nationality, patterns in self.name_patterns.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    return nationality
        
        return None
    
    def _detect_communication_style(self, text: str) -> str:
        """Detect communication style from text patterns"""
        if not text:
            return "casual"
        
        text_lower = text.lower()
        scores = {"formal": 0, "casual": 0, "business": 0}
        
        for style, patterns in self.style_indicators.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                scores[style] += matches
        
        # Return style with highest score, default to casual
        return max(scores, key=scores.get) if any(scores.values()) else "casual"
    
    def _analyze_behavioral_indicators(self, text: str) -> Dict[str, bool]:
        """Analyze behavioral indicators from text"""
        text_lower = text.lower()
        
        # Investment-related keywords
        investment_keywords = r"\b(invest|investment|roi|profit|return|portfolio|business|buy to let|rental income)\b"
        likely_investor = bool(re.search(investment_keywords, text_lower))
        
        # Local indicators (Thai language, local knowledge)
        local_keywords = r"[\u0e00-\u0e7f]|\b(baht|THB|BTS|MRT|soi|amphur|tambon)\b"
        likely_local = bool(re.search(local_keywords, text_lower))
        
        # Expat indicators (foreign name but interested in Thailand)
        likely_expat = (
            not likely_local and 
            bool(re.search(r"\b(expat|foreigner|visa|work permit|retirement|living in|moved to)\b", text_lower))
        )
        
        return {
            "investor": likely_investor,
            "local": likely_local,
            "expat": likely_expat
        }
    
    def _detect_secondary_languages(self, text: str, primary: str) -> List[str]:
        """Detect secondary languages user might speak"""
        secondary = []
        
        for lang in ["en", "ru", "th"]:
            if lang != primary:
                score = 0
                for pattern in self.language_patterns[lang]:
                    score += len(re.findall(pattern, text.lower(), re.IGNORECASE))
                if score > 0:
                    secondary.append(lang)
        
        return secondary
    
    def _calculate_confidence(self, user, bio: str, conversation: List[str]) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 0.3  # Base confidence
        
        # Name available
        if user.first_name:
            confidence += 0.1
        if user.last_name:
            confidence += 0.1
        
        # Bio available and substantial
        if bio and len(bio) > 20:
            confidence += 0.2
        elif bio:
            confidence += 0.1
        
        # Conversation history available
        if conversation and len(conversation) >= 3:
            confidence += 0.3
        elif conversation:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_completeness(self, user, bio: str) -> float:
        """Calculate profile completeness score"""
        completeness = 0.0
        
        if user.first_name:
            completeness += 0.3
        if user.last_name:
            completeness += 0.2
        if user.username:
            completeness += 0.2
        if bio and len(bio) > 10:
            completeness += 0.3
        
        return completeness
    
    async def _load_cached_profile(self, user_id: str) -> Optional[UserProfile]:
        """Load cached profile if recent enough"""
        profile_file = self.profiles_path / f"{user_id}.json"
        
        if not profile_file.exists():
            return None
        
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if cache is recent (within 7 days)
            analyzed_at = datetime.fromisoformat(data["analyzed_at"])
            if (datetime.now(timezone.utc) - analyzed_at).days > 7:
                return None
            
            # Convert back to UserProfile
            data["analyzed_at"] = analyzed_at
            return UserProfile(**data)
            
        except (json.JSONDecodeError, KeyError, TypeError):
            self.logger.warning(f"Invalid cached profile for user {user_id}")
            return None
    
    async def _cache_profile(self, profile: UserProfile) -> None:
        """Cache user profile for future use"""
        profile_file = self.profiles_path / f"{profile.user_id}.json"
        
        profile_data = asdict(profile)
        profile_data["analyzed_at"] = profile.analyzed_at.isoformat()
        
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    async def get_greeting_for_profile(self, profile: UserProfile, 
                                      last_seen_days: int = 0, 
                                      last_search_topic: str = None) -> str:
        """Generate personalized greeting based on profile and history"""
        
        # Base greetings by language
        greetings = {
            "en": {
                "new": "Hello! Welcome to OneMinuta. May I know how I can help with your property search?",
                "returning_recent": "Hello! How's your property search going?",
                "returning_old": "Long time no see! Any updates on your property search?",
                "formal": "Good day! How may I assist you with your property requirements?",
                "business": "Hello! Are you looking for investment opportunities or properties for business use?"
            },
            "ru": {
                "new": "Привет! Добро пожаловать в OneMinuta. Чем могу помочь с поиском недвижимости?",
                "returning_recent": "Привет! Как дела с поиском недвижимости?",
                "returning_old": "Давно не виделись! Есть новости по поиску недвижимости?",
                "formal": "Добро пожаловать! Как я могу помочь с недвижимостью?",
                "business": "Здравствуйте! Ищете инвестиционные возможности или коммерческую недвижимость?"
            },
            "th": {
                "new": "สวัสดีครับ! ยินดีต้อนรับสู่ OneMinuta ช่วยอะไรเรื่องอสังหาริมทรัพย์ได้บ้างครับ?",
                "returning_recent": "สวัสดีครับ! เป็นอย่างไรบ้างกับการหาบ้าน?",
                "returning_old": "นานแล้วนะครับ! มีอัพเดทเรื่องการหาบ้านไหมครับ?",
                "formal": "สวัสดีครับ! ช่วยเรื่องอสังหาริมทรัพย์อะไรได้บ้างครับ?",
                "business": "สวัสดีครับ! กำลังหาโอกาสลงทุนหรือทรัพย์สินเชิงธุรกิจครับ?"
            }
        }
        
        lang = profile.primary_language
        lang_greetings = greetings.get(lang, greetings["en"])
        
        # Choose greeting based on context
        if last_seen_days == 0:  # New user
            if profile.communication_style == "formal":
                greeting = lang_greetings["formal"]
            elif profile.likely_investor or profile.communication_style == "business":
                greeting = lang_greetings["business"]
            else:
                greeting = lang_greetings["new"]
        
        elif last_seen_days > 30:  # Long time user
            greeting = lang_greetings["returning_old"]
        
        else:  # Recent user
            greeting = lang_greetings["returning_recent"]
            
            # Add context if we know what they were searching for
            if last_search_topic:
                search_context = {
                    "en": f" Still looking for {last_search_topic}?",
                    "ru": f" Все еще ищете {last_search_topic}?",
                    "th": f" ยังหา{last_search_topic}อยู่ไหมครับ?"
                }
                greeting += search_context.get(lang, search_context["en"])
        
        return greeting