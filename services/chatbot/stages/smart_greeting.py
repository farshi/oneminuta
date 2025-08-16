"""
Smart Greeting Stage

Provides personalized greeting based on user profile and initiates 
the inquiry collection process.
"""

import json
from typing import Dict, Any

from .base_stage import BaseChatbotStage
from libs.permissions import check_permission


class SmartGreetingStage(BaseChatbotStage):
    """Generate personalized greeting and transition to inquiry collection"""
    
    def get_stage_name(self) -> str:
        return "smart-greeting"
    
    async def process(self, user_id: str, message: str, session: Dict, context: Dict = None) -> Dict:
        """Process message and provide personalized greeting"""
        
        # Get user profile and roles from session
        profile = session.get('collected_data', {}).get('profile', {})
        language = profile.get('language_preference', 'en')
        user_type = profile.get('user_type', 'buyer')
        user_roles = session.get('roles', ['user'])
        
        # Check if user is admin or partner
        is_admin = 'admin' in user_roles
        is_partner = 'partner' in user_roles
        
        # Generate personalized greeting based on role
        if is_admin:
            greeting = self._get_admin_greeting(language)
        elif is_partner:
            greeting = self._get_partner_greeting(language)
        else:
            greeting = await self._generate_personalized_greeting(profile, message, session)
        
        if not greeting:
            # Fallback greeting
            greeting = self._get_fallback_greeting(user_type, language)
        
        # Add conversation starter based on user type and role
        if is_admin:
            conversation_starter = self._get_admin_menu(language)
        elif is_partner:
            conversation_starter = self._get_partner_menu(language)
        else:
            conversation_starter = self._get_conversation_starter(user_type, language)
        
        full_response = f"{greeting}\n\n{conversation_starter}"
        
        return {
            'reply': full_response,
            'next_stage': 'inquiry-collection',
            'data_collected': {
                'greeting': {
                    'personalized': True,
                    'greeting_type': user_type,
                    'language': language
                }
            },
            'confidence': 0.9,
            'user_message': message
        }
    
    async def _generate_personalized_greeting(self, profile: Dict, message: str, session: Dict) -> str:
        """Generate personalized greeting using LLM"""
        
        user_type = profile.get('user_type', 'buyer')
        language = profile.get('language_preference', 'en')
        intent = profile.get('intent', 'search')
        
        system_prompt = f"""You are OneMinuta's friendly property assistant. Generate a personalized greeting that:

1. Acknowledges their profile as a {user_type}
2. References their intent: {intent}
3. Shows enthusiasm and professionalism
4. Language: {language} ({'English' if language == 'en' else 'Russian'})
5. Keep it warm but concise (1-2 sentences)
6. Don't ask questions yet - this is just the greeting

User profile:
- Type: {user_type}
- Intent: {intent}
- Language: {language}

Make it feel personal and welcoming, like talking to a knowledgeable local expert.
"""
        
        response = await self._call_openai(
            [{"role": "system", "content": system_prompt}],
            temperature=0.8,
            max_tokens=150
        )
        
        return response
    
    def _get_fallback_greeting(self, user_type: str, language: str) -> str:
        """Get fallback greeting if LLM fails"""
        
        greetings = {
            "en": {
                "buyer": "Welcome to OneMinuta! I'm excited to help you find your perfect property in Thailand.",
                "seller": "Hello! I'm here to help you successfully list and sell your property.",
                "investor": "Great to meet you! I'll help you discover excellent investment opportunities.",
                "agent": "Welcome to OneMinuta! Let's help you serve your clients better."
            },
            "ru": {
                "buyer": "Добро пожаловать в OneMinuta! Я рад помочь вам найти идеальную недвижимость в Таиланде.",
                "seller": "Привет! Я здесь, чтобы помочь вам успешно разместить и продать недвижимость.",
                "investor": "Приятно познакомиться! Я помогу вам найти отличные инвестиционные возможности.", 
                "agent": "Добро пожаловать в OneMinuta! Давайте поможем вашим клиентам еще лучше."
            }
        }
        
        return greetings.get(language, greetings["en"]).get(user_type, greetings["en"]["buyer"])
    
    def _get_admin_greeting(self, language: str) -> str:
        """Get admin-specific greeting"""
        greetings = {
            "en": "Welcome Admin! You have full system access.",
            "ru": "Добро пожаловать, Администратор! У вас есть полный доступ к системе."
        }
        return greetings.get(language, greetings["en"])
    
    def _get_partner_greeting(self, language: str) -> str:
        """Get partner-specific greeting"""
        greetings = {
            "en": "Welcome back, Partner! Ready to manage your property listings?",
            "ru": "С возвращением, Партнер! Готовы управлять своими объявлениями?"
        }
        return greetings.get(language, greetings["en"])
    
    def _get_admin_menu(self, language: str) -> str:
        """Get admin menu options"""
        menus = {
            "en": "Admin Commands:\n/add_role @username role\n/remove_role @username role\n/list_partners\n/list_admins\n/view_analytics",
            "ru": "Команды администратора:\n/add_role @username role\n/remove_role @username role\n/list_partners\n/list_admins\n/view_analytics"
        }
        return menus.get(language, menus["en"])
    
    def _get_partner_menu(self, language: str) -> str:
        """Get partner menu options"""
        menus = {
            "en": "Partner Options:\n1) Set up Telegram channel\n2) Post new listings\n3) View your analytics\n4) Manage existing listings",
            "ru": "Опции партнера:\n1) Настроить Telegram канал\n2) Разместить новые объявления\n3) Посмотреть аналитику\n4) Управлять объявлениями"
        }
        return menus.get(language, menus["en"])
    
    def _get_conversation_starter(self, user_type: str, language: str) -> str:
        """Get conversation starter based on user type"""
        
        starters = {
            "en": {
                "buyer": "Are you looking to BUY or RENT? Once I know that, I can help you find the perfect property.",
                "renter": "Great! You're looking to rent. What type of property interests you - condo, villa, or house? And what's your monthly budget?",
                "seller": "To help you list your property effectively, let me gather some details. What type of property are you looking to sell?",
                "investor": "To identify the best investment opportunities for you, I need to understand your investment criteria. What's your preferred property type and budget range?",
                "agent": "I can help you access properties for your clients or list new ones. What would you like to do today?",
                "partner": "Welcome partner! Would you like to: 1) Set up your Telegram channel, 2) Post new listings, or 3) View analytics?"
            },
            "ru": {
                "buyer": "Вы хотите КУПИТЬ или АРЕНДОВАТЬ? Как только я узнаю, я помогу найти идеальную недвижимость.",
                "renter": "Отлично! Вы ищете аренду. Какой тип недвижимости вас интересует - кондо, вилла или дом? И какой ваш месячный бюджет?",
                "seller": "Чтобы помочь эффективно разместить вашу недвижимость, позвольте собрать некоторые детали. Какой тип недвижимости вы хотите продать?",
                "investor": "Чтобы определить лучшие инвестиционные возможности для вас, мне нужно понять ваши критерии. Какой тип недвижимости и бюджетный диапазон предпочитаете?",
                "agent": "Я могу помочь вам получить доступ к недвижимости для ваших клиентов или разместить новые объекты. Что бы вы хотели сделать сегодня?",
                "partner": "Добро пожаловать, партнер! Что хотите сделать: 1) Настроить Telegram канал, 2) Разместить объявления, или 3) Посмотреть аналитику?"
            }
        }
        
        return starters.get(language, starters["en"]).get(user_type, starters["en"]["buyer"])
    
    def _analyze_greeting_effectiveness(self, profile: Dict, message: str) -> Dict:
        """Analyze how to make greeting most effective"""
        
        user_type = profile.get('user_type', 'buyer')
        urgency = profile.get('urgency', 'medium')
        
        effectiveness_factors = {
            'personalization_level': 'high' if user_type in ['buyer', 'investor'] else 'medium',
            'urgency_response': urgency,
            'focus_area': self._determine_focus_area(profile),
            'tone': self._determine_tone(profile, message)
        }
        
        return effectiveness_factors
    
    def _determine_focus_area(self, profile: Dict) -> str:
        """Determine what to focus on in greeting"""
        
        user_type = profile.get('user_type', 'buyer')
        intent = profile.get('intent', 'search')
        
        focus_map = {
            ('buyer', 'search'): 'property_discovery',
            ('buyer', 'browse'): 'exploration_support',
            ('seller', 'sell'): 'listing_assistance',
            ('investor', 'invest'): 'investment_analysis',
            ('agent', 'browse'): 'client_tools'
        }
        
        return focus_map.get((user_type, intent), 'general_assistance')
    
    def _determine_tone(self, profile: Dict, message: str) -> str:
        """Determine appropriate tone for greeting"""
        
        # Analyze message formality
        formal_indicators = ['please', 'could you', 'would you', 'пожалуйста', 'не могли бы']
        casual_indicators = ['hi', 'hey', 'привет', 'салам']
        
        message_lower = message.lower()
        
        if any(indicator in message_lower for indicator in formal_indicators):
            return 'formal'
        elif any(indicator in message_lower for indicator in casual_indicators):
            return 'casual'
        else:
            return 'professional'  # Default balanced tone