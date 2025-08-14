"""
Partner Support Stage for OneMinuta Chatbot
Handles partner questions and provides information about the partnership program
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import re

from .base_stage import BaseStage, StageResult


class PartnerSupportStage(BaseStage):
    """Handles partner inquiries and provides partnership information"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stage_name = "partner-support"
        self.logger = logging.getLogger(__name__)
        
        # Load FAQ responses
        self.faq_data = self._load_faq_data()
        
        # Keywords that trigger partner support
        self.partner_keywords = [
            "partner", "partnership", "earn", "commission", "revenue",
            "channel owner", "admin", "monetize", "affiliate",
            "join program", "become partner", "add bot",
            "how much earn", "payment", "payout"
        ]
        
        # Keywords for specific topics
        self.topic_keywords = {
            "earnings": ["earn", "commission", "money", "revenue", "income", "payment", "payout"],
            "setup": ["setup", "add bot", "install", "integrate", "start", "begin"],
            "requirements": ["requirement", "eligible", "qualify", "need", "criteria"],
            "features": ["feature", "what does", "capability", "function", "bot do"],
            "support": ["help", "support", "contact", "assistance", "problem"]
        }
    
    def _load_faq_data(self) -> Dict:
        """Load partner FAQ responses"""
        faq_file = Path(__file__).parent.parent.parent / "docs" / "PARTNER_FAQ_RESPONSES.json"
        
        if faq_file.exists():
            try:
                with open(faq_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load FAQ data: {e}")
        
        # Return basic structure if file not found
        return {
            "partner_faqs": {},
            "quick_responses": {
                "greeting": "Welcome! I can help you learn about OneMinuta Partnership Program.",
                "more_info": "Message @oneminuta_partners for more information.",
                "apply_now": "Ready to start? Message @oneminuta_partners!",
                "not_understood": "Please ask about earnings, setup, or requirements."
            }
        }
    
    def should_process(self, message: str, context: Dict[str, Any]) -> bool:
        """Check if message is asking about partnership"""
        message_lower = message.lower()
        
        # Check for partner keywords
        for keyword in self.partner_keywords:
            if keyword in message_lower:
                return True
        
        # Check if context indicates partner inquiry
        if context.get("intent") == "partner_inquiry":
            return True
        
        # Check for question patterns about channels
        partner_patterns = [
            r"how.*add.*bot.*channel",
            r"can.*bot.*my.*channel",
            r"want.*partner",
            r"interested.*program",
            r"tell.*about.*partner"
        ]
        
        for pattern in partner_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    async def process(self, message: str, session_id: str, **kwargs) -> StageResult:
        """Process partner inquiry and provide relevant information"""
        
        # Get or create session
        session = self.get_session(session_id)
        
        # Detect the topic of inquiry
        topic = self._detect_topic(message)
        
        # Find best matching FAQ
        best_faq = self._find_best_faq(message)
        
        # Generate response
        if best_faq:
            response = best_faq["answer"]
            
            # Add relevant follow-up based on topic
            if topic == "earnings":
                response += "\n\n💰 Average partners earn $2,000-5,000 monthly. Ready to start earning?"
            elif topic == "setup":
                response += "\n\n🚀 Setup takes just 5 minutes! Message @oneminuta_partners to begin."
            elif topic == "requirements":
                response += "\n\n✅ It's free to join with no obligations. Want to learn more?"
        else:
            # Use quick responses for general inquiries
            response = self._get_general_response(message, topic)
        
        # Update session
        session["interactions"].append({
            "message": message,
            "topic": topic,
            "response": response
        })
        
        # Check if user seems interested
        interest_level = self._assess_interest_level(session)
        
        # Add call-to-action if interested
        if interest_level == "high":
            response += "\n\n📲 You seem interested! Message @oneminuta_partners now to get started. Setup takes only 5 minutes!"
        elif interest_level == "medium":
            response += "\n\n📚 Want to learn more? Ask me about earnings, requirements, or how the bot works."
        
        self.save_session(session_id, session)
        
        return StageResult(
            success=True,
            data={
                "response": response,
                "topic": topic,
                "interest_level": interest_level,
                "stage": self.stage_name
            },
            confidence=0.9,
            next_stage="conversation" if interest_level != "high" else None
        )
    
    def _detect_topic(self, message: str) -> Optional[str]:
        """Detect the main topic of the inquiry"""
        message_lower = message.lower()
        
        topic_scores = {}
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        
        return None
    
    def _find_best_faq(self, message: str) -> Optional[Dict]:
        """Find the best matching FAQ for the message"""
        message_lower = message.lower()
        best_match = None
        best_score = 0
        
        for category in self.faq_data.get("partner_faqs", {}).values():
            for faq in category.values():
                if not isinstance(faq, dict):
                    continue
                    
                # Calculate match score based on keywords
                score = 0
                for keyword in faq.get("keywords", []):
                    if keyword in message_lower:
                        score += 1
                
                # Check if question is similar
                if "question" in faq:
                    question_words = set(faq["question"].lower().split())
                    message_words = set(message_lower.split())
                    overlap = len(question_words & message_words)
                    score += overlap * 0.5
                
                if score > best_score:
                    best_score = score
                    best_match = faq
        
        # Return match if score is good enough
        if best_score >= 1.0:
            return best_match
        
        return None
    
    def _get_general_response(self, message: str, topic: Optional[str]) -> str:
        """Get a general response based on topic"""
        quick_responses = self.faq_data.get("quick_responses", {})
        
        if topic == "earnings":
            return """💰 **OneMinuta Partnership Earnings**

You can earn:
• 0.5% commission on property sales (minimum $500)
• 25% of first month's rent on rentals (minimum $100)
• $10-50 per qualified lead

Average channels earn $2,000-5,000 per month!"""

        elif topic == "setup":
            return """🚀 **Quick 5-Minute Setup**

1. Message @oneminuta_partners with your channel
2. Add @oneminuta_bot as admin
3. Grant necessary permissions
4. Start earning immediately!

No fees, no technical knowledge required."""

        elif topic == "requirements":
            return """✅ **Partnership Requirements**

All you need:
• Active Telegram channel (property-related)
• Admin access to add our bot
• 100+ members (recommended)

That's it! No fees, no contracts, cancel anytime."""

        elif topic == "features":
            return """🤖 **What Our Bot Does**

• Auto-welcomes new channel members
• Analyzes property needs with AI
• Provides instant property search (EN/RU)
• Scores leads: Cold → Warm → Hot → 🔥 Burning
• Sends personalized property matches

Your members get premium service, you earn commissions!"""

        elif topic == "support":
            return """📞 **Partner Support**

We're here to help:
• Telegram: @oneminuta_partners
• Email: partners@oneminuta.com
• Support Hours: 9 AM - 6 PM ICT (Mon-Fri)
• Emergency: @oneminuta_urgent

Full training and setup assistance provided!"""
        
        # Default greeting
        return quick_responses.get("greeting", 
            "Welcome! I can help you learn about OneMinuta Partnership. Ask me about earnings, setup, or requirements!")
    
    def _assess_interest_level(self, session: Dict) -> str:
        """Assess user's interest level based on conversation"""
        interactions = session.get("interactions", [])
        
        if not interactions:
            return "low"
        
        # High interest indicators
        high_interest_keywords = [
            "how to join", "sign up", "ready to start", "add bot now",
            "want to partner", "interested", "apply", "begin earning"
        ]
        
        # Medium interest indicators
        medium_interest_keywords = [
            "how much", "tell me more", "explain", "what about",
            "requirements", "commission", "earnings"
        ]
        
        # Check recent messages
        recent_messages = " ".join([i["message"].lower() for i in interactions[-3:]])
        
        high_count = sum(1 for keyword in high_interest_keywords if keyword in recent_messages)
        medium_count = sum(1 for keyword in medium_interest_keywords if keyword in recent_messages)
        
        if high_count >= 1:
            return "high"
        elif medium_count >= 2 or len(interactions) >= 3:
            return "medium"
        else:
            return "low"
    
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new partner inquiry session"""
        return {
            "session_id": session_id,
            "stage": self.stage_name,
            "interactions": [],
            "topics_discussed": [],
            "interest_level": "low",
            "created_at": None,
            "last_updated": None
        }
    
    async def generate_pitch(self, channel_size: int = 1000) -> str:
        """Generate a customized partnership pitch based on channel size"""
        
        # Estimate earnings based on channel size
        if channel_size < 1000:
            estimated_earnings = "$300-800"
            tier = "Starter"
        elif channel_size < 5000:
            estimated_earnings = "$500-2,000"
            tier = "Growth"
        elif channel_size < 20000:
            estimated_earnings = "$2,000-7,000"
            tier = "Professional"
        else:
            estimated_earnings = "$7,000-20,000+"
            tier = "Premium"
        
        pitch = f"""🚀 **OneMinuta Partnership - {tier} Tier**

Based on your channel size (~{channel_size:,} members), you could earn:
💰 **{estimated_earnings} per month**

✨ **What You Get:**
• Free AI bot that auto-serves your members
• Instant property search in English/Russian
• Hot lead detection & scoring
• Detailed analytics dashboard
• No setup costs or fees

📊 **Your Potential:**
• Property Sales: 0.5% commission
• Rentals: 25% of first month
• Leads: $10-50 per qualified lead

🎯 **Success Story:**
A similar {tier} channel earned ${int(channel_size * 0.7)} in their first month!

⚡ **Quick Start:**
Setup takes 5 minutes. You could be earning commissions by tomorrow!

Ready to monetize your channel? Message @oneminuta_partners now!"""
        
        return pitch


# Example integration with main chatbot
async def handle_partner_inquiry(message: str, session_id: str) -> str:
    """Handle partner inquiries through the chatbot"""
    
    partner_stage = PartnerSupportStage()
    
    # Check if this is a partner inquiry
    if partner_stage.should_process(message, {}):
        result = await partner_stage.process(message, session_id)
        if result.success:
            return result.data["response"]
    
    return None