"""
Base Stage for Chatbot Conversations

Provides common functionality and interface for all conversation stages.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import openai


class BaseChatbotStage(ABC):
    """Base class for all chatbot conversation stages"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Only initialize OpenAI client if not a mock key
        if openai_api_key and openai_api_key != "mock_key":
            try:
                self.client = openai.OpenAI(api_key=openai_api_key)
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
    
    @abstractmethod
    async def process(self, user_id: str, message: str, session: Dict, context: Dict = None) -> Dict:
        """
        Process user message and return stage result
        
        Args:
            user_id: User identifier
            message: User's message text
            session: Current session data
            context: Additional context
            
        Returns:
            Dict containing:
            - reply: Bot's response
            - next_stage: Next stage to transition to (optional)
            - data_collected: New data extracted from conversation
            - confidence: Confidence in the extraction (0-1)
            - session_complete: Whether conversation is complete
        """
        pass
    
    @abstractmethod
    def get_stage_name(self) -> str:
        """Return the name of this stage"""
        pass
    
    async def _call_openai(self, messages: list, model: str = None, temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
        """Call OpenAI API with error handling"""
        if self.client is None:
            self.logger.warning("OpenAI client not available (mock mode or initialization failed)")
            return None
            
        try:
            # Use model from env if not specified
            import os
            if model is None:
                model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return None
    
    def _extract_language(self, text: str) -> str:
        """Simple language detection for English/Russian"""
        # Count Cyrillic characters
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        total_chars = len([char for char in text if char.isalpha()])
        
        if total_chars == 0:
            return "en"  # Default to English
        
        cyrillic_ratio = cyrillic_chars / total_chars
        
        # If more than 30% Cyrillic, consider it Russian
        return "ru" if cyrillic_ratio > 0.3 else "en"
    
    def _get_response_template(self, language: str, template_key: str) -> str:
        """Get response template in specified language"""
        templates = {
            "en": {
                "error": "I apologize, but I couldn't process your request. Could you please try again?",
                "clarification": "Could you please provide more details about your property requirements?",
                "confirmation": "Thank you for the information. Let me help you find the perfect property.",
                "greeting": "Hello! I'm here to help you find your ideal property in Thailand.",
                "goodbye": "Thank you for using OneMinuta. Feel free to return anytime for property assistance!"
            },
            "ru": {
                "error": "Извините, но я не смог обработать ваш запрос. Не могли бы вы попробовать ещё раз?",
                "clarification": "Не могли бы вы предоставить больше деталей о ваших требованиях к недвижимости?",
                "confirmation": "Спасибо за информацию. Позвольте мне помочь вам найти идеальную недвижимость.",
                "greeting": "Привет! Я здесь, чтобы помочь вам найти идеальную недвижимость в Таиланде.",
                "goodbye": "Спасибо за использование OneMinuta. Возвращайтесь в любое время за помощью с недвижимостью!"
            }
        }
        
        return templates.get(language, templates["en"]).get(template_key, templates["en"][template_key])
    
    def _build_context_messages(self, session: Dict, system_prompt: str) -> list:
        """Build context messages for OpenAI API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for context (last 5 exchanges)
        history = session.get('conversation_history', [])[-5:]
        for exchange in history:
            if exchange.get('user_message'):
                messages.append({
                    "role": "user", 
                    "content": exchange['user_message']
                })
            if exchange.get('bot_reply'):
                messages.append({
                    "role": "assistant",
                    "content": exchange['bot_reply']
                })
        
        return messages