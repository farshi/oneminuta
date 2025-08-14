"""
File Watcher for Storage Reindexing
Monitors user storage directories for changes and updates indexing accordingly
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Set, Callable, Optional
from datetime import datetime
import json
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, DirCreatedEvent, DirDeletedEvent


class StorageFileHandler(FileSystemEventHandler):
    """Handles file system events for storage reindexing"""
    
    def __init__(self, storage_manager, reindex_callback: Optional[Callable] = None):
        self.storage_manager = storage_manager
        self.reindex_callback = reindex_callback
        self.logger = logging.getLogger(__name__)
        
        # Track pending reindex operations to avoid duplicate work
        self.pending_reindex = set()
        self.reindex_lock = threading.Lock()
        
        # Debounce mechanism - wait before processing changes
        self.debounce_delay = 2.0  # seconds
        self.pending_changes = {}
        self.timer = None
    
    def on_any_event(self, event):
        """Handle any file system event"""
        if event.is_directory:
            return
        
        # Only monitor changes in user asset directories
        path = Path(event.src_path)
        if not self._is_asset_file(path):
            return
        
        self.logger.debug(f"File event: {event.event_type} - {event.src_path}")
        
        # Extract asset information from path
        asset_info = self._extract_asset_info(path)
        if not asset_info:
            return
        
        # Handle different event types
        if isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
            self._schedule_reindex(asset_info, "update")
        elif isinstance(event, FileDeletedEvent):
            self._schedule_reindex(asset_info, "delete")
    
    def on_created(self, event):
        """Handle file/directory creation"""
        self.on_any_event(event)
    
    def on_modified(self, event):
        """Handle file modification"""
        self.on_any_event(event)
    
    def on_deleted(self, event):
        """Handle file deletion"""
        self.on_any_event(event)
    
    def _is_asset_file(self, path: Path) -> bool:
        """Check if file is an asset file that requires reindexing"""
        try:
            parts = path.parts
            
            # Look for pattern: storage/users/username/assets/assetType/availability/assetId/transaction/
            if 'users' not in parts:
                return False
            
            users_index = parts.index('users')
            
            # Should have: users/username/assets/assetType/availability/assetId/transaction/file
            if len(parts) <= users_index + 7:
                return False
            
            # Check if it's in the assets directory structure
            if parts[users_index + 2] != 'assets':
                return False
            
            # Check if it's an important asset file
            filename = path.name
            important_files = ['meta.json', 'state.json', 'description.txt']
            
            return filename in important_files
            
        except (ValueError, IndexError):
            return False
    
    def _extract_asset_info(self, path: Path) -> Optional[Dict[str, str]]:
        """Extract asset information from file path"""
        try:
            parts = path.parts
            users_index = parts.index('users')
            
            if len(parts) <= users_index + 7:
                return None
            
            username = parts[users_index + 1]
            asset_type = parts[users_index + 3]
            availability = parts[users_index + 4]
            asset_id = parts[users_index + 5]
            transaction_type = parts[users_index + 6]
            
            return {
                'username': username,
                'asset_type': asset_type,
                'availability': availability,
                'asset_id': asset_id,
                'transaction_type': transaction_type,
                'file_path': str(path)
            }
            
        except (ValueError, IndexError):
            return None
    
    def _schedule_reindex(self, asset_info: Dict[str, str], operation: str):
        """Schedule reindexing with debouncing"""
        key = f"{asset_info['username']}:{asset_info['asset_id']}:{asset_info['transaction_type']}"
        
        with self.reindex_lock:
            # Update pending changes
            self.pending_changes[key] = {
                'asset_info': asset_info,
                'operation': operation,
                'timestamp': time.time()
            }
            
            # Cancel previous timer
            if self.timer:
                self.timer.cancel()
            
            # Start new timer
            self.timer = threading.Timer(self.debounce_delay, self._process_pending_changes)
            self.timer.start()
    
    def _process_pending_changes(self):
        """Process all pending changes after debounce delay"""
        with self.reindex_lock:
            changes_to_process = self.pending_changes.copy()
            self.pending_changes.clear()
        
        for key, change in changes_to_process.items():
            try:
                asset_info = change['asset_info']
                operation = change['operation']
                
                self.logger.info(f"Processing {operation} for asset {asset_info['asset_id']}")
                
                if operation == "update":
                    self._reindex_asset(asset_info)
                elif operation == "delete":
                    self._remove_from_index(asset_info)
                
            except Exception as e:
                self.logger.error(f"Failed to process change for {key}: {e}")
    
    def _reindex_asset(self, asset_info: Dict[str, str]):
        """Reindex a single asset"""
        try:
            username = asset_info['username']
            asset_id = asset_info['asset_id']
            asset_type = asset_info['asset_type']
            transaction_type = asset_info['transaction_type']
            availability = asset_info['availability']
            
            # Only reindex available assets
            if availability != 'available':
                self.logger.debug(f"Skipping reindex of {availability} asset {asset_id}")
                return
            
            # Load asset data
            asset_dir = (self.storage_manager.users_path / username / "assets" / 
                        asset_type / availability / asset_id / transaction_type)
            
            if not asset_dir.exists():
                self.logger.warning(f"Asset directory not found: {asset_dir}")
                return
            
            asset_data = self.storage_manager._load_asset_data(asset_dir)
            if not asset_data:
                self.logger.warning(f"Could not load asset data for {asset_id}")
                return
            
            # Remove existing symlinks
            self.storage_manager._remove_indexed_symlinks(username, asset_id, asset_type, transaction_type)
            
            # Create new symlinks
            self.storage_manager._create_indexed_symlink(username, asset_id, asset_type, 
                                                       transaction_type, asset_dir, asset_data)
            
            self.logger.info(f"Reindexed asset {asset_id} for user {username}")
            
            # Call custom callback if provided
            if self.reindex_callback:
                self.reindex_callback(asset_info, "reindexed")
            
        except Exception as e:
            self.logger.error(f"Failed to reindex asset {asset_info.get('asset_id', 'unknown')}: {e}")
    
    def _remove_from_index(self, asset_info: Dict[str, str]):
        """Remove asset from index when deleted"""
        try:
            username = asset_info['username']
            asset_id = asset_info['asset_id']
            asset_type = asset_info['asset_type']
            transaction_type = asset_info['transaction_type']
            
            # Remove symlinks from indexed structure
            self.storage_manager._remove_indexed_symlinks(username, asset_id, asset_type, transaction_type)
            
            self.logger.info(f"Removed asset {asset_id} from index")
            
            # Call custom callback if provided
            if self.reindex_callback:
                self.reindex_callback(asset_info, "removed")
                
        except Exception as e:
            self.logger.error(f"Failed to remove asset {asset_info.get('asset_id', 'unknown')} from index: {e}")


class StorageFileWatcher:
    """File watcher for storage reindexing"""
    
    def __init__(self, storage_manager, reindex_callback: Optional[Callable] = None):
        self.storage_manager = storage_manager
        self.reindex_callback = reindex_callback
        self.logger = logging.getLogger(__name__)
        
        self.observer = Observer()
        self.handler = StorageFileHandler(storage_manager, reindex_callback)
        self.is_watching = False
    
    def start_watching(self):
        """Start watching storage directories for changes"""
        try:
            # Watch the users directory
            users_path = str(self.storage_manager.users_path)
            
            if not os.path.exists(users_path):
                self.logger.warning(f"Users path does not exist: {users_path}")
                return
            
            self.observer.schedule(self.handler, users_path, recursive=True)
            self.observer.start()
            self.is_watching = True
            
            self.logger.info(f"Started watching storage directory: {users_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}")
    
    def stop_watching(self):
        """Stop watching storage directories"""
        try:
            if self.is_watching:
                self.observer.stop()
                self.observer.join()
                self.is_watching = False
                self.logger.info("Stopped storage file watcher")
                
        except Exception as e:
            self.logger.error(f"Failed to stop file watcher: {e}")
    
    def is_alive(self) -> bool:
        """Check if watcher is running"""
        return self.is_watching and self.observer.is_alive()
    
    def get_stats(self) -> Dict[str, any]:
        """Get watcher statistics"""
        return {
            'is_watching': self.is_watching,
            'is_alive': self.is_alive(),
            'watched_path': str(self.storage_manager.users_path),
            'pending_changes': len(self.handler.pending_changes) if hasattr(self.handler, 'pending_changes') else 0
        }


def start_storage_watcher(storage_manager, reindex_callback: Optional[Callable] = None) -> StorageFileWatcher:
    """Convenience function to start storage file watcher"""
    watcher = StorageFileWatcher(storage_manager, reindex_callback)
    watcher.start_watching()
    return watcher


# Example usage with custom callback
def asset_change_callback(asset_info: Dict[str, str], operation: str):
    """Example callback for asset changes"""
    print(f"Asset {operation}: {asset_info['asset_id']} by {asset_info['username']}")


if __name__ == "__main__":
    # Example usage
    from storage_manager import StorageManager
    
    storage = StorageManager("./storage")
    watcher = start_storage_watcher(storage, asset_change_callback)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop_watching()