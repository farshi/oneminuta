"""
New Storage Manager for OneMinuta Platform
Implements improved storage structure:
- storage/users/username/assets/assetType/available|archived/assetId/rent|sell/
- storage/indexed/ (symlinks to available assets only)
- storage/sys/ (session files, analytics, etc.)
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import hashlib

# Add libs to path for SpheriCode imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'geo-spherical'))
from sphericode import encode_sphericode, prefixes_for_query
from spherical import inside_cap

from .models import (
    AssetType, RentOrSale, PropertyStatus, Location, PropertyMeta, 
    PropertyState, Price, Media, SpheriCode
)


class StorageManager:
    """New storage manager implementing the improved storage structure"""
    
    ASSET_TYPES = ["property", "vehicle", "service"]
    AVAILABILITY_STATES = ["available", "archived"]
    TRANSACTION_TYPES = ["rent", "sell"]
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)
        
        # Main storage directories
        self.users_path = self.storage_path / "users"
        self.indexed_path = self.storage_path / "indexed" 
        self.sys_path = self.storage_path / "sys"
        
        # Create base directories
        for path in [self.users_path, self.indexed_path, self.sys_path]:
            path.mkdir(parents=True, exist_ok=True)
            
        # SpheriCode configuration
        self.bits_per_axis = 16
        self.default_prefix_lengths = [2, 4, 6, 8]
    
    def create_user_structure(self, username: str) -> Path:
        """Create user directory structure with all asset types"""
        user_dir = self.users_path / username
        
        # Create assets directory structure
        for asset_type in self.ASSET_TYPES:
            for availability in self.AVAILABILITY_STATES:
                asset_dir = user_dir / "assets" / asset_type / availability
                asset_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Created user structure for {username}")
        return user_dir
    
    def store_asset(self, username: str, asset_id: str, asset_type: str, 
                   transaction_type: str, asset_data: Dict[str, Any], 
                   media_files: List[Path] = None) -> bool:
        """
        Store asset in new structure
        
        Args:
            username: User's directory name
            asset_id: Unique asset identifier  
            asset_type: property, vehicle, service
            transaction_type: rent, sell
            asset_data: Asset metadata and state
            media_files: List of media file paths to copy
        """
        try:
            # Validate inputs
            if asset_type not in self.ASSET_TYPES:
                raise ValueError(f"Asset type {asset_type} not supported")
            if transaction_type not in self.TRANSACTION_TYPES:
                raise ValueError(f"Transaction type {transaction_type} not supported")
            
            # Create user structure if needed
            user_dir = self.create_user_structure(username)
            
            # Asset is available by default when first created
            availability = "available"
            
            # Create asset directory: username/assets/property/available/asset_id/rent/
            asset_dir = user_dir / "assets" / asset_type / availability / asset_id / transaction_type
            asset_dir.mkdir(parents=True, exist_ok=True)
            
            # Store asset metadata
            meta_file = asset_dir / "meta.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(asset_data.get("meta", {}), f, indent=2, ensure_ascii=False, default=str)
            
            # Store asset state
            state_file = asset_dir / "state.json"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(asset_data.get("state", {}), f, indent=2, ensure_ascii=False, default=str)
            
            # Store description
            if "description" in asset_data:
                desc_file = asset_dir / "description.txt"
                with open(desc_file, "w", encoding="utf-8") as f:
                    f.write(asset_data["description"])
            
            # Copy media files
            if media_files:
                photos_dir = asset_dir / "photos"
                photos_dir.mkdir(exist_ok=True)
                for media_file in media_files:
                    if media_file.exists():
                        import shutil
                        shutil.copy2(media_file, photos_dir / media_file.name)
            
            # Create symlink in indexed structure for available assets
            if availability == "available":
                self._create_indexed_symlink(username, asset_id, asset_type, 
                                           transaction_type, asset_dir, asset_data)
            
            self.logger.info(f"Stored asset {asset_id} for user {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store asset {asset_id}: {e}")
            return False
    
    def _create_indexed_symlink(self, username: str, asset_id: str, asset_type: str,
                              transaction_type: str, asset_dir: Path, asset_data: Dict[str, Any]):
        """Create symlink in indexed structure for geo-spatial searching"""
        try:
            # Get location from asset data
            location = asset_data.get("meta", {}).get("location")
            if not location:
                self.logger.warning(f"No location for asset {asset_id}, skipping indexing")
                return
            
            lat = location["lat"]
            lon = location["lon"]
            country = location.get("country", "TH")
            
            # Generate SpheriCode for this location
            spheri_code = encode_sphericode(lat, lon, self.bits_per_axis)
            
            # Create symlinks at multiple precision levels
            for prefix_len in self.default_prefix_lengths:
                prefix = spheri_code[:prefix_len]
                nested_path = self._create_nested_path(prefix)
                
                # Structure: storage/indexed/TH/spheri/3/g/6/f/property/rent/
                indexed_dir = (self.indexed_path / country / "spheri" / nested_path / 
                             asset_type / transaction_type)
                indexed_dir.mkdir(parents=True, exist_ok=True)
                
                # Create symlink to actual asset directory
                symlink_path = indexed_dir / f"{username}_{asset_id}"
                
                # Remove existing symlink if it exists
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                
                # Create new symlink with relative path to avoid absolute path issues
                relative_asset_dir = os.path.relpath(asset_dir, symlink_path.parent)
                symlink_path.symlink_to(relative_asset_dir, target_is_directory=True)
                
            self.logger.info(f"Created indexed symlinks for asset {asset_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create indexed symlinks for {asset_id}: {e}")
    
    def _create_nested_path(self, prefix: str) -> str:
        """Convert SpheriCode prefix to nested directory path"""
        if not prefix:
            return ""
        
        chars = list(prefix.lower())
        return "/".join(chars)
    
    def archive_asset(self, username: str, asset_id: str, asset_type: str, 
                     transaction_type: str) -> bool:
        """Move asset from available to archived and remove from indexing"""
        try:
            user_dir = self.users_path / username / "assets" / asset_type
            
            # Source and destination paths
            available_dir = user_dir / "available" / asset_id / transaction_type
            archived_dir = user_dir / "archived" / asset_id / transaction_type
            
            if not available_dir.exists():
                self.logger.warning(f"Asset {asset_id} not found in available")
                return False
            
            # Create archived directory structure
            archived_dir.mkdir(parents=True, exist_ok=True)
            
            # Move files
            import shutil
            for item in available_dir.iterdir():
                dest = archived_dir / item.name
                if item.is_file():
                    shutil.move(str(item), str(dest))
                elif item.is_dir():
                    shutil.move(str(item), str(dest))
            
            # Remove empty available directory
            available_dir.rmdir()
            if available_dir.parent.exists() and not any(available_dir.parent.iterdir()):
                available_dir.parent.rmdir()
            
            # Remove symlinks from indexed structure
            self._remove_indexed_symlinks(username, asset_id, asset_type, transaction_type)
            
            self.logger.info(f"Archived asset {asset_id} for user {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to archive asset {asset_id}: {e}")
            return False
    
    def _remove_indexed_symlinks(self, username: str, asset_id: str, 
                                asset_type: str, transaction_type: str):
        """Remove symlinks from indexed structure when archiving"""
        try:
            # Find and remove all symlinks for this asset
            pattern = f"{username}_{asset_id}"
            indexed_base = self.indexed_path
            
            # Search through all indexed directories
            for country_dir in indexed_base.iterdir():
                if not country_dir.is_dir():
                    continue
                
                spheri_dir = country_dir / "spheri"
                if not spheri_dir.exists():
                    continue
                
                # Find symlinks recursively
                for symlink_path in spheri_dir.rglob(pattern):
                    if symlink_path.is_symlink():
                        symlink_path.unlink()
                        self.logger.debug(f"Removed symlink {symlink_path}")
                        
        except Exception as e:
            self.logger.error(f"Failed to remove symlinks for {asset_id}: {e}")
    
    def unarchive_asset(self, username: str, asset_id: str, asset_type: str,
                       transaction_type: str) -> bool:
        """Move asset from archived back to available and reindex"""
        try:
            user_dir = self.users_path / username / "assets" / asset_type
            
            # Source and destination paths  
            archived_dir = user_dir / "archived" / asset_id / transaction_type
            available_dir = user_dir / "available" / asset_id / transaction_type
            
            if not archived_dir.exists():
                self.logger.warning(f"Asset {asset_id} not found in archived")
                return False
            
            # Create available directory structure
            available_dir.mkdir(parents=True, exist_ok=True)
            
            # Move files back
            import shutil
            for item in archived_dir.iterdir():
                dest = available_dir / item.name
                if item.is_file():
                    shutil.move(str(item), str(dest))
                elif item.is_dir():
                    shutil.move(str(item), str(dest))
            
            # Remove empty archived directory
            archived_dir.rmdir()
            if archived_dir.parent.exists() and not any(archived_dir.parent.iterdir()):
                archived_dir.parent.rmdir()
            
            # Recreate symlinks in indexed structure
            asset_data = self._load_asset_data(available_dir)
            if asset_data:
                self._create_indexed_symlink(username, asset_id, asset_type,
                                           transaction_type, available_dir, asset_data)
            
            self.logger.info(f"Unarchived asset {asset_id} for user {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unarchive asset {asset_id}: {e}")
            return False
    
    def _load_asset_data(self, asset_dir: Path) -> Optional[Dict[str, Any]]:
        """Load asset data from directory"""
        try:
            asset_data = {}
            
            meta_file = asset_dir / "meta.json"
            if meta_file.exists():
                with open(meta_file, "r", encoding="utf-8") as f:
                    asset_data["meta"] = json.load(f)
            
            state_file = asset_dir / "state.json"
            if state_file.exists():
                with open(state_file, "r", encoding="utf-8") as f:
                    asset_data["state"] = json.load(f)
            
            desc_file = asset_dir / "description.txt"
            if desc_file.exists():
                with open(desc_file, "r", encoding="utf-8") as f:
                    asset_data["description"] = f.read()
                    
            return asset_data
            
        except Exception as e:
            self.logger.error(f"Failed to load asset data from {asset_dir}: {e}")
            return None
    
    def search_assets_by_location(self, center_lat: float, center_lon: float,
                                radius_m: float, asset_type: str = None,
                                transaction_type: str = None,
                                filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search available assets using geo-spatial queries with symlinks"""
        filters = filters or {}
        
        try:
            # Get SpheriCode prefixes that cover the search area
            prefixes = prefixes_for_query(center_lat, center_lon, radius_m, self.bits_per_axis)
            
            results = []
            seen = set()
            
            for prefix in prefixes:
                nested_path = self._create_nested_path(prefix)
                country = "TH"  # TODO: Make dynamic
                
                # Search in indexed structure
                base_path = self.indexed_path / country / "spheri" / nested_path
                
                if not base_path.exists():
                    continue
                
                # Search specific asset type and transaction type if specified
                search_paths = []
                if asset_type and transaction_type:
                    search_paths = [base_path / asset_type / transaction_type]
                elif asset_type:
                    for trans_type in self.TRANSACTION_TYPES:
                        search_paths.append(base_path / asset_type / trans_type)
                else:
                    for a_type in self.ASSET_TYPES:
                        for trans_type in self.TRANSACTION_TYPES:
                            search_paths.append(base_path / a_type / trans_type)
                
                # Check each search path
                for search_path in search_paths:
                    if not search_path.exists():
                        continue
                    
                    # Find symlinks (which point to available assets)
                    for symlink in search_path.iterdir():
                        if not symlink.is_symlink():
                            continue
                        
                        try:
                            # Load asset data from symlinked directory
                            asset_data = self._load_asset_data(symlink)
                            if not asset_data:
                                continue
                            
                            location = asset_data.get("meta", {}).get("location", {})
                            if not location:
                                continue
                            
                            asset_lat = location.get("lat")
                            asset_lon = location.get("lon")
                            if asset_lat is None or asset_lon is None:
                                continue
                            
                            # Precise distance check
                            if not inside_cap(center_lat, center_lon, radius_m,
                                            asset_lat, asset_lon):
                                continue
                            
                            # Apply additional filters
                            if self._matches_filters(asset_data, filters):
                                asset_id = asset_data.get("meta", {}).get("id")
                                username = symlink.name.split("_")[0]
                                
                                key = f"{username}:{asset_id}"
                                if key not in seen:
                                    seen.add(key)
                                    
                                    result = {
                                        "username": username,
                                        "asset_id": asset_id,
                                        "asset_data": asset_data,
                                        "symlink_path": str(symlink),
                                        "actual_path": str(symlink.resolve())
                                    }
                                    results.append(result)
                            
                        except Exception as e:
                            self.logger.warning(f"Error processing symlink {symlink}: {e}")
                            continue
            
            self.logger.info(f"Found {len(results)} assets in {radius_m}m radius")
            return results
            
        except Exception as e:
            self.logger.error(f"Geo-spatial search failed: {e}")
            return []
    
    def _matches_filters(self, asset_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if asset matches search filters"""
        meta = asset_data.get("meta", {})
        state = asset_data.get("state", {})
        
        if filters.get("asset_type") and meta.get("asset_type") != filters["asset_type"]:
            return False
        if filters.get("rent_or_sale") and state.get("for_rent_or_sale") != filters["rent_or_sale"]:
            return False
        if filters.get("min_price"):
            price = state.get("price", {}).get("value", 0)
            if price < filters["min_price"]:
                return False
        if filters.get("max_price"):
            price = state.get("price", {}).get("value", float('inf'))
            if price > filters["max_price"]:
                return False
        if filters.get("status") and state.get("status") != filters["status"]:
            return False
            
        return True
    
    def get_user_assets(self, username: str, asset_type: str = None,
                       availability: str = None) -> List[Dict[str, Any]]:
        """Get all assets for a user"""
        try:
            user_dir = self.users_path / username
            if not user_dir.exists():
                return []
            
            assets = []
            
            # Determine which asset types to check
            asset_types = [asset_type] if asset_type else self.ASSET_TYPES
            
            # Determine which availability states to check  
            availabilities = [availability] if availability else self.AVAILABILITY_STATES
            
            for a_type in asset_types:
                for avail in availabilities:
                    asset_base_dir = user_dir / "assets" / a_type / avail
                    if not asset_base_dir.exists():
                        continue
                    
                    # Each asset ID directory
                    for asset_id_dir in asset_base_dir.iterdir():
                        if not asset_id_dir.is_dir():
                            continue
                        
                        asset_id = asset_id_dir.name
                        
                        # Each transaction type directory
                        for trans_dir in asset_id_dir.iterdir():
                            if not trans_dir.is_dir():
                                continue
                            
                            transaction_type = trans_dir.name
                            asset_data = self._load_asset_data(trans_dir)
                            
                            if asset_data:
                                assets.append({
                                    "username": username,
                                    "asset_id": asset_id,
                                    "asset_type": a_type,
                                    "transaction_type": transaction_type,
                                    "availability": avail,
                                    "asset_data": asset_data,
                                    "path": str(trans_dir)
                                })
            
            return assets
            
        except Exception as e:
            self.logger.error(f"Failed to get assets for user {username}: {e}")
            return []
    
    def move_sessions_to_sys(self):
        """Move session files and analytics to storage/sys/"""
        try:
            # Move from old storage structure to sys
            old_storage = self.storage_path.parent / "_storage"
            
            # Move session files
            if (old_storage / "chatbot" / "sessions").exists():
                dest_dir = self.sys_path / "chatbot" / "sessions"
                dest_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copytree(old_storage / "chatbot" / "sessions", dest_dir, dirs_exist_ok=True)
            
            # Move analytics
            if (old_storage / "analytics").exists():
                dest_dir = self.sys_path / "analytics"
                dest_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copytree(old_storage / "analytics", dest_dir, dirs_exist_ok=True)
            
            # Move telegram sessions
            if (old_storage / "telegram_sessions").exists():
                dest_dir = self.sys_path / "telegram_sessions"
                dest_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copytree(old_storage / "telegram_sessions", dest_dir, dirs_exist_ok=True)
            
            self.logger.info("Moved session files and analytics to storage/sys/")
            
        except Exception as e:
            self.logger.error(f"Failed to move sessions to sys: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                "users": 0,
                "total_assets": 0,
                "available_assets": 0,
                "archived_assets": 0,
                "by_asset_type": {},
                "by_transaction_type": {},
                "indexed_symlinks": 0
            }
            
            # Count user directories
            if self.users_path.exists():
                stats["users"] = len([d for d in self.users_path.iterdir() if d.is_dir()])
            
            # Count assets by traversing user directories
            for user_dir in self.users_path.iterdir():
                if not user_dir.is_dir():
                    continue
                
                assets_dir = user_dir / "assets"
                if not assets_dir.exists():
                    continue
                
                for asset_type_dir in assets_dir.iterdir():
                    if not asset_type_dir.is_dir():
                        continue
                    
                    asset_type = asset_type_dir.name
                    
                    for availability_dir in asset_type_dir.iterdir():
                        if not availability_dir.is_dir():
                            continue
                        
                        availability = availability_dir.name
                        
                        # Count assets in this availability state
                        asset_count = len([d for d in availability_dir.iterdir() if d.is_dir()])
                        
                        stats["total_assets"] += asset_count
                        if availability == "available":
                            stats["available_assets"] += asset_count
                        elif availability == "archived":
                            stats["archived_assets"] += asset_count
                        
                        if asset_type not in stats["by_asset_type"]:
                            stats["by_asset_type"][asset_type] = 0
                        stats["by_asset_type"][asset_type] += asset_count
            
            # Count indexed symlinks
            if self.indexed_path.exists():
                symlink_count = 0
                for symlink in self.indexed_path.rglob("*"):
                    if symlink.is_symlink():
                        symlink_count += 1
                stats["indexed_symlinks"] = symlink_count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return {}