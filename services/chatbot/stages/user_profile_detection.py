"""
User Profile Detection Stage

Determines user type (buyer, seller, agent, investor) and language preference
from initial conversation patterns.
"""

import json
import re
from typing import Dict, Any, Optional

from .base_stage import BaseChatbotStage


class UserProfileDetectionStage(BaseChatbotStage):
    """Detect user profile and preferences from initial interactions"""
    
    def get_stage_name(self) -> str:
        return "user-profile-detection"
    
    async def process(self, user_id: str, message: str, session: Dict, context: Dict = None) -> Dict:
        """Process message to detect user profile"""
        
        # Detect language from message
        detected_language = self._extract_language(message)
        
        # Extract user type and intent using LLM
        user_profile = await self._analyze_user_profile(message, detected_language, session)
        
        if not user_profile:
            # Fallback response if analysis fails
            return {
                'reply': self._get_response_template(detected_language, "error"),
                'data_collected': {'language_preference': detected_language},
                'confidence': 0.3,
                'user_message': message
            }
        
        # Prepare collected data
        collected_data = {
            'profile': {
                'user_type': user_profile.get('user_type', 'buyer'),
                'language_preference': detected_language,
                'intent': user_profile.get('intent', 'search'),
                'confidence': user_profile.get('confidence', 0.7)
            }
        }
        
        # Generate response based on profile
        reply = await self._generate_profile_response(user_profile, detected_language, message)
        
        # Determine if we have enough profile data to proceed
        confidence = user_profile.get('confidence', 0.7)
        next_stage = 'smart-greeting' if confidence > 0.6 else None
        
        return {
            'reply': reply,
            'next_stage': next_stage,
            'data_collected': collected_data,
            'confidence': confidence,
            'user_message': message
        }
    
    async def _analyze_user_profile(self, message: str, language: str, session: Dict) -> Optional[Dict]:
        """Analyze message to determine user profile using LLM"""
        
        system_prompt = f"""You are an AI assistant that analyzes user messages to determine their profile for a property platform. 

Analyze the user's message and determine:
1. User type: buyer, seller, agent, investor
   - buyer: Looking to purchase or rent property for personal use
   - seller: Wants to sell or list their property
   - agent: Real estate professional needing platform access
   - investor: Looking for investment opportunities, rental income, ROI
2. Primary intent: search, sell, invest, browse
   - search: Actively looking for specific properties
   - sell: Wants to list/sell property
   - invest: Seeking investment opportunities
   - browse: General exploration of available properties
3. Urgency level: low, medium, high
4. Budget indication: budget_mentioned, no_budget_mentioned
5. Location mentioned: location_mentioned, no_location_mentioned

The message language is: {language}

IMPORTANT DISTINCTIONS:
- If someone mentions "investment", "инвестиции", "ROI", "rental income" → investor
- If someone says "I'm an agent", "real estate agent" → agent
- For non-meaningful input (numbers, gibberish), use fallback values

Respond with a JSON object containing:
{{
  "user_type": "buyer|seller|agent|investor",
  "intent": "search|sell|invest|browse", 
  "urgency": "low|medium|high",
  "budget_indication": "budget_mentioned|no_budget_mentioned",
  "location_mentioned": "location_mentioned|no_location_mentioned",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Examples:
- "I'm looking for a condo in Phuket under 50k THB" → buyer, search, medium, budget_mentioned, location_mentioned
- "Привет, хочу продать квартиру" → seller, sell, low, no_budget_mentioned, no_location_mentioned  
- "What properties do you have?" → buyer, browse, low, no_budget_mentioned, no_location_mentioned
- "Looking for investment opportunities" → investor, invest, medium, no_budget_mentioned, no_location_mentioned
- "I'm a real estate agent" → agent, browse, low, no_budget_mentioned, no_location_mentioned
- "123456" → buyer, browse, low, no_budget_mentioned, no_location_mentioned (fallback)
"""
        
        messages = self._build_context_messages(session, system_prompt)
        messages.append({"role": "user", "content": message})
        
        response = await self._call_openai(messages, temperature=0.3, max_tokens=300)
        
        if not response:
            return None
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse profile analysis response: {response}")
            return None
    
    async def _generate_profile_response(self, profile: Dict, language: str, original_message: str) -> str:
        """Generate appropriate response based on detected profile"""
        
        user_type = profile.get('user_type', 'buyer')
        intent = profile.get('intent', 'search')
        
        # Build response prompt
        system_prompt = f"""You are OneMinuta's friendly property assistant. Generate a welcoming response that:

1. Acknowledges the user's intent ({intent}) 
2. Shows you understand they are a {user_type}
3. Provides next steps
4. Keep it conversational and helpful
5. Language: {language} ({'English' if language == 'en' else 'Russian'})
6. Maximum 2-3 sentences
7. End with a question to continue the conversation

User type: {user_type}
Intent: {intent}
Original message: "{original_message}"

For buyers: Focus on helping them find properties
For sellers: Focus on helping them list properties  
For investors: Focus on investment opportunities
For agents: Focus on platform features
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.8,
            max_tokens=200
        )
        
        if response:
            return response
        
        # Fallback responses by user type and language
        fallbacks = {
            "en": {
                "buyer": "Welcome! I'd love to help you find the perfect property. What type of property are you looking for?",
                "seller": "Hello! I can help you list your property on OneMinuta. What property would you like to sell?", 
                "investor": "Great to meet an investor! I can show you investment opportunities. What's your investment focus?",
                "agent": "Welcome to OneMinuta! As an agent, you can access our full platform features. What would you like to do first?"
            },
            "ru": {
                "buyer": "Добро пожаловать! Я помогу вам найти идеальную недвижимость. Какой тип недвижимости вас интересует?",
                "seller": "Привет! Я могу помочь разместить вашу недвижимость на OneMinuta. Какую недвижимость хотите продать?",
                "investor": "Приятно встретить инвестора! Я покажу вам инвестиционные возможности. На чём фокусируетесь?", 
                "agent": "Добро пожаловать в OneMinuta! Как агент, у вас есть доступ ко всем функциям платформы. С чего начнём?"
            }
        }
        
        return fallbacks.get(language, fallbacks["en"]).get(user_type, fallbacks["en"]["buyer"])
    
    def _extract_keywords(self, text: str) -> Dict:
        """Extract relevant keywords from user message"""
        text_lower = text.lower()
        
        # Property type keywords
        property_types = {
            'condo': ['condo', 'condominium', 'apartment', 'кондо', 'квартира'],
            'house': ['house', 'home', 'дом', 'домик'],
            'villa': ['villa', 'вилла'],
            'townhouse': ['townhouse', 'townhome', 'таунхаус']
        }
        
        # Location keywords
        locations = {
            'phuket': ['phuket', 'пхукет'],
            'bangkok': ['bangkok', 'бангкок'],
            'pattaya': ['pattaya', 'паттайя'],
            'rawai': ['rawai', 'равай'],
            'kata': ['kata', 'ката'],
            'patong': ['patong', 'патонг']
        }
        
        # Intent keywords
        intent_keywords = {
            'buy': ['buy', 'purchase', 'купить', 'приобрести'],
            'rent': ['rent', 'rental', 'lease', 'арендовать', 'снять'],
            'sell': ['sell', 'selling', 'продать', 'продажа'],
            'invest': ['invest', 'investment', 'инвестиции', 'инвестировать']
        }
        
        extracted = {
            'property_types': [],
            'locations': [],
            'intents': []
        }
        
        # Check for property types
        for prop_type, keywords in property_types.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['property_types'].append(prop_type)
        
        # Check for locations
        for location, keywords in locations.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['locations'].append(location)
        
        # Check for intents
        for intent, keywords in intent_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['intents'].append(intent)
        
        return extracted