"""
Telegram Session Manager for Production
Handles session reuse and authentication properly
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger(__name__)


class TelegramSessionManager:
    """Manages Telegram sessions for production use"""
    
    def __init__(self, api_id: int, api_hash: str, session_dir: str = './sessions'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        
        # Use a single consistent session name
        self.session_name = str(self.session_dir / 'oneminuta_prod')
        self.client: Optional[TelegramClient] = None
        
    async def get_client(self) -> TelegramClient:
        """Get or create authenticated Telegram client"""
        
        if self.client and self.client.is_connected():
            return self.client
        
        # Create client with persistent session
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        
        try:
            # Start client
            await self.client.start()
            
            # Check if we're authorized
            if await self.client.is_user_authorized():
                logger.info("✅ Using existing session - no authentication needed")
            else:
                logger.warning("⚠️ Session exists but not authorized - may need to re-authenticate")
                
        except Exception as e:
            logger.error(f"Session error: {e}")
            # Try to recover by creating new session
            await self.reset_session()
            await self.client.start()
        
        return self.client
    
    async def reset_session(self):
        """Reset session file if corrupted"""
        logger.warning("Resetting session file...")
        
        # Disconnect if connected
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        
        # Remove old session file
        session_file = f"{self.session_name}.session"
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                logger.info("Old session file removed")
            except Exception as e:
                logger.error(f"Could not remove session file: {e}")
    
    async def authenticate_interactive(self, phone: Optional[str] = None):
        """Interactive authentication for first-time setup"""
        
        if not self.client:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        
        async def phone_callback():
            """Callback for phone number"""
            if phone:
                return phone
            return input('Please enter your phone number (with country code): ')
        
        async def code_callback():
            """Callback for verification code"""
            return input('Please enter the verification code: ')
        
        async def password_callback():
            """Callback for 2FA password"""
            return input('Please enter your 2FA password (if enabled): ')
        
        try:
            await self.client.start(
                phone=phone_callback,
                code_callback=code_callback,
                password=password_callback
            )
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                print(f"✅ Successfully authenticated as: {me.first_name} (@{me.username})")
                print(f"📁 Session saved to: {self.session_name}.session")
                return True
            
        except SessionPasswordNeededError:
            print("❌ 2FA is enabled. Please provide your password.")
            return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
        
        return False
    
    async def disconnect(self):
        """Properly disconnect client"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            logger.info("Client disconnected")
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.client and self.client.is_connected():
            asyncio.create_task(self.disconnect())


# Singleton instance for production
_session_manager: Optional[TelegramSessionManager] = None


def get_session_manager(api_id: int = None, api_hash: str = None) -> TelegramSessionManager:
    """Get singleton session manager instance"""
    global _session_manager
    
    if _session_manager is None:
        if api_id is None or api_hash is None:
            # Try to load from environment
            api_id = int(os.getenv('TELEGRAM_API_ID', 0))
            api_hash = os.getenv('TELEGRAM_API_HASH', '')
            
            if not api_id or not api_hash:
                raise ValueError("Telegram API credentials not provided")
        
        _session_manager = TelegramSessionManager(api_id, api_hash)
    
    return _session_manager