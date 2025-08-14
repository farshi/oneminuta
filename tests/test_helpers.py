"""
Test helpers for OneMinuta test suite
Provides utilities for working with test fixtures and new storage structure
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.core.storage_manager import StorageManager
from services.collector.asset_manager import AssetManager
from services.analytics.channel_analytics import ChannelAnalytics


class TestStorageHelper:
    """Helper for managing test storage and fixtures"""
    
    def __init__(self, fixtures_path: str = None):
        if fixtures_path is None:
            fixtures_path = str(Path(__file__).parent / "fixtures")
        
        self.fixtures_path = Path(fixtures_path)
        if not self.fixtures_path.exists():
            raise FileNotFoundError(f"Fixtures path {fixtures_path} does not exist")
        
        # Initialize storage components with new structure
        self.storage_manager = StorageManager(str(self.fixtures_path))
        self.asset_manager = AssetManager(str(self.fixtures_path))
    
    def get_asset_manager(self) -> AssetManager:
        """Get AssetManager configured for test fixtures"""
        return self.asset_manager
    
    def get_storage_manager(self) -> StorageManager:
        """Get StorageManager configured for test fixtures"""
        return self.storage_manager
    
    def get_analytics(self) -> ChannelAnalytics:
        """Get ChannelAnalytics configured for test fixtures"""
        return ChannelAnalytics(str(self.fixtures_path))
    
    def search_test_properties(self, lat: float, lon: float, radius_m: float = 5000, **filters):
        """Search test properties using new storage system"""
        # Extract specific parameters for search_assets_by_location
        asset_type = filters.get('asset_type', 'property')
        transaction_type = filters.get('transaction_type')
        
        # Extract search filters (price, bedrooms, etc.)
        search_filters = {}
        for key in ['min_price', 'max_price', 'rent_or_sale', 'status']:
            if key in filters:
                search_filters[key] = filters[key]
        
        return self.storage_manager.search_assets_by_location(
            center_lat=lat,
            center_lon=lon, 
            radius_m=radius_m,
            asset_type=asset_type,
            transaction_type=transaction_type,
            filters=search_filters
        )
    
    def get_test_stats(self):
        """Get test fixture statistics"""
        return self.storage_manager.get_storage_stats()
    
    def list_test_users(self):
        """List all test users"""
        users = []
        users_path = self.fixtures_path / "users"
        if users_path.exists():
            for user_dir in users_path.iterdir():
                if user_dir.is_dir():
                    users.append(user_dir.name)
        return users
    
    def get_user_test_assets(self, username: str):
        """Get all assets for a test user"""
        return self.storage_manager.get_user_assets(username)


class TestFixtureManager:
    """Manager for test fixture data"""
    
    @staticmethod
    def get_sample_locations():
        """Get sample locations for testing"""
        return {
            'rawai': {'lat': 7.77965, 'lon': 98.32532, 'name': 'Rawai, Phuket'},
            'kata': {'lat': 7.8167, 'lon': 98.3500, 'name': 'Kata, Phuket'},
            'patong': {'lat': 7.8804, 'lon': 98.3923, 'name': 'Patong, Phuket'},
            'kamala': {'lat': 7.9519, 'lon': 98.3381, 'name': 'Kamala, Phuket'},
            'surin': {'lat': 8.0247, 'lon': 98.2674, 'name': 'Surin, Phuket'},
            'bangkok': {'lat': 13.7563, 'lon': 100.5018, 'name': 'Bangkok'}
        }
    
    @staticmethod
    def get_search_scenarios():
        """Get common search test scenarios"""
        locations = TestFixtureManager.get_sample_locations()
        
        return [
            {
                'name': 'Small radius - Rawai',
                'lat': locations['rawai']['lat'],
                'lon': locations['rawai']['lon'],
                'radius_m': 1000,
                'expected_min': 0
            },
            {
                'name': 'Medium radius - Rawai',
                'lat': locations['rawai']['lat'], 
                'lon': locations['rawai']['lon'],
                'radius_m': 5000,
                'expected_min': 1
            },
            {
                'name': 'Large radius - Phuket wide',
                'lat': locations['rawai']['lat'],
                'lon': locations['rawai']['lon'], 
                'radius_m': 20000,
                'expected_min': 5
            },
            {
                'name': 'Rent only - Medium radius',
                'lat': locations['rawai']['lat'],
                'lon': locations['rawai']['lon'],
                'radius_m': 10000,
                'filters': {'transaction_type': 'rent'},
                'expected_min': 1
            },
            {
                'name': 'Sale only - Medium radius',
                'lat': locations['rawai']['lat'],
                'lon': locations['rawai']['lon'],
                'radius_m': 10000,
                'filters': {'transaction_type': 'sell'},
                'expected_min': 1
            }
        ]


def get_test_storage_helper(fixtures_path: Optional[str] = None) -> TestStorageHelper:
    """Convenience function to get test storage helper"""
    return TestStorageHelper(fixtures_path)


def skip_if_no_fixtures():
    """Decorator to skip tests if fixtures are not available"""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            fixtures_path = Path(__file__).parent / "fixtures"
            if not fixtures_path.exists():
                print(f"⚠️  Skipping {test_func.__name__} - fixtures not found at {fixtures_path}")
                return
            
            try:
                return test_func(*args, **kwargs)
            except FileNotFoundError as e:
                print(f"⚠️  Skipping {test_func.__name__} - fixture error: {e}")
                return
        
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Test the helper
    try:
        helper = get_test_storage_helper()
        stats = helper.get_test_stats()
        print(f"Test fixtures loaded: {stats}")
        
        users = helper.list_test_users()
        print(f"Test users: {users}")
        
        # Try a search
        locations = TestFixtureManager.get_sample_locations()
        rawai = locations['rawai']
        
        results = helper.search_test_properties(
            lat=rawai['lat'],
            lon=rawai['lon'], 
            radius_m=10000
        )
        
        print(f"Test search found {len(results)} properties")
        
    except Exception as e:
        print(f"Test helper error: {e}")
        import traceback
        traceback.print_exc()