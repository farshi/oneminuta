"""
Unit tests for analytics configuration
"""

import os
import pytest
from unittest.mock import patch
from services.analytics.config import AnalyticsConfig, get_config


class TestAnalyticsConfig:
    """Test analytics configuration loading"""
    
    def test_config_requires_openai_key(self):
        """Test that OPENAI_API_KEY is required"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                AnalyticsConfig()
    
    def test_config_requires_telegram_credentials(self):
        """Test that Telegram credentials are required"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_API_ID"):
                AnalyticsConfig()
    
    def test_config_loads_defaults(self):
        """Test that default values are loaded correctly"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AnalyticsConfig()
            
            assert config.OPENAI_API_KEY == 'test-key'
            assert config.TELEGRAM_API_ID == 12345
            assert config.TELEGRAM_API_HASH == 'test-hash'
            assert config.LLM_MODEL == 'gpt-4o-mini'
            assert config.STORAGE_PATH == './storage'
            assert config.HOT_CLIENT_THRESHOLD == 70.0
    
    def test_config_parses_channels_from_env(self):
        """Test that channels can be configured via environment"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash',
            'TELEGRAM_CHANNELS': '@channel1, @channel2, @channel3'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AnalyticsConfig()
            
            assert config.DEFAULT_CHANNELS == ['@channel1', '@channel2', '@channel3']
    
    def test_config_parses_languages_from_env(self):
        """Test that supported languages can be configured"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash',
            'SUPPORTED_LANGUAGES': 'en, fr, de'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AnalyticsConfig()
            
            assert config.SUPPORTED_LANGUAGES == ['en', 'fr', 'de']
    
    def test_get_session_path(self):
        """Test session path generation"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash',
            'SESSION_PATH': './test-sessions'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AnalyticsConfig()
            
            assert str(config.get_session_path()) == 'test-sessions/oneminuta_prod'
    
    def test_config_validation_success(self):
        """Test successful config validation"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AnalyticsConfig()
            assert config.validate() is True
    
    def test_get_config_singleton(self):
        """Test that get_config returns singleton"""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test-hash'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Clear any existing config
            import services.analytics.config
            services.analytics.config._config = None
            
            config1 = get_config()
            config2 = get_config()
            
            assert config1 is config2