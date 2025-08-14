"""
Inquiry Collection Stage

Systematically collects user requirements for property search including:
- Property type preferences
- Location preferences  
- Budget range
- Specific features (bedrooms, bathrooms, etc.)
- Timeline and urgency
"""

import json
import re
from typing import Dict, Any, List, Optional

from .base_stage import BaseChatbotStage


class InquiryCollectionStage(BaseChatbotStage):
    """Collect detailed property requirements from user"""
    
    def get_stage_name(self) -> str:
        return "inquiry-collection"
    
    async def process(self, user_id: str, message: str, session: Dict, context: Dict = None) -> Dict:
        """Process message to collect property requirements"""
        
        # Get existing collected data
        collected_data = session.get('collected_data', {})
        profile = collected_data.get('profile', {})
        requirements = collected_data.get('requirements', {})
        language = profile.get('language_preference', 'en')
        
        # Extract new information from current message
        extracted_info = await self._extract_requirements(message, language, session)
        
        if not extracted_info:
            # Ask clarifying question if extraction failed
            clarifying_question = await self._generate_clarifying_question(requirements, language)
            return {
                'reply': clarifying_question,
                'data_collected': {},
                'confidence': 0.4,
                'user_message': message
            }
        
        # Merge new information with existing requirements
        updated_requirements = self._merge_requirements(requirements, extracted_info)
        
        # Determine what's still missing
        missing_fields = self._identify_missing_requirements(updated_requirements)
        
        # Generate response based on completeness
        if not missing_fields:
            # All required info collected - transition to property matching
            response = await self._generate_completion_response(updated_requirements, language)
            return {
                'reply': response,
                'next_stage': 'property-matching',
                'data_collected': {'requirements': updated_requirements},
                'confidence': 0.9,
                'user_message': message
            }
        else:
            # Ask for missing information
            follow_up_question = await self._generate_follow_up_question(missing_fields, updated_requirements, language)
            return {
                'reply': follow_up_question,
                'data_collected': {'requirements': updated_requirements},
                'confidence': 0.7,
                'user_message': message
            }
    
    async def _extract_requirements(self, message: str, language: str, session: Dict) -> Optional[Dict]:
        """Extract property requirements from message using LLM"""
        
        system_prompt = f"""You are an expert at extracting property requirements from user messages. 

Extract the following information from the user's message (if mentioned):
- property_type: condo, villa, house, townhouse, apartment
- location_preference: specific areas, cities, or general regions
- rent_or_sale: rent, sale, or both
- budget_min: minimum budget (extract number and currency)
- budget_max: maximum budget (extract number and currency) 
- bedrooms: number of bedrooms (extract number)
- bathrooms: number of bathrooms (extract number)
- furnished: true/false if mentioned
- timeline: when they need property (urgent, within_month, flexible, etc.)
- special_requirements: any specific features mentioned

The message language is: {language}

Respond with a JSON object. Only include fields that are clearly mentioned in the message.
If a field is not mentioned, don't include it in the response.

Examples:
"I need a 2-bedroom condo in Phuket for rent under 30,000 THB" → 
{{"property_type": "condo", "location_preference": "Phuket", "rent_or_sale": "rent", "budget_max": 30000, "bedrooms": 2}}

"Looking for furnished villa to buy" →
{{"property_type": "villa", "rent_or_sale": "sale", "furnished": true}}
"""
        
        messages = self._build_context_messages(session, system_prompt)
        messages.append({"role": "user", "content": message})
        
        response = await self._call_openai(messages, temperature=0.2, max_tokens=400)
        
        if not response:
            return None
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                # Validate and clean extracted data
                return self._validate_extracted_data(extracted)
            return None
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse requirements extraction: {response}")
            return None
    
    def _validate_extracted_data(self, extracted: Dict) -> Dict:
        """Validate and clean extracted requirements data"""
        
        valid_data = {}
        
        # Validate property type
        valid_property_types = ['condo', 'villa', 'house', 'townhouse', 'apartment']
        if 'property_type' in extracted and extracted['property_type'] in valid_property_types:
            valid_data['property_type'] = extracted['property_type']
        
        # Validate rent or sale
        valid_rent_sale = ['rent', 'sale', 'both']
        if 'rent_or_sale' in extracted and extracted['rent_or_sale'] in valid_rent_sale:
            valid_data['rent_or_sale'] = extracted['rent_or_sale']
        
        # Validate numeric fields
        numeric_fields = ['budget_min', 'budget_max', 'bedrooms', 'bathrooms']
        for field in numeric_fields:
            if field in extracted:
                try:
                    value = float(extracted[field])
                    if value > 0:
                        valid_data[field] = int(value) if field in ['bedrooms', 'bathrooms'] else value
                except (ValueError, TypeError):
                    pass
        
        # Validate boolean fields
        if 'furnished' in extracted and isinstance(extracted['furnished'], bool):
            valid_data['furnished'] = extracted['furnished']
        
        # Pass through text fields
        text_fields = ['location_preference', 'timeline', 'special_requirements']
        for field in text_fields:
            if field in extracted and isinstance(extracted[field], str) and extracted[field].strip():
                valid_data[field] = extracted[field].strip()
        
        return valid_data
    
    def _merge_requirements(self, existing: Dict, new: Dict) -> Dict:
        """Merge new requirements with existing ones"""
        merged = existing.copy()
        
        # Update with new information
        for key, value in new.items():
            if value is not None:
                merged[key] = value
        
        return merged
    
    def _identify_missing_requirements(self, requirements: Dict) -> List[str]:
        """Identify what required information is still missing"""
        
        required_fields = [
            'property_type',
            'rent_or_sale', 
            'location_preference'
        ]
        
        important_fields = [
            'budget_max',  # At least max budget
            'bedrooms'     # At least bedroom count
        ]
        
        missing = []
        
        # Check required fields
        for field in required_fields:
            if field not in requirements or not requirements[field]:
                missing.append(field)
        
        # Check important fields (if no budget range specified at all)
        if 'budget_min' not in requirements and 'budget_max' not in requirements:
            missing.append('budget_range')
        
        if 'bedrooms' not in requirements:
            missing.append('bedrooms')
        
        return missing
    
    async def _generate_clarifying_question(self, requirements: Dict, language: str) -> str:
        """Generate clarifying question when extraction fails"""
        
        questions = {
            "en": [
                "I'd like to help you find the perfect property. Could you tell me what type of property you're looking for - a condo, villa, or house?",
                "To better assist you, could you share more details about your property preferences?",
                "What kind of property are you interested in, and in which area?"
            ],
            "ru": [
                "Я хотел бы помочь вам найти идеальную недвижимость. Не могли бы вы сказать, какой тип недвижимости вы ищете - кондо, виллу или дом?",
                "Чтобы лучше вам помочь, не могли бы вы поделиться подробностями о ваших предпочтениях?",
                "Какая недвижимость вас интересует и в каком районе?"
            ]
        }
        
        question_list = questions.get(language, questions["en"])
        return question_list[0]  # Use first question for simplicity
    
    async def _generate_follow_up_question(self, missing_fields: List[str], current_requirements: Dict, language: str) -> str:
        """Generate follow-up question for missing information"""
        
        # Prioritize questions based on what's missing
        question_priority = {
            'property_type': 1,
            'location_preference': 2,
            'rent_or_sale': 3,
            'budget_range': 4,
            'bedrooms': 5
        }
        
        # Find highest priority missing field
        priority_field = min(missing_fields, key=lambda x: question_priority.get(x, 999))
        
        system_prompt = f"""Generate a natural follow-up question to collect missing property requirement information.

Current requirements collected: {json.dumps(current_requirements, indent=2)}
Missing information needed: {priority_field}
Language: {language} ({'English' if language == 'en' else 'Russian'})

Generate a conversational question that:
1. Acknowledges what they've already shared
2. Asks specifically for the missing information
3. Provides helpful examples or options
4. Keep it friendly and natural (1-2 sentences)

Missing field to ask about: {priority_field}
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        if response:
            return response
        
        # Fallback questions
        fallback_questions = {
            "en": {
                "property_type": "What type of property interests you - a condo, villa, house, or townhouse?",
                "location_preference": "Which area would you prefer? For example, Phuket, Bangkok, or Pattaya?",
                "rent_or_sale": "Are you looking to rent or buy a property?",
                "budget_range": "What's your budget range? This helps me show you suitable options.",
                "bedrooms": "How many bedrooms do you need?"
            },
            "ru": {
                "property_type": "Какой тип недвижимости вас интересует - кондо, вилла, дом или таунхаус?",
                "location_preference": "Какой район вы предпочитаете? Например, Пхукет, Бангкок или Паттайя?",
                "rent_or_sale": "Вы хотите арендовать или купить недвижимость?",
                "budget_range": "Каков ваш бюджетный диапазон? Это поможет мне показать подходящие варианты.",
                "bedrooms": "Сколько спален вам нужно?"
            }
        }
        
        return fallback_questions.get(language, fallback_questions["en"]).get(priority_field, 
            fallback_questions["en"]["property_type"])
    
    async def _generate_completion_response(self, requirements: Dict, language: str) -> str:
        """Generate response when all requirements are collected"""
        
        system_prompt = f"""Generate an enthusiastic response indicating you have collected all the necessary information and are ready to search for properties.

Requirements collected: {json.dumps(requirements, indent=2)}
Language: {language} ({'English' if language == 'en' else 'Russian'})

Generate a response that:
1. Summarizes what they're looking for
2. Shows enthusiasm about helping them
3. Indicates you're now searching for properties
4. Keep it concise (2-3 sentences)
5. End with anticipation of showing results
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.8,
            max_tokens=200
        )
        
        if response:
            return response
        
        # Fallback completion responses
        fallbacks = {
            "en": "Perfect! I now have all the information I need. Let me search for properties that match your requirements - I think you'll be excited by what I find!",
            "ru": "Отлично! Теперь у меня есть вся необходимая информация. Позвольте мне найти недвижимость, соответствующую вашим требованиям - думаю, вы будете в восторге от того, что я найду!"
        }
        
        return fallbacks.get(language, fallbacks["en"])