"""
Centralized Configuration Loader for OneMinuta Platform
Handles loading configuration from environment variables and .env files
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """
    Centralized configuration loader that follows the hierarchy:
    1. Environment variables (highest priority)
    2. .env file in project root
    3. Default values or error if required
    """
    
    _instance = None
    _config_cache: Dict[str, Any] = {}
    _env_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the config loader and load .env file once"""
        if not ConfigLoader._env_loaded:
            self._load_env_file()
            ConfigLoader._env_loaded = True
            self.logger = logging.getLogger(__name__)
    
    def _load_env_file(self):
        """Load .env file from project root"""
        # Find project root by looking for .env file
        current_path = Path(__file__).parent.parent  # libs/ -> project root
        env_path = current_path / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded configuration from {env_path}")
        else:
            # Try to find .env in parent directories
            for parent in current_path.parents:
                env_path = parent / '.env'
                if env_path.exists():
                    load_dotenv(env_path)
                    print(f"✅ Loaded configuration from {env_path}")
                    break
    
    def get(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        Get configuration value following the hierarchy:
        1. Check cache
        2. Check environment variable
        3. Check .env (already loaded into environment)
        4. Use default or raise error if required
        
        Args:
            key: Configuration key (e.g., 'OPENAI_API_KEY')
            default: Default value if not found
            required: If True, raise error when not found and no default
            
        Returns:
            Configuration value or None
        """
        # Check cache first
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Get from environment (includes .env values)
        value = os.getenv(key)
        
        if value is None:
            if required and default is None:
                error_msg = (
                    f"❌ Required configuration '{key}' not found!\n"
                    f"Please set it in one of these ways:\n"
                    f"1. Export as environment variable: export {key}='your-value'\n"
                    f"2. Add to .env file: {key}=your-value\n"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            value = default
        
        # Cache the value
        if value is not None:
            self._config_cache[key] = value
            
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            self.logger.warning(f"Invalid integer value for {key}: {value}, using default: {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float configuration value"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            self.logger.warning(f"Invalid float value for {key}: {value}, using default: {default}")
            return default
    
    def get_list(self, key: str, delimiter: str = ',', default: list = None) -> list:
        """Get list configuration value (comma-separated by default)"""
        value = self.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(delimiter) if item.strip()]
    
    def get_dict(self, prefix: str) -> Dict[str, str]:
        """
        Get all configuration values with a given prefix
        Example: get_dict('DB_') returns all DB_* configurations
        """
        result = {}
        for key in os.environ:
            if key.startswith(prefix):
                result[key] = os.environ[key]
        return result
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()
    
    def reload(self):
        """Reload configuration from environment and .env file"""
        self.clear_cache()
        self._load_env_file()


# Singleton instance
config = ConfigLoader()


# Convenience functions
def get_config(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get configuration value - convenience function"""
    return config.get(key, default, required)


def get_openai_api_key(required: bool = True) -> Optional[str]:
    """Get OpenAI API key from configuration"""
    return config.get('OPENAI_API_KEY', required=required)


def get_telegram_bot_token(required: bool = True) -> Optional[str]:
    """Get Telegram bot token from configuration"""
    return config.get('TELEGRAM_BOT_TOKEN', required=required)


def get_telegram_api_id(required: bool = False) -> Optional[str]:
    """Get Telegram API ID from configuration"""
    return config.get('TELEGRAM_API_ID', required=required)


def get_telegram_api_hash(required: bool = False) -> Optional[str]:
    """Get Telegram API hash from configuration"""
    return config.get('TELEGRAM_API_HASH', required=required)


def get_storage_path(default: str = './storage') -> str:
    """Get storage path from configuration"""
    return config.get('STORAGE_PATH', default=default)


def get_log_level(default: str = 'INFO') -> str:
    """Get log level from configuration"""
    return config.get('LOG_LEVEL', default=default)


def get_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return config.get_bool('DEBUG', default=False)


def get_test_mode() -> bool:
    """Check if test mode is enabled"""
    return config.get_bool('TEST_MODE', default=False)


# OneMinuta specific configurations
def get_partner_channels() -> list:
    """Get list of partner channels from configuration"""
    return config.get_list('PARTNER_CHANNELS', default=[])


def get_official_channel() -> str:
    """Get official OneMinuta channel"""
    return config.get('ONEMINUTA_OFFICIAL_CHANNEL', default='@oneminuta_property')


def get_commission_rate() -> float:
    """Get default commission rate"""
    return config.get_float('DEFAULT_COMMISSION_RATE', default=3.0)


if __name__ == "__main__":
    # Test the configuration loader
    print("Testing Configuration Loader")
    print("=" * 50)
    
    # Test getting various configurations
    print(f"OpenAI API Key exists: {get_openai_api_key(required=False) is not None}")
    print(f"Telegram Bot Token exists: {get_telegram_bot_token(required=False) is not None}")
    print(f"Storage Path: {get_storage_path()}")
    print(f"Debug Mode: {get_debug_mode()}")
    print(f"Test Mode: {get_test_mode()}")
    
    # Test getting with default
    print(f"Custom Config: {get_config('MY_CUSTOM_CONFIG', default='default_value')}")
    
    # Test error handling
    try:
        get_config('REQUIRED_BUT_MISSING', required=True)
    except ValueError as e:
        print(f"Expected error for missing required config: ✓")