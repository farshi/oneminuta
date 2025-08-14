"""
Chatbot Session Manager

Handles persistent storage and retrieval of conversation sessions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


class ChatbotSessionManager:
    """Manages chatbot conversation sessions with file-based persistence"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.sessions_dir = self.storage_path / "chatbot" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"ChatbotSessionManager initialized with storage: {self.sessions_dir}")
    
    async def get_session(self, user_id: str) -> Dict:
        """Get existing session or create new one"""
        session_file = self.sessions_dir / f"{user_id}.json"
        
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                self.logger.debug(f"Loaded existing session for {user_id}")
                return session
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.logger.warning(f"Error loading session for {user_id}: {e}")
                # Fall through to create new session
        
        # Create new session
        session = {
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_active': datetime.now(timezone.utc).isoformat(),
            'current_stage': 'user-profile-detection',
            'status': 'active',
            'message_count': 0,
            'collected_data': {},
            'conversation_history': []
        }
        
        await self.save_session(user_id, session)
        self.logger.info(f"Created new session for {user_id}")
        return session
    
    async def save_session(self, user_id: str, session: Dict) -> bool:
        """Save session to persistent storage"""
        try:
            session_file = self.sessions_dir / f"{user_id}.json"
            
            # Update last_active timestamp
            session['last_active'] = datetime.now(timezone.utc).isoformat()
            
            # Write session to file
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved session for {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving session for {user_id}: {e}")
            return False
    
    async def clear_session(self, user_id: str) -> bool:
        """Clear/reset session for user"""
        try:
            session_file = self.sessions_dir / f"{user_id}.json"
            
            if session_file.exists():
                # Archive old session before deleting
                archive_dir = self.sessions_dir / "archived"
                archive_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                archive_file = archive_dir / f"{user_id}_{timestamp}.json"
                
                # Move session to archive
                session_file.rename(archive_file)
                self.logger.info(f"Archived session for {user_id} to {archive_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing session for {user_id}: {e}")
            return False
    
    async def list_active_sessions(self) -> Dict[str, Dict]:
        """List all active sessions"""
        sessions = {}
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                if session_file.name == "archived":
                    continue
                    
                user_id = session_file.stem
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                    
                    # Include basic session info
                    sessions[user_id] = {
                        'user_id': user_id,
                        'current_stage': session.get('current_stage'),
                        'status': session.get('status'),
                        'message_count': session.get('message_count', 0),
                        'last_active': session.get('last_active'),
                        'created_at': session.get('created_at')
                    }
                    
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Error reading session {user_id}: {e}")
                    continue
            
            self.logger.info(f"Found {len(sessions)} active sessions")
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error listing sessions: {e}")
            return {}
    
    async def cleanup_inactive_sessions(self, days_inactive: int = 30) -> int:
        """Clean up sessions inactive for specified days"""
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        cleaned_count = 0
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                if session_file.name == "archived":
                    continue
                
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                    
                    last_active_str = session.get('last_active')
                    if last_active_str:
                        last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
                        
                        if last_active < cutoff_date:
                            # Archive inactive session
                            user_id = session_file.stem
                            await self.clear_session(user_id)
                            cleaned_count += 1
                            self.logger.info(f"Cleaned up inactive session: {user_id}")
                
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.warning(f"Error processing session {session_file.name}: {e}")
                    continue
            
            self.logger.info(f"Cleaned up {cleaned_count} inactive sessions")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return 0
    
    async def get_session_stats(self) -> Dict:
        """Get statistics about all sessions"""
        try:
            sessions = await self.list_active_sessions()
            
            stats = {
                'total_sessions': len(sessions),
                'by_stage': {},
                'by_status': {},
                'avg_messages': 0,
                'total_messages': 0
            }
            
            total_messages = 0
            
            for session_info in sessions.values():
                # Count by stage
                stage = session_info.get('current_stage', 'unknown')
                stats['by_stage'][stage] = stats['by_stage'].get(stage, 0) + 1
                
                # Count by status
                status = session_info.get('status', 'unknown')
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # Sum message counts
                msg_count = session_info.get('message_count', 0)
                total_messages += msg_count
            
            stats['total_messages'] = total_messages
            if len(sessions) > 0:
                stats['avg_messages'] = round(total_messages / len(sessions), 1)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting session stats: {e}")
            return {}