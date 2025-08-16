"""
Role-based permissions system for OneMinuta platform.

Manages user roles and permissions using file-based configuration.
Integrates with config_loader for consistent configuration management.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Set
from libs.config_loader import config as global_config

logger = logging.getLogger(__name__)


class PermissionManager:
    """Manages user roles and permissions"""
    
    def __init__(self):
        """Initialize permission manager with config files"""
        self.config_dir = Path(__file__).parent.parent / "config"
        self.roles_file = self.config_dir / "roles.json"
        self.user_roles_file = self.config_dir / "user_roles.json"
        
        # Cache for performance
        self._roles_cache = None
        self._user_roles_cache = None
        
        # Load configurations
        self._load_roles()
        self._load_user_roles()
    
    def _load_roles(self) -> Dict:
        """Load role definitions from config file"""
        try:
            if self.roles_file.exists():
                with open(self.roles_file, 'r', encoding='utf-8') as f:
                    self._roles_cache = json.load(f)
                    logger.info(f"Loaded roles configuration from {self.roles_file}")
            else:
                logger.warning(f"Roles file not found: {self.roles_file}")
                self._roles_cache = {"roles": {}, "default_role": "user"}
        except Exception as e:
            logger.error(f"Error loading roles: {e}")
            self._roles_cache = {"roles": {}, "default_role": "user"}
        
        return self._roles_cache
    
    def _load_user_roles(self) -> Dict:
        """Load user role assignments from config file"""
        try:
            if self.user_roles_file.exists():
                with open(self.user_roles_file, 'r', encoding='utf-8') as f:
                    self._user_roles_cache = json.load(f)
                    logger.info(f"Loaded user roles from {self.user_roles_file}")
            else:
                logger.warning(f"User roles file not found: {self.user_roles_file}")
                self._user_roles_cache = {"users": {}, "channel_mappings": {}}
        except Exception as e:
            logger.error(f"Error loading user roles: {e}")
            self._user_roles_cache = {"users": {}, "channel_mappings": {}}
        
        return self._user_roles_cache
    
    def _save_user_roles(self) -> bool:
        """Save user role assignments to config file"""
        try:
            with open(self.user_roles_file, 'w', encoding='utf-8') as f:
                json.dump(self._user_roles_cache, f, indent=2)
            logger.info(f"Saved user roles to {self.user_roles_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving user roles: {e}")
            return False
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get roles assigned to a user"""
        if not self._user_roles_cache:
            self._load_user_roles()
        
        user_id = str(user_id)  # Ensure string format
        roles = self._user_roles_cache.get("users", {}).get(user_id, [])
        
        # If no roles assigned, return default role
        if not roles:
            default_role = self._roles_cache.get("default_role", "user")
            roles = [default_role]
        
        return roles
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user based on their roles"""
        permissions = set()
        user_roles = self.get_user_roles(user_id)
        
        for role in user_roles:
            role_permissions = self._roles_cache.get("roles", {}).get(role, {}).get("permissions", [])
            permissions.update(role_permissions)
        
        return permissions
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        user_permissions = self.get_user_permissions(user_id)
        has_permission = permission in user_permissions
        
        logger.debug(f"Permission check: user={user_id}, permission={permission}, result={has_permission}")
        return has_permission
    
    def add_role(self, user_id: str, role: str) -> bool:
        """Add a role to a user"""
        user_id = str(user_id)
        
        # Check if role exists
        if role not in self._roles_cache.get("roles", {}):
            logger.error(f"Role does not exist: {role}")
            return False
        
        # Get current roles
        if user_id not in self._user_roles_cache["users"]:
            self._user_roles_cache["users"][user_id] = []
        
        # Add role if not already assigned
        if role not in self._user_roles_cache["users"][user_id]:
            self._user_roles_cache["users"][user_id].append(role)
            self._save_user_roles()
            logger.info(f"Added role '{role}' to user {user_id}")
            return True
        else:
            logger.info(f"User {user_id} already has role '{role}'")
            return True
    
    def remove_role(self, user_id: str, role: str) -> bool:
        """Remove a role from a user"""
        user_id = str(user_id)
        
        # Check if user has the role
        if user_id in self._user_roles_cache["users"]:
            if role in self._user_roles_cache["users"][user_id]:
                self._user_roles_cache["users"][user_id].remove(role)
                
                # Remove user entry if no roles left
                if not self._user_roles_cache["users"][user_id]:
                    del self._user_roles_cache["users"][user_id]
                
                self._save_user_roles()
                logger.info(f"Removed role '{role}' from user {user_id}")
                return True
        
        logger.info(f"User {user_id} does not have role '{role}'")
        return False
    
    def set_user_channel(self, user_id: str, channel_id: str) -> bool:
        """Set Telegram channel for a partner user in their metadata"""
        user_id = str(user_id)
        
        # Check if user is a partner
        if "partner" not in self.get_user_roles(user_id):
            logger.error(f"User {user_id} is not a partner")
            return False
        
        # Store in user's metadata file
        user_meta_dir = Path(__file__).parent.parent / "storage" / "chatbot" / "users" / user_id
        user_meta_dir.mkdir(parents=True, exist_ok=True)
        user_meta_file = user_meta_dir / "metadata.json"
        
        try:
            # Load existing metadata
            if user_meta_file.exists():
                with open(user_meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Set channel
            metadata['channel_id'] = channel_id
            metadata['last_updated'] = json.dumps(Path(__file__).stat().st_mtime)
            
            # Save metadata
            with open(user_meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Set channel {channel_id} for partner {user_id} in metadata")
            return True
            
        except Exception as e:
            logger.error(f"Error setting channel for user {user_id}: {e}")
            return False
    
    def get_user_channel(self, user_id: str) -> Optional[str]:
        """Get Telegram channel for a partner user from their metadata"""
        user_id = str(user_id)
        user_meta_file = Path(__file__).parent.parent / "storage" / "chatbot" / "users" / user_id / "metadata.json"
        
        try:
            if user_meta_file.exists():
                with open(user_meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                return metadata.get('channel_id')
        except Exception as e:
            logger.error(f"Error reading channel for user {user_id}: {e}")
        
        return None
    
    def list_users_by_role(self, role: str) -> List[str]:
        """List all users with a specific role"""
        users = []
        for user_id, user_roles in self._user_roles_cache.get("users", {}).items():
            if role in user_roles:
                users.append(user_id)
        return users
    
    def get_role_info(self, role: str) -> Dict:
        """Get information about a specific role"""
        return self._roles_cache.get("roles", {}).get(role, {})
    
    def clear_cache(self):
        """Clear cached data and reload from files"""
        self._roles_cache = None
        self._user_roles_cache = None
        self._load_roles()
        self._load_user_roles()
        logger.info("Cleared permission cache and reloaded from files")


# Singleton instance
permission_manager = PermissionManager()

# Convenience functions for easy import
def check_permission(user_id: str, permission: str) -> bool:
    """Check if user has a specific permission"""
    return permission_manager.check_permission(user_id, permission)

def get_user_roles(user_id: str) -> List[str]:
    """Get roles assigned to a user"""
    return permission_manager.get_user_roles(user_id)

def add_role(user_id: str, role: str) -> bool:
    """Add a role to a user"""
    return permission_manager.add_role(user_id, role)

def remove_role(user_id: str, role: str) -> bool:
    """Remove a role from a user"""
    return permission_manager.remove_role(user_id, role)

def get_user_permissions(user_id: str) -> Set[str]:
    """Get all permissions for a user"""
    return permission_manager.get_user_permissions(user_id)

def set_user_channel(user_id: str, channel_id: str) -> bool:
    """Set Telegram channel for a partner"""
    return permission_manager.set_user_channel(user_id, channel_id)

def get_user_channel(user_id: str) -> Optional[str]:
    """Get Telegram channel for a partner"""
    return permission_manager.get_user_channel(user_id)

def list_partners() -> List[str]:
    """List all partner users"""
    return permission_manager.list_users_by_role("partner")

def list_admins() -> List[str]:
    """List all admin users"""
    return permission_manager.list_users_by_role("admin")