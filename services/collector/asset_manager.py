"""
Asset Manager for Property Collection
Integrates extracted properties with OneMinuta's asset storage system
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys
import os

# Add libs to path for SpheriCode imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'geo-spherical'))
from sphericode import encode_sphericode, prefixes_for_query
from spherical import inside_cap

from services.core.models import (
    AssetType,
    RentOrSale,
    Location,
    PropertyMeta,
    PropertyState,
    Price,
    Media,
    PropertyStatus,
    SpheriCode,
)
from .property_extractor import ExtractedProperty


class AssetManager:
    """Manages property assets in OneMinuta storage system"""

    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)

        # Ensure storage directories exist
        self.users_path = self.storage_path / "users"
        self.geo_path = self.storage_path / "geo"
        self.global_path = self.storage_path / "global"

        for path in [self.users_path, self.geo_path, self.global_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Telegram channel user mapping (configurable via environment)
        self.channel_users = self._load_channel_user_mapping()

        # Location mapping for Thailand - hierarchical cone caps
        # Rawai (small) → Phuket (medium) → Thailand (large)
        self.location_mapping = {
            # Major cities/provinces (parent cone caps)
            "bangkok": {"lat": 13.7563, "lon": 100.5018, "radius_km": 50, "type": "province"},
            "phuket": {"lat": 7.8804, "lon": 98.3923, "radius_km": 25, "type": "province"},
            "pattaya": {"lat": 12.9236, "lon": 100.8825, "radius_km": 15, "type": "city"},
            "chiang mai": {"lat": 18.7883, "lon": 98.9853, "radius_km": 20, "type": "province"},
            
            # Sub-areas within Phuket (child cone caps)
            "rawai": {"lat": 7.77965, "lon": 98.32532, "radius_km": 3, "type": "district", "parent": "phuket"},
            "patong": {"lat": 7.89608, "lon": 98.29193, "radius_km": 2, "type": "district", "parent": "phuket"},
            "kata": {"lat": 7.81667, "lon": 98.30000, "radius_km": 2, "type": "district", "parent": "phuket"},
            "karon": {"lat": 7.83700, "lon": 98.30400, "radius_km": 2, "type": "district", "parent": "phuket"},
            "bang tao": {"lat": 8.02500, "lon": 98.28700, "radius_km": 3, "type": "district", "parent": "phuket"},
            
            # Sub-areas within Bangkok
            "sukhumvit": {"lat": 13.7367, "lon": 100.5588, "radius_km": 5, "type": "district", "parent": "bangkok"},
            "silom": {"lat": 13.7243, "lon": 100.5265, "radius_km": 3, "type": "district", "parent": "bangkok"},
            "sathorn": {"lat": 13.7199, "lon": 100.5252, "radius_km": 3, "type": "district", "parent": "bangkok"},
            
            # Other locations
            "hua hin": {"lat": 12.5664, "lon": 99.9581, "radius_km": 10, "type": "city"},
            "koh samui": {"lat": 9.5380, "lon": 100.0614, "radius_km": 8, "type": "island"},
        }
        
        # SpheriCode configuration
        self.bits_per_axis = 16
        self.default_prefix_lengths = [2, 4, 6, 8]  # Different precision levels

    def _load_channel_user_mapping(self) -> Dict[str, str]:
        """Load channel to user ID mapping"""
        # Map Telegram channels to user IDs who can post listings
        # In production, this would come from user permissions configuration
        mapping = {
            "@phuketgidsell": "tg_phuketgidsell",
            "@phuketgid": "tg_phuketgid",
            "@sabay_property": "tg_sabay_property",
        }

        # Create user directories if they don't exist
        for user_id in mapping.values():
            user_dir = self.users_path / user_id
            user_dir.mkdir(exist_ok=True)

            # Create user meta.json if it doesn't exist
            meta_file = user_dir / "meta.json"
            if not meta_file.exists():
                user_meta = {
                    "user_id": user_id,
                    "type": "telegram_channel",
                    "created_at": datetime.utcnow().isoformat(),
                    "display_name": mapping[
                        list(mapping.keys())[list(mapping.values()).index(user_id)]
                    ],
                    "source": "telegram_collector",
                    "active": True,
                    "permissions": ["create_listings", "edit_listings", "delete_listings"],
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(user_meta, f, indent=2, ensure_ascii=False)

        return mapping

    def _generate_asset_id(self, extracted: ExtractedProperty) -> str:
        """Generate unique asset ID based on message content"""
        # Create hash from channel, message_id, and key content
        content = f"{extracted.channel}_{extracted.message_id}_{extracted.sender_id}"
        return hashlib.md5(content.encode()).hexdigest()

    def _map_location(self, extracted: ExtractedProperty) -> Optional[Location]:
        """Map extracted location to geo coordinates with hierarchical matching"""
        if not extracted.extracted_locations:
            return None

        # Find the most specific location match (prefer child over parent)
        best_match = None
        best_specificity = 0
        
        for location_text in extracted.extracted_locations:
            location_key = location_text.lower().strip()

            # Try exact match first
            if location_key in self.location_mapping:
                geo_data = self.location_mapping[location_key]
                specificity = self._get_location_specificity(geo_data)
                if specificity > best_specificity:
                    best_match = (location_key, location_text, geo_data)
                    best_specificity = specificity

            # Try partial match
            for mapped_location, geo_data in self.location_mapping.items():
                if mapped_location in location_key or location_key in mapped_location:
                    specificity = self._get_location_specificity(geo_data)
                    if specificity > best_specificity:
                        best_match = (mapped_location, location_text, geo_data)
                        best_specificity = specificity

        if not best_match:
            return None
            
        location_key, location_text, geo_data = best_match
        
        # Determine city based on hierarchy
        city = self._get_city_for_location(location_key, geo_data)
        
        return Location(
            city=city,
            area=location_text,
            lat=geo_data["lat"],
            lon=geo_data["lon"],
            country="TH"  # Hardcoded for Thailand for now
        )
    
    def _get_location_specificity(self, geo_data: dict) -> int:
        """Get specificity score for location (higher = more specific)"""
        location_type = geo_data.get("type", "unknown")
        specificity_scores = {
            "district": 3,  # Most specific (e.g., Rawai)
            "city": 2,      # Medium (e.g., Pattaya)
            "island": 2,    # Medium (e.g., Koh Samui)
            "province": 1,  # Least specific (e.g., Phuket province)
            "unknown": 0
        }
        return specificity_scores.get(location_type, 0)
    
    def _get_city_for_location(self, location_key: str, geo_data: dict) -> str:
        """Get appropriate city name based on location hierarchy"""
        # If it has a parent, use the parent as city
        if "parent" in geo_data:
            parent_key = geo_data["parent"]
            parent_data = self.location_mapping.get(parent_key, {})
            return parent_key.title()
        
        # Otherwise, use itself as city
        return location_key.title()

    def _extract_property_fields(self, extracted: ExtractedProperty) -> dict:
        """Extract property fields for PropertyState"""
        fields = {}

        # Basic fields
        fields["bedrooms"] = extracted.bedrooms
        fields["bathrooms"] = extracted.bathrooms
        fields["area_sqm"] = extracted.size_sqm
        fields["floor"] = extracted.floor

        # Features
        fields["furnished"] = "furnished" in extracted.features
        fields["parking"] = 1 if "parking" in extracted.features else None

        return fields

    def convert_to_asset(self, extracted: ExtractedProperty) -> dict:
        """Convert ExtractedProperty to OneMinuta storage format"""
        asset_id = self._generate_asset_id(extracted)
        location = self._map_location(extracted)
        property_fields = self._extract_property_fields(extracted)

        # Get user ID from channel mapping  
        user_id = self.channel_users.get(extracted.channel, "unknown_user")

        # CRITICAL: Location is MANDATORY - OneMinuta requires geo-sharding
        if not location:
            self.logger.warning(f"Skipping asset {asset_id} - no location found (required for geo-sharding)")
            return None
            
        # CRITICAL: Price is MANDATORY - even if 0, must be specified
        if extracted.price is None:
            self.logger.warning(f"Skipping asset {asset_id} - no price found (required field)")
            return None

        meta = PropertyMeta(
            id=asset_id,
            owner_user_id=user_id,
            asset_type=extracted.asset_type or AssetType.CONDO,
            location=location,
            created_at=extracted.message_date,
            source_channel=extracted.channel,
            source_message_id=extracted.message_id,
        )

        # Create PropertyState (mutable)
        state = PropertyState(
            for_rent_or_sale=extracted.rent_or_sale or RentOrSale.SALE,
            price=Price(
                value=extracted.price,  # Now guaranteed to exist
                currency=extracted.currency,
                period="month" if extracted.rent_or_sale == RentOrSale.RENT else None,
            ),
            status=PropertyStatus.AVAILABLE,
            last_updated=datetime.utcnow(),
            spheri=SpheriCode(code="temp", bits_per_axis=self.bits_per_axis, prefix_len=8),  # Will be calculated in geo indexing
            media=Media(),
            **property_fields,
        )

        # Combine into storage format
        asset_data = {
            "meta": meta.dict(),
            "state": state.dict(),
            "telegram_metadata": {
                "sender_id": extracted.sender_id,
                "extraction_confidence": extracted.extraction_confidence,
                "extracted_locations": extracted.extracted_locations,
                "extracted_features": extracted.features,
                "has_photos": extracted.has_photos,
                "photo_count": extracted.photo_count,
                "message_text": extracted.message_text,
                "contact_info": extracted.contact_info,
            },
        }

        return asset_data
    
    def _create_nested_path(self, prefix: str) -> str:
        """Convert SpheriCode prefix to nested directory path
        
        Examples:
        '3G' -> '3/g'
        '3G6F' -> '3/g/6/f'  
        '3G6FBS' -> '3/g/6/f/b/s'
        '3G6FBSR' -> '3/g/6/f/b/s/r'
        """
        if not prefix:
            return ""
        
        # Convert to lowercase and split into individual characters
        chars = list(prefix.lower())
        
        # Join with path separator
        return "/".join(chars)
    
    def search_assets_by_location(self, center_lat: float, center_lon: float, 
                                 radius_m: float, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search assets using proper geo-spatial queries with SpheriCode"""
        filters = filters or {}
        
        try:
            # Get SpheriCode prefixes that cover the search area
            prefixes = prefixes_for_query(center_lat, center_lon, radius_m, self.bits_per_axis)
            
            results = []
            
            for prefix in prefixes:
                # Look in geo structure with nested paths
                country = "TH"  # TODO: Make this dynamic
                nested_path = self._create_nested_path(prefix)
                geo_cell_dir = self.geo_path / country / "spheri" / nested_path
                properties_dir = geo_cell_dir / "properties"
                
                if not properties_dir.exists():
                    continue
                
                # Read all property references in this cell
                for prop_file in properties_dir.glob("*.json"):
                    try:
                        with open(prop_file, "r", encoding="utf-8") as f:
                            prop_ref = json.load(f)
                        
                        # Apply distance filter (precise check)
                        if not inside_cap(center_lat, center_lon, radius_m, 
                                        prop_ref["lat"], prop_ref["lon"]):
                            continue
                        
                        # Apply other filters
                        if self._matches_filters(prop_ref, filters):
                            results.append(prop_ref)
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Corrupted property reference {prop_file}: {e}")
                        continue
            
            # Remove duplicates (same asset might appear in multiple cells)
            seen = set()
            unique_results = []
            for result in results:
                key = f"{result['user_id']}:{result['asset_id']}"
                if key not in seen:
                    seen.add(key)
                    unique_results.append(result)
            
            self.logger.info(f"Geo-spatial search found {len(unique_results)} assets in {radius_m}m radius")
            return unique_results
            
        except Exception as e:
            self.logger.error(f"Geo-spatial search failed: {e}")
            return []
    
    def _matches_filters(self, asset_ref: dict, filters: Dict[str, Any]) -> bool:
        """Check if asset reference matches search filters"""
        if filters.get("asset_type") and asset_ref.get("asset_type") != filters["asset_type"]:
            return False
        if filters.get("rent_or_sale") and asset_ref.get("rent_or_sale") != filters["rent_or_sale"]:
            return False
        if filters.get("min_price") and asset_ref.get("price", 0) < filters["min_price"]:
            return False
        if filters.get("max_price") and asset_ref.get("price", float('inf')) > filters["max_price"]:
            return False
        if filters.get("status") and asset_ref.get("status") != filters["status"]:
            return False
        return True
    
    def search_assets_countrywide(self, country: str = "TH", filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search all assets in a country efficiently using nested structure"""
        filters = filters or {}
        
        try:
            # Use glob pattern to find all property files in country
            country_path = self.geo_path / country / "spheri"
            if not country_path.exists():
                return []
            
            # Efficiently traverse nested structure
            property_files = list(country_path.rglob("properties/*.json"))
            
            results = []
            seen = set()
            
            for prop_file in property_files:
                try:
                    with open(prop_file, "r", encoding="utf-8") as f:
                        prop_ref = json.load(f)
                    
                    # Apply filters
                    if self._matches_filters(prop_ref, filters):
                        # Avoid duplicates
                        key = f"{prop_ref['user_id']}:{prop_ref['asset_id']}"
                        if key not in seen:
                            seen.add(key)
                            results.append(prop_ref)
                            
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Corrupted property reference {prop_file}: {e}")
                    continue
            
            self.logger.info(f"Country-wide search in {country} found {len(results)} assets")
            return results
            
        except Exception as e:
            self.logger.error(f"Country-wide search failed: {e}")
            return []

    def store_asset(self, asset_data: dict) -> bool:
        """Store asset in OneMinuta's geo-sharded storage system"""
        try:
            asset_id = asset_data["meta"]["id"]
            user_id = asset_data["meta"]["owner_user_id"]

            # Store in user's directory
            user_dir = self.users_path / user_id
            user_dir.mkdir(exist_ok=True)

            # Store meta.json
            meta_file = user_dir / f"{asset_id}_meta.json"
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(asset_data["meta"], f, indent=2, ensure_ascii=False, default=str)

            # Store state.json
            state_file = user_dir / f"{asset_id}_state.json"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(asset_data["state"], f, indent=2, ensure_ascii=False, default=str)

            # Store telegram metadata
            telegram_file = user_dir / f"{asset_id}_telegram.json"
            with open(telegram_file, "w", encoding="utf-8") as f:
                json.dump(
                    asset_data["telegram_metadata"],
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            # Also store in geo-sharded structure if location available
            if asset_data["meta"].get("location"):
                self._store_geo_indexed(asset_data)

            # Update global index
            self._update_global_index(asset_data)

            channel = asset_data["telegram_metadata"].get("channel", "unknown")
            self.logger.info(f"Stored asset {asset_id} from {channel}")
            return True

        except Exception as e:
            asset_id = asset_data.get("meta", {}).get("id", "unknown")
            self.logger.error(f"Failed to store asset {asset_id}: {e}")
            return False

    def _store_geo_indexed(self, asset_data: dict):
        """Store asset in proper SpheriCode geo-sharded structure"""
        location = asset_data["meta"].get("location")
        if not location:
            return

        lat = location["lat"]
        lon = location["lon"]
        asset_id = asset_data["meta"]["id"]
        agent_id = asset_data["meta"]["owner_user_id"]
        
        try:
            # Generate SpheriCode for this location
            spheri_code = encode_sphericode(lat, lon, self.bits_per_axis)
            
            # Store asset reference at multiple precision levels for efficient querying
            for prefix_len in self.default_prefix_lengths:
                prefix = spheri_code[:prefix_len]
                
                # Create nested directory structure: geo/TH/spheri/3/g/6/f/b/s/
                country = location.get("country", "TH")
                nested_path = self._create_nested_path(prefix)
                geo_cell_dir = self.geo_path / country / "spheri" / nested_path
                geo_cell_dir.mkdir(parents=True, exist_ok=True)
                
                # Store asset reference (not full data - just pointer)
                asset_ref_file = geo_cell_dir / "properties" / f"{user_id}_{asset_id}.json"
                asset_ref_file.parent.mkdir(exist_ok=True)
                
                asset_ref = {
                    "user_id": user_id,
                    "asset_id": asset_id,
                    "asset_type": asset_data["meta"]["asset_type"],
                    "price": asset_data["state"]["price"]["value"],
                    "currency": asset_data["state"]["price"]["currency"],
                    "rent_or_sale": asset_data["state"]["for_rent_or_sale"],
                    "status": asset_data["state"]["status"],
                    "lat": lat,
                    "lon": lon,
                    "created_at": asset_data["meta"]["created_at"],
                    "spheri_code": spheri_code,
                    "spheri_prefix": prefix
                }
                
                with open(asset_ref_file, "w", encoding="utf-8") as f:
                    json.dump(asset_ref, f, indent=2, ensure_ascii=False, default=str)
                
                # Update cell index
                self._update_geo_cell_index(geo_cell_dir, asset_ref)
                
            # Update the asset's state with calculated SpheriCode
            asset_data["state"]["spheri"] = {
                "code": spheri_code,
                "bits_per_axis": self.bits_per_axis,
                "prefix_len": 8  # Default display length
            }
            
            self.logger.info(f"Geo-indexed asset {asset_id} with SpheriCode {spheri_code[:8]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to geo-index asset {asset_id}: {e}")
    
    def _update_geo_cell_index(self, geo_cell_dir: Path, asset_ref: dict):
        """Update the index.json for a geo cell"""
        index_file = geo_cell_dir / "index.json"
        
        # Load existing index
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            # Extract the original prefix from the nested path
            # geo_cell_dir might be like "storage/geo/TH/spheri/3/g/6/f"
            # We want to reconstruct "3G6F" from "3/g/6/f"
            spheri_parts = geo_cell_dir.parts
            spheri_index = None
            for i, part in enumerate(spheri_parts):
                if part == "spheri":
                    spheri_index = i + 1
                    break
            
            if spheri_index and spheri_index < len(spheri_parts):
                nested_chars = spheri_parts[spheri_index:]
                cell_code = "".join(nested_chars).upper()
            else:
                cell_code = geo_cell_dir.name
            
            index = {
                "cell": cell_code,
                "count": 0,
                "by_status": {},
                "by_asset_type": {},
                "properties": [],
                "children": [],
                "last_indexed": None
            }
        
        # Update counters
        asset_type = asset_ref["asset_type"]
        status = asset_ref["status"]
        property_ref = f"{asset_ref['user_id']}:{asset_ref['asset_id']}"
        
        # Add to properties list if not already there
        if property_ref not in index["properties"]:
            index["properties"].append(property_ref)
            index["count"] = len(index["properties"])
        
        # Update type counters
        index["by_asset_type"][asset_type] = index["by_asset_type"].get(asset_type, 0) + 1
        index["by_status"][status] = index["by_status"].get(status, 0) + 1
        
        # Update timestamp
        index["last_indexed"] = datetime.utcnow().isoformat()
        
        # Write updated index
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False, default=str)

    def _update_global_index(self, asset_data: dict):
        """Update global asset index"""
        global_index_file = self.global_path / "asset_index.json"

        # Load existing index
        if global_index_file.exists():
            with open(global_index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"assets": [], "last_updated": None, "total_count": 0}

        # Add or update asset entry
        asset_id = asset_data["meta"]["id"]
        location = asset_data["meta"].get("location")

        asset_entry = {
            "id": asset_id,
            "user_id": asset_data["meta"]["owner_user_id"],
            "asset_type": asset_data["meta"]["asset_type"],
            "rent_or_sale": asset_data["state"]["for_rent_or_sale"],
            "price": asset_data["state"]["price"]["value"],
            "location_area": location.get("area") if location else None,
            "created_at": asset_data["meta"]["created_at"],
            "source": "telegram",
        }

        # Remove existing entry if it exists
        index["assets"] = [a for a in index["assets"] if a["id"] != asset_id]

        # Add new entry
        index["assets"].append(asset_entry)
        index["last_updated"] = datetime.utcnow().isoformat()
        index["total_count"] = len(index["assets"])

        # Write updated index
        with open(global_index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False, default=str)

    def get_asset_stats(self) -> Dict[str, Any]:
        """Get asset collection statistics"""
        global_index_file = self.global_path / "asset_index.json"

        if not global_index_file.exists():
            return {"total_assets": 0, "by_source": {}, "by_type": {}, "by_user": {}}

        with open(global_index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        stats = {
            "total_assets": index.get("total_count", 0),
            "last_updated": index.get("last_updated"),
            "by_source": {},
            "by_type": {},
            "by_user": {},
            "by_transaction": {},
        }

        # Aggregate statistics
        for asset in index.get("assets", []):
            source = asset.get("source", "unknown")
            asset_type = asset.get("asset_type", "unknown")
            user_id = asset.get("user_id", "unknown")
            transaction = asset.get("rent_or_sale", "unknown")

            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1
            stats["by_user"][user_id] = stats["by_user"].get(user_id, 0) + 1
            stats["by_transaction"][transaction] = stats["by_transaction"].get(transaction, 0) + 1

        return stats

    def search_assets(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search assets with filters"""
        global_index_file = self.global_path / "asset_index.json"

        if not global_index_file.exists():
            return []

        with open(global_index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        results = []
        for asset in index.get("assets", []):
            # Apply filters
            if filters.get("asset_type") and asset.get("asset_type") != filters["asset_type"]:
                continue
            if filters.get("rent_or_sale") and asset.get("rent_or_sale") != filters["rent_or_sale"]:
                continue
            if filters.get("user_id") and asset.get("user_id") != filters["user_id"]:
                continue
            if filters.get("min_price") and (asset.get("price", 0) < filters["min_price"]):
                continue
            if filters.get("max_price") and (
                asset.get("price", float("inf")) > filters["max_price"]
            ):
                continue

            results.append(asset)

        return results
