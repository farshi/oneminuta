"""
Configuration for Analytics service
Centralized config loader following project guidelines
"""

import os
from typing import Optional, List
from pathlib import Path


class AnalyticsConfig:
    """Configuration for analytics services - single source of truth"""
    
    def __init__(self):
        """Load all config from environment variables"""
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env file"""
        # OpenAI/LLM Configuration
        self.OPENAI_API_KEY: str = self._require_env('OPENAI_API_KEY')
        self.LLM_MODEL: str = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        self.LLM_TEMPERATURE: float = float(os.getenv('LLM_TEMPERATURE', '0.1'))
        self.LLM_MAX_TOKENS: int = int(os.getenv('LLM_MAX_TOKENS', '1000'))
        
        # Telegram Configuration
        self.TELEGRAM_API_ID: int = int(self._require_env('TELEGRAM_API_ID'))
        self.TELEGRAM_API_HASH: str = self._require_env('TELEGRAM_API_HASH')
        
        # Storage Configuration
        self.STORAGE_PATH: str = os.getenv('STORAGE_PATH', './storage')
        self.SESSION_PATH: str = os.getenv('SESSION_PATH', './sessions')
        
        # Alert Configuration
        self.WEBHOOK_URL: Optional[str] = os.getenv('WEBHOOK_URL')
        self.HOT_CLIENT_THRESHOLD: float = float(os.getenv('HOT_CLIENT_THRESHOLD', '70.0'))
        self.BURNING_CLIENT_THRESHOLD: float = float(os.getenv('BURNING_CLIENT_THRESHOLD', '85.0'))
        
        # Monitoring Configuration - from environment
        channels_env = os.getenv('TELEGRAM_CHANNELS', '')
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
        languages_env = os.getenv('SUPPORTED_LANGUAGES', 'en,ru')
        self.SUPPORTED_LANGUAGES: List[str] = [lang.strip() for lang in languages_env.split(',')]
        self.DEFAULT_LANGUAGE: str = os.getenv('DEFAULT_LANGUAGE', 'en')
        
        # Analysis Configuration
        self.MAX_MESSAGES_PER_ANALYSIS: int = int(os.getenv('MAX_MESSAGES_PER_ANALYSIS', '20'))
        self.MAX_STORED_MESSAGES: int = int(os.getenv('MAX_STORED_MESSAGES', '50'))
        self.ANALYSIS_CACHE_TTL: int = int(os.getenv('ANALYSIS_CACHE_TTL', '3600'))
    
    def _require_env(self, var_name: str) -> str:
        """Require an environment variable to be set"""
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Required environment variable {var_name} not set")
        return value
    
    def get_session_path(self) -> Path:
        """Get the session file path"""
        return Path(self.SESSION_PATH) / 'oneminuta_prod'
    
    def validate(self) -> bool:
        """Validate required configuration"""
        try:
            # Required fields will raise ValueError if missing
            self._require_env('OPENAI_API_KEY')
            self._require_env('TELEGRAM_API_ID') 
            self._require_env('TELEGRAM_API_HASH')
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