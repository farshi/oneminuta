"""
Configuration for Analytics service
Centralized config loader following project guidelines
"""

import os
from typing import Optional, List
from pathlib import Path
from libs.config_loader import get_config, get_openai_api_key, get_telegram_api_id, get_telegram_api_hash


class AnalyticsConfig:
    """Configuration for analytics services - single source of truth"""
    
    def __init__(self):
        """Load all config from environment variables"""
        self._load_config()
    
    def _load_config(self):
        """Load configuration using centralized config loader"""
        # OpenAI/LLM Configuration
        self.OPENAI_API_KEY: str = get_openai_api_key(required=True)
        self.LLM_MODEL: str = get_config('LLM_MODEL', default='gpt-4o-mini')
        self.LLM_TEMPERATURE: float = float(get_config('LLM_TEMPERATURE', default='0.1'))
        self.LLM_MAX_TOKENS: int = int(get_config('LLM_MAX_TOKENS', default='1000'))
        
        # Telegram Configuration
        telegram_api_id = get_telegram_api_id(required=False)
        telegram_api_hash = get_telegram_api_hash(required=False)
        if not telegram_api_id or not telegram_api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required for analytics service")
        self.TELEGRAM_API_ID: int = int(telegram_api_id)
        self.TELEGRAM_API_HASH: str = telegram_api_hash
        
        # Storage Configuration
        self.STORAGE_PATH: str = get_config('STORAGE_PATH', default='./storage')
        self.SESSION_PATH: str = get_config('SESSION_PATH', default='./sessions')
        
        # Alert Configuration
        self.WEBHOOK_URL: Optional[str] = get_config('WEBHOOK_URL')
        self.HOT_CLIENT_THRESHOLD: float = float(get_config('HOT_CLIENT_THRESHOLD', default='70.0'))
        self.BURNING_CLIENT_THRESHOLD: float = float(get_config('BURNING_CLIENT_THRESHOLD', default='85.0'))
        
        # Monitoring Configuration - from centralized config
        channels_env = get_config('TELEGRAM_CHANNELS', default='')
        if channels_env:
            self.DEFAULT_CHANNELS: List[str] = [ch.strip() for ch in channels_env.split(',')]
        else:
            # Fallback defaults
            self.DEFAULT_CHANNELS: List[str] = [
                '@phuketgidsell',
                '@phuketgid', 
                '@sabay_property'
            ]
        
        # Language Configuration
        languages_env = get_config('SUPPORTED_LANGUAGES', default='en,ru')
        self.SUPPORTED_LANGUAGES: List[str] = [lang.strip() for lang in languages_env.split(',')]
        self.DEFAULT_LANGUAGE: str = get_config('DEFAULT_LANGUAGE', default='en')
        
        # Analysis Configuration
        self.MAX_MESSAGES_PER_ANALYSIS: int = int(get_config('MAX_MESSAGES_PER_ANALYSIS', default='20'))
        self.MAX_STORED_MESSAGES: int = int(get_config('MAX_STORED_MESSAGES', default='50'))
        self.ANALYSIS_CACHE_TTL: int = int(get_config('ANALYSIS_CACHE_TTL', default='3600'))
    
    def _require_env(self, var_name: str) -> str:
        """Require an environment variable to be set (legacy method - use config loader instead)"""
        value = get_config(var_name, required=True)
        return value
    
    def get_session_path(self) -> Path:
        """Get the session file path"""
        return Path(self.SESSION_PATH) / 'oneminuta_prod'
    
    def validate(self) -> bool:
        """Validate required configuration"""
        try:
            # Check required configuration using centralized loader
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required")
            if not self.TELEGRAM_API_ID or not self.TELEGRAM_API_HASH:
                raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
            print("✅ Analytics configuration validated")
            return True
        except ValueError as e:
            print(f"❌ {e}")
            return False
    
    def get_telegram_config(self) -> tuple:
        """Get Telegram API configuration"""
        return self.TELEGRAM_API_ID, self.TELEGRAM_API_HASH


# Global config instance
_config = None

def get_config() -> AnalyticsConfig:
    """Get singleton config instance"""
    global _config
    if _config is None:
        _config = AnalyticsConfig()
    return _config