"""
LLM-based Property Client Analysis for OneMinuta
Uses GPT/LLM to analyze client messages for property intent and hotness
Supports English and Russian languages
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

try:
    import openai
except ImportError:
    openai = None

from services.core.models import AssetType, RentOrSale


@dataclass
class LLMClientAnalysis:
    """LLM analysis result for a client"""
    user_id: str
    hotness_score: float  # 0-100
    hotness_level: str  # "cold", "warm", "hot", "burning"
    
    # Intent analysis
    primary_intent: str  # "buying", "renting", "selling", "browsing"
    intent_confidence: float  # 0-1
    urgency_level: str  # "low", "medium", "high", "urgent"
    
    # Property preferences (extracted)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "USD"
    preferred_locations: List[str] = None
    asset_types: List[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    
    # Behavioral indicators
    financing_ready: bool = False
    wants_viewing: bool = False
    wants_contact: bool = False
    timeline: Optional[str] = None  # "immediate", "this_week", "this_month", "flexible"
    
    # Analysis metadata
    language_detected: str = "en"
    confidence: float = 0.0  # Overall analysis confidence
    key_phrases: List[str] = None
    reasoning: str = ""
    
    def __post_init__(self):
        if self.preferred_locations is None:
            self.preferred_locations = []
        if self.asset_types is None:
            self.asset_types = []
        if self.key_phrases is None:
            self.key_phrases = []


class LLMPropertyAnalyzer:
    """LLM-based analyzer for property client messages"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", storage_path: str = "./storage"):
        self.api_key = api_key
        self.model = model
        self.storage_path = Path(storage_path)
        
        # Initialize OpenAI client
        if openai:
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
        else:
            self.openai_client = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Create analysis prompt templates
        self.setup_prompts()
    
    def setup_prompts(self):
        """Setup LLM prompts for analysis"""
        
        self.client_analysis_prompt = """
You are an expert real estate lead analyzer. Analyze the following Telegram messages from a potential property client and provide a detailed assessment.

LANGUAGES SUPPORTED: English and Russian only

MESSAGES TO ANALYZE:
{messages}

USER CONTEXT:
- User ID: {user_id}
- Username: {username}
- Message Count: {message_count}
- Time Period: {time_period}

ANALYSIS REQUIRED:
1. **Hotness Score** (0-100): How likely is this person to buy/rent property soon?
   - 0-30: Cold (just browsing, no clear intent)
   - 31-60: Warm (interested but not urgent)
   - 61-85: Hot (actively searching, likely to transact)
   - 86-100: Burning (urgent, ready to buy/rent immediately)

2. **Intent Analysis**:
   - Primary intent: buying, renting, selling, or browsing
   - Confidence level (0-1)
   - Urgency: low, medium, high, urgent

3. **Property Preferences** (extract if mentioned):
   - Budget range (min/max in USD, convert if needed)
   - Preferred locations
   - Property types (condo, villa, house, land, townhouse, shophouse)
   - Bedrooms/bathrooms
   - Special requirements

4. **Behavioral Signals**:
   - Ready with financing/cash?
   - Wants property viewing?
   - Wants to be contacted?
   - Timeline for decision

5. **Language Detection**: en or ru

RESPONSE FORMAT (JSON only):
```json
{{
  "hotness_score": 75,
  "hotness_level": "hot",
  "primary_intent": "buying",
  "intent_confidence": 0.8,
  "urgency_level": "high",
  "budget_min": 150000,
  "budget_max": 300000,
  "currency": "USD",
  "preferred_locations": ["Phuket", "Rawai"],
  "asset_types": ["condo", "villa"],
  "bedrooms": 2,
  "bathrooms": 2,
  "financing_ready": true,
  "wants_viewing": true,
  "wants_contact": true,
  "timeline": "this_month",
  "language_detected": "en",
  "confidence": 0.85,
  "key_phrases": ["ready to buy", "cash available", "viewing this week"],
  "reasoning": "Client shows strong buying intent with specific budget, location preferences, and urgency indicators. Multiple requests for viewings and mentions cash readiness."
}}
```

IMPORTANT GUIDELINES:
- Focus on PROPERTY-RELATED content only
- Ignore non-property messages
- Be conservative with scores - only high scores for clear buying/renting intent
- Extract specific numbers, locations, and property types mentioned
- Consider message frequency and enthusiasm level
- Russian clients often use different communication style - adjust accordingly
- Look for urgency keywords in both languages
- Currency conversion: assume Russian clients use USD for international property

ENGLISH URGENCY INDICATORS: urgent, ASAP, ready now, cash ready, today, this week
RUSSIAN URGENCY INDICATORS: срочно, готов покупать, наличные готовы, сегодня, на этой неделе

Respond with ONLY the JSON object, no other text.
"""

        self.single_message_prompt = """
Analyze this single property-related message for client intent (English/Russian only):

MESSAGE: "{message}"
CONTEXT: From user {user_id} in channel {channel}

Rate the message for property buying/renting intent (0-100) and extract any property preferences mentioned.

Respond with JSON only:
```json
{{
  "intent_score": 65,
  "intent_type": "buying",
  "urgency": "medium",
  "extracted_preferences": {{
    "budget": 250000,
    "location": "Phuket",
    "property_type": "condo",
    "bedrooms": 2
  }},
  "signals": ["budget mentioned", "specific location", "viewing request"],
  "language": "en"
}}
```
"""
    
    async def analyze_client_messages(self, user_id: str, messages: List[Dict], 
                                    username: Optional[str] = None) -> LLMClientAnalysis:
        """Analyze multiple messages from a client using LLM"""
        
        if not messages:
            return LLMClientAnalysis(
                user_id=user_id,
                hotness_score=0,
                hotness_level="cold",
                primary_intent="browsing",
                intent_confidence=0.0,
                urgency_level="low"
            )
        
        # Format messages for analysis
        message_texts = []
        for i, msg in enumerate(messages[-20:], 1):  # Last 20 messages max
            timestamp = msg.get('timestamp', 'unknown')
            content = msg.get('content', msg.get('text', ''))
            channel = msg.get('channel', 'unknown')
            message_texts.append(f"[{i}] ({timestamp}) #{channel}: {content}")
        
        messages_str = "\n".join(message_texts)
        
        # Calculate time period
        if len(messages) > 1:
            first_msg = messages[0].get('timestamp', datetime.utcnow())
            last_msg = messages[-1].get('timestamp', datetime.utcnow())
            if isinstance(first_msg, str):
                first_msg = datetime.fromisoformat(first_msg.replace('Z', '+00:00'))
            if isinstance(last_msg, str):
                last_msg = datetime.fromisoformat(last_msg.replace('Z', '+00:00'))
            time_period = f"{(last_msg - first_msg).days} days"
        else:
            time_period = "single message"
        
        # Format prompt
        prompt = self.client_analysis_prompt.format(
            messages=messages_str,
            user_id=user_id,
            username=username or "unknown",
            message_count=len(messages),
            time_period=time_period
        )
        
        try:
            # Call LLM
            response = await self._call_llm(prompt)
            
            # Parse response
            analysis_data = json.loads(response)
            
            # Create analysis object
            analysis = LLMClientAnalysis(
                user_id=user_id,
                hotness_score=analysis_data.get('hotness_score', 0),
                hotness_level=analysis_data.get('hotness_level', 'cold'),
                primary_intent=analysis_data.get('primary_intent', 'browsing'),
                intent_confidence=analysis_data.get('intent_confidence', 0.0),
                urgency_level=analysis_data.get('urgency_level', 'low'),
                budget_min=analysis_data.get('budget_min'),
                budget_max=analysis_data.get('budget_max'),
                currency=analysis_data.get('currency', 'USD'),
                preferred_locations=analysis_data.get('preferred_locations', []),
                asset_types=analysis_data.get('asset_types', []),
                bedrooms=analysis_data.get('bedrooms'),
                bathrooms=analysis_data.get('bathrooms'),
                financing_ready=analysis_data.get('financing_ready', False),
                wants_viewing=analysis_data.get('wants_viewing', False),
                wants_contact=analysis_data.get('wants_contact', False),
                timeline=analysis_data.get('timeline'),
                language_detected=analysis_data.get('language_detected', 'en'),
                confidence=analysis_data.get('confidence', 0.0),
                key_phrases=analysis_data.get('key_phrases', []),
                reasoning=analysis_data.get('reasoning', '')
            )
            
            # Save analysis
            await self._save_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing client {user_id}: {e}")
            
            # Return default analysis on error
            return LLMClientAnalysis(
                user_id=user_id,
                hotness_score=0,
                hotness_level="cold",
                primary_intent="browsing",
                intent_confidence=0.0,
                urgency_level="low",
                reasoning=f"Analysis failed: {str(e)}"
            )
    
    async def analyze_single_message(self, message: str, user_id: str, 
                                   channel: str = "unknown") -> Dict:
        """Analyze a single message for quick intent detection"""
        
        prompt = self.single_message_prompt.format(
            message=message,
            user_id=user_id,
            channel=channel
        )
        
        try:
            response = await self._call_llm(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error analyzing single message: {e}")
            return {
                "intent_score": 0,
                "intent_type": "browsing",
                "urgency": "low",
                "extracted_preferences": {},
                "signals": [],
                "language": "en"
            }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API (OpenAI for now, extensible to other providers)"""
        
        if not self.openai_client:
            raise Exception("OpenAI library not installed. Run: pip install openai")
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert real estate lead analyzer. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            if content.startswith('```'):
                content = content[3:]   # Remove ```
            if content.endswith('```'):
                content = content[:-3]  # Remove trailing ```
            
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            raise
    
    async def _save_analysis(self, analysis: LLMClientAnalysis):
        """Save analysis results"""
        analysis_dir = self.storage_path / "analytics" / "llm_analyses"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual analysis
        analysis_file = analysis_dir / f"{analysis.user_id}_latest.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(analysis), f, indent=2, ensure_ascii=False, default=str)
        
        # Append to history log
        history_file = analysis_dir / f"{analysis.user_id}_history.ndjson"
        with open(history_file, 'a', encoding='utf-8') as f:
            analysis_with_timestamp = asdict(analysis)
            analysis_with_timestamp['analyzed_at'] = datetime.utcnow().isoformat()
            f.write(json.dumps(analysis_with_timestamp, ensure_ascii=False, default=str) + '\n')
    
    async def get_hot_clients(self, min_score: float = 61.0) -> List[LLMClientAnalysis]:
        """Get clients with high hotness scores"""
        analysis_dir = self.storage_path / "analytics" / "llm_analyses"
        
        if not analysis_dir.exists():
            return []
        
        hot_clients = []
        
        for analysis_file in analysis_dir.glob("*_latest.json"):
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    analysis = LLMClientAnalysis(**data)
                    
                    if analysis.hotness_score >= min_score:
                        hot_clients.append(analysis)
            except Exception as e:
                self.logger.error(f"Error loading analysis {analysis_file}: {e}")
        
        # Sort by hotness score descending
        hot_clients.sort(key=lambda x: x.hotness_score, reverse=True)
        
        return hot_clients
    
    async def generate_summary_report(self) -> Dict:
        """Generate summary report of all analyzed clients"""
        analysis_dir = self.storage_path / "analytics" / "llm_analyses"
        
        if not analysis_dir.exists():
            return {"error": "No analyses found"}
        
        all_analyses = []
        
        for analysis_file in analysis_dir.glob("*_latest.json"):
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_analyses.append(LLMClientAnalysis(**data))
            except Exception as e:
                self.logger.error(f"Error loading analysis {analysis_file}: {e}")
        
        if not all_analyses:
            return {"error": "No valid analyses found"}
        
        # Calculate statistics
        total_clients = len(all_analyses)
        
        # Hotness distribution
        hotness_distribution = {
            "burning": len([a for a in all_analyses if a.hotness_score >= 86]),
            "hot": len([a for a in all_analyses if 61 <= a.hotness_score < 86]),
            "warm": len([a for a in all_analyses if 31 <= a.hotness_score < 61]),
            "cold": len([a for a in all_analyses if a.hotness_score < 31])
        }
        
        # Intent distribution
        intent_distribution = {}
        for analysis in all_analyses:
            intent = analysis.primary_intent
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
        
        # Language distribution
        language_distribution = {}
        for analysis in all_analyses:
            lang = analysis.language_detected
            language_distribution[lang] = language_distribution.get(lang, 0) + 1
        
        # Average scores
        avg_hotness = sum(a.hotness_score for a in all_analyses) / total_clients
        avg_confidence = sum(a.confidence for a in all_analyses) / total_clients
        
        # Top locations
        all_locations = []
        for analysis in all_analyses:
            all_locations.extend(analysis.preferred_locations)
        
        location_counts = {}
        for loc in all_locations:
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_clients": total_clients,
            "hotness_distribution": hotness_distribution,
            "intent_distribution": intent_distribution,
            "language_distribution": language_distribution,
            "average_hotness_score": round(avg_hotness, 2),
            "average_confidence": round(avg_confidence, 2),
            "top_locations": top_locations,
            "high_value_clients": len([a for a in all_analyses if a.hotness_score >= 61]),
            "financing_ready_count": len([a for a in all_analyses if a.financing_ready]),
            "wants_viewing_count": len([a for a in all_analyses if a.wants_viewing]),
            "generated_at": datetime.utcnow().isoformat()
        }


class LLMClientMonitor:
    """Monitor for LLM-based client analysis with real-time updates"""
    
    def __init__(self, analyzer: LLMPropertyAnalyzer, webhook_url: Optional[str] = None):
        self.analyzer = analyzer
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)
        
        # Thresholds for alerts
        self.hot_threshold = 70.0
        self.burning_threshold = 85.0
    
    async def process_new_message(self, user_id: str, message: str, 
                                channel: str, username: Optional[str] = None):
        """Process a new message and update client analysis"""
        
        # Quick analysis of single message
        single_analysis = await self.analyzer.analyze_single_message(
            message, user_id, channel
        )
        
        # If message shows high intent, trigger full analysis
        if single_analysis.get('intent_score', 0) >= 50:
            
            # Load existing messages for this user
            user_messages = await self._load_user_messages(user_id)
            
            # Add new message
            user_messages.append({
                'content': message,
                'channel': channel,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Save updated messages
            await self._save_user_messages(user_id, user_messages)
            
            # Run full LLM analysis
            full_analysis = await self.analyzer.analyze_client_messages(
                user_id, user_messages, username
            )
            
            # Check for alerts
            await self._check_alerts(full_analysis)
            
            return full_analysis
        
        return None
    
    async def _load_user_messages(self, user_id: str) -> List[Dict]:
        """Load existing messages for a user"""
        messages_file = self.analyzer.storage_path / "analytics" / "user_messages" / f"{user_id}.json"
        
        if messages_file.exists():
            with open(messages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    
    async def _save_user_messages(self, user_id: str, messages: List[Dict]):
        """Save user messages"""
        messages_dir = self.analyzer.storage_path / "analytics" / "user_messages"
        messages_dir.mkdir(parents=True, exist_ok=True)
        
        messages_file = messages_dir / f"{user_id}.json"
        
        # Keep only last 50 messages to prevent unlimited growth
        messages = messages[-50:]
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False, default=str)
    
    async def _check_alerts(self, analysis: LLMClientAnalysis):
        """Check if analysis triggers any alerts"""
        
        if analysis.hotness_score >= self.burning_threshold:
            await self._send_alert(analysis, "burning")
        elif analysis.hotness_score >= self.hot_threshold:
            await self._send_alert(analysis, "hot")
    
    async def _send_alert(self, analysis: LLMClientAnalysis, alert_type: str):
        """Send alert for hot client"""
        
        alert = {
            "alert_type": alert_type,
            "user_id": analysis.user_id,
            "hotness_score": analysis.hotness_score,
            "intent": analysis.primary_intent,
            "urgency": analysis.urgency_level,
            "budget_range": f"${analysis.budget_min}-{analysis.budget_max}" if analysis.budget_min else "Unknown",
            "locations": analysis.preferred_locations,
            "key_signals": {
                "financing_ready": analysis.financing_ready,
                "wants_viewing": analysis.wants_viewing,
                "wants_contact": analysis.wants_contact,
                "timeline": analysis.timeline
            },
            "reasoning": analysis.reasoning,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log alert
        self.logger.info(f"🚨 {alert_type.upper()} CLIENT ALERT: {analysis.user_id} (Score: {analysis.hotness_score})")
        
        # Save alert
        alerts_file = self.analyzer.storage_path / "analytics" / "alerts.ndjson"
        alerts_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(alerts_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')
        
        # Send webhook if configured
        if self.webhook_url:
            await self._send_webhook_alert(alert)
    
    async def _send_webhook_alert(self, alert: Dict):
        """Send alert via webhook"""
        try:
            import aiohttp
            
            # Format for Slack/Discord
            color = "danger" if alert["alert_type"] == "burning" else "warning"
            emoji = "🔥" if alert["alert_type"] == "burning" else "⚡"
            
            payload = {
                "text": f"{emoji} Hot Property Client Alert",
                "attachments": [{
                    "color": color,
                    "fields": [
                        {"title": "Client", "value": alert["user_id"], "short": True},
                        {"title": "Score", "value": f"{alert['hotness_score']}/100", "short": True},
                        {"title": "Intent", "value": alert["intent"].title(), "short": True},
                        {"title": "Urgency", "value": alert["urgency"].title(), "short": True},
                        {"title": "Budget", "value": alert["budget_range"], "short": True},
                        {"title": "Locations", "value": ", ".join(alert["locations"][:3]) or "Not specified", "short": True},
                        {"title": "Key Signals", "value": f"💰 Financing: {'✅' if alert['key_signals']['financing_ready'] else '❌'}\n🏠 Viewing: {'✅' if alert['key_signals']['wants_viewing'] else '❌'}\n📞 Contact: {'✅' if alert['key_signals']['wants_contact'] else '❌'}", "short": False},
                        {"title": "AI Reasoning", "value": alert["reasoning"][:200] + "..." if len(alert["reasoning"]) > 200 else alert["reasoning"], "short": False}
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert webhook sent successfully for {alert['user_id']}")
                    else:
                        self.logger.error(f"Webhook failed with status {response.status}")
        
        except Exception as e:
            self.logger.error(f"Error sending webhook: {e}")


# Example usage and testing
async def test_llm_analyzer():
    """Test function for the LLM analyzer"""
    
    # Initialize analyzer (you'll need to set your OpenAI API key)
    analyzer = LLMPropertyAnalyzer(
        api_key="your-openai-api-key",  # Set this from environment
        storage_path="./storage"
    )
    
    # Test messages (English and Russian)
    test_messages = [
        {
            "content": "Hi, I'm looking for a 2-bedroom condo in Phuket, budget around $200k. Need to buy urgent!",
            "timestamp": "2024-01-15T10:30:00Z",
            "channel": "@phuket_property"
        },
        {
            "content": "Cash ready, can view this weekend. Please contact me ASAP",
            "timestamp": "2024-01-15T11:45:00Z", 
            "channel": "@phuket_property"
        },
        {
            "content": "Срочно ищу квартиру в Паттайе до $150k, готов покупать сегодня",
            "timestamp": "2024-01-15T12:15:00Z",
            "channel": "@pattaya_russian"
        }
    ]
    
    # Analyze client
    analysis = await analyzer.analyze_client_messages(
        user_id="test_user_123",
        messages=test_messages,
        username="@property_hunter"
    )
    
    print("Analysis Result:")
    print(f"Hotness Score: {analysis.hotness_score}/100")
    print(f"Level: {analysis.hotness_level}")
    print(f"Intent: {analysis.primary_intent} (confidence: {analysis.intent_confidence})")
    print(f"Budget: ${analysis.budget_min}-{analysis.budget_max}")
    print(f"Locations: {analysis.preferred_locations}")
    print(f"Ready signals: Financing={analysis.financing_ready}, Viewing={analysis.wants_viewing}")
    print(f"Language: {analysis.language_detected}")
    print(f"Reasoning: {analysis.reasoning}")


if __name__ == "__main__":
    asyncio.run(test_llm_analyzer())