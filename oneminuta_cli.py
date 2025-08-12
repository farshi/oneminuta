#!/usr/bin/env python3
"""
OneMinuta CLI - Basic implementation for testing
"""

import json
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "coord-spherical"))

from spherical import surface_distance, inside_cap
from sphericode import encode_sphericode, prefixes_for_query


class OneMinutaCLI:
    """OneMinuta CLI for property search"""
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Storage path {storage_path} does not exist")
    
    def search(self, lat: float, lon: float, radius_m: float = 5000,
               rent: bool = None, sale: bool = None, max_price: float = None,
               min_price: float = None, asset_type: str = None, 
               limit: int = 20, json_output: bool = False) -> List[Dict]:
        """
        Search for properties by location and filters
        """
        start_time = time.time()
        
        # Generate prefixes for the search area
        prefixes = prefixes_for_query(lat, lon, radius_m)
        
        # Find all properties in those geo cells
        candidate_properties = []
        cells_found = 0
        
        for prefix in prefixes:
            # Build geo path: geo/TH/spheri/37/DT/TR/...
            path_parts = ["geo", "TH", "spheri"]
            for i in range(0, len(prefix), 2):
                path_parts.append(prefix[i:i+2])
            
            index_path = self.storage_path / "/".join(path_parts) / "index.json"
            
            if index_path.exists():
                cells_found += 1
                with open(index_path) as f:
                    index_data = json.load(f)
                
                # Add all properties from this cell
                for prop_ref in index_data.get("properties", []):
                    candidate_properties.append(prop_ref)
        
        # Load property details and apply filters
        results = []
        properties_loaded = 0
        
        for prop_ref in candidate_properties:
            user_id, prop_id = prop_ref.split(":", 1)
            
            # Load property files
            prop_dir = self.storage_path / "users" / user_id / "assets" / "property" / prop_id
            
            if not prop_dir.exists():
                continue
                
            try:
                # Load meta and state
                with open(prop_dir / "meta.json") as f:
                    meta = json.load(f)
                with open(prop_dir / "state.json") as f:
                    state = json.load(f)
                
                properties_loaded += 1
                
                # Check distance filter
                prop_lat = meta["location"]["lat"]
                prop_lon = meta["location"]["lon"]
                distance = surface_distance(lat, lon, prop_lat, prop_lon)
                
                if distance > radius_m:
                    continue
                
                # Apply filters
                if rent and state["for_rent_or_sale"] != "rent":
                    continue
                if sale and state["for_rent_or_sale"] != "sale":
                    continue
                
                if asset_type and meta["asset_type"] != asset_type:
                    continue
                
                price_value = state["price"]["value"]
                if min_price and price_value < min_price:
                    continue
                if max_price and price_value > max_price:
                    continue
                
                # Only show available properties
                if state["status"] != "available":
                    continue
                
                # Load description
                description = ""
                desc_path = prop_dir / "description.txt"
                if desc_path.exists():
                    with open(desc_path) as f:
                        description = f.read().strip()
                
                # Build result
                result = {
                    "id": prop_ref,
                    "distance_m": round(distance),
                    "location": {
                        "lat": prop_lat,
                        "lon": prop_lon,
                        "area": meta["location"]["area"],
                        "city": meta["location"]["city"]
                    },
                    "price": state["price"],
                    "type": meta["asset_type"],
                    "for_rent_or_sale": state["for_rent_or_sale"],
                    "bedrooms": state.get("bedrooms"),
                    "bathrooms": state.get("bathrooms"),
                    "area_sqm": state.get("area_sqm"),
                    "furnished": state.get("furnished"),
                    "description": description,
                    "last_updated": state["last_updated"]
                }
                
                results.append(result)
                
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                print(f"Warning: Could not load property {prop_ref}: {e}", file=sys.stderr)
                continue
        
        # Sort by distance
        results.sort(key=lambda x: x["distance_m"])
        
        # Apply limit
        if limit:
            results = results[:limit]
        
        query_time = time.time() - start_time
        
        # Add query metadata
        query_info = {
            "query_time_ms": round(query_time * 1000, 1),
            "prefixes_generated": len(prefixes),
            "cells_found": cells_found,
            "candidates_found": len(candidate_properties),
            "properties_loaded": properties_loaded,
            "results_returned": len(results),
            "search_center": {"lat": lat, "lon": lon},
            "search_radius_m": radius_m
        }
        
        if json_output:
            return {
                "results": results,
                "query": query_info
            }
        else:
            self._print_search_results(results, query_info)
            return results
    
    def show(self, property_id: str, json_output: bool = False) -> Dict:
        """Show details for a specific property"""
        try:
            user_id, prop_id = property_id.split(":", 1)
        except ValueError:
            raise ValueError("Property ID must be in format 'user_id:prop_id'")
        
        prop_dir = self.storage_path / "users" / user_id / "assets" / "property" / prop_id
        
        if not prop_dir.exists():
            raise FileNotFoundError(f"Property {property_id} not found")
        
        # Load all files
        with open(prop_dir / "meta.json") as f:
            meta = json.load(f)
        with open(prop_dir / "state.json") as f:
            state = json.load(f)
        
        # Load description
        description = ""
        desc_path = prop_dir / "description.txt"
        if desc_path.exists():
            with open(desc_path) as f:
                description = f.read().strip()
        
        # Load events
        events = []
        events_path = prop_dir / "events.ndjson"
        if events_path.exists():
            with open(events_path) as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        
        result = {
            "id": property_id,
            "meta": meta,
            "state": state,
            "description": description,
            "events": events,
            "files": {
                "meta_path": str(prop_dir / "meta.json"),
                "state_path": str(prop_dir / "state.json"),
                "description_path": str(desc_path),
                "events_path": str(events_path)
            }
        }
        
        if json_output:
            return result
        else:
            self._print_property_details(result)
            return result
    
    def stats(self, json_output: bool = False) -> Dict:
        """Show storage statistics"""
        stats = {}
        
        # Count users
        users_dir = self.storage_path / "users"
        if users_dir.exists():
            stats["total_users"] = len(list(users_dir.iterdir()))
        
        # Count properties
        total_properties = 0
        by_area = {}
        by_type = {}
        by_status = {}
        
        if users_dir.exists():
            for user_dir in users_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                
                props_dir = user_dir / "assets" / "property"
                if props_dir.exists():
                    for prop_dir in props_dir.iterdir():
                        if not prop_dir.is_dir():
                            continue
                        
                        try:
                            with open(prop_dir / "meta.json") as f:
                                meta = json.load(f)
                            with open(prop_dir / "state.json") as f:
                                state = json.load(f)
                            
                            total_properties += 1
                            
                            area = meta["location"]["area"]
                            by_area[area] = by_area.get(area, 0) + 1
                            
                            asset_type = meta["asset_type"]
                            by_type[asset_type] = by_type.get(asset_type, 0) + 1
                            
                            status = state["status"]
                            by_status[status] = by_status.get(status, 0) + 1
                            
                        except (json.JSONDecodeError, KeyError, FileNotFoundError):
                            continue
        
        # Count geo indexes
        geo_dir = self.storage_path / "geo"
        geo_indexes = 0
        if geo_dir.exists():
            for index_file in geo_dir.glob("**/index.json"):
                geo_indexes += 1
        
        stats.update({
            "total_properties": total_properties,
            "by_area": by_area,
            "by_type": by_type,
            "by_status": by_status,
            "geo_indexes": geo_indexes,
            "storage_path": str(self.storage_path)
        })
        
        if json_output:
            return stats
        else:
            self._print_stats(stats)
            return stats
    
    def _print_search_results(self, results: List[Dict], query_info: Dict):
        """Print search results in human-readable format"""
        print(f"Found {len(results)} properties within {query_info['search_radius_m']/1000:.1f}km:")
        print(f"Query took {query_info['query_time_ms']}ms")
        print()
        
        if not results:
            print("No properties found matching your criteria.")
            return
        
        for i, prop in enumerate(results, 1):
            print(f"{i}. {prop['type'].title()} in {prop['location']['area']} ({prop['distance_m']}m away)")
            
            if prop['for_rent_or_sale'] == 'rent':
                period = prop['price'].get('period', 'month')
                print(f"   Rent: {prop['price']['value']:,} {prop['price']['currency']}/{period}")
            else:
                print(f"   Sale: {prop['price']['value']:,} {prop['price']['currency']}")
            
            details = []
            if prop['bedrooms']:
                details.append(f"{prop['bedrooms']} bed")
            if prop['bathrooms']:
                details.append(f"{prop['bathrooms']} bath")
            if prop['area_sqm']:
                details.append(f"{prop['area_sqm']} sqm")
            if prop['furnished']:
                details.append("furnished")
            
            if details:
                print(f"   {', '.join(details)}")
            
            print(f"   ID: {prop['id']}")
            print()
    
    def _print_property_details(self, prop: Dict):
        """Print detailed property information"""
        meta = prop["meta"]
        state = prop["state"]
        
        print(f"Property: {prop['id']}")
        print(f"Type: {meta['asset_type'].title()}")
        print(f"Location: {meta['location']['area']}, {meta['location']['city']}")
        print(f"Coordinates: {meta['location']['lat']:.5f}, {meta['location']['lon']:.5f}")
        print(f"SpheriCode: {state['spheri']['code']}")
        print()
        
        if state['for_rent_or_sale'] == 'rent':
            period = state['price'].get('period', 'month')
            print(f"For Rent: {state['price']['value']:,} {state['price']['currency']}/{period}")
        else:
            print(f"For Sale: {state['price']['value']:,} {state['price']['currency']}")
        
        print(f"Status: {state['status'].title()}")
        print(f"Last Updated: {state['last_updated']}")
        print()
        
        if state.get('bedrooms'):
            print(f"Bedrooms: {state['bedrooms']}")
        if state.get('bathrooms'):
            print(f"Bathrooms: {state['bathrooms']}")
        if state.get('area_sqm'):
            print(f"Area: {state['area_sqm']} sqm")
        if state.get('furnished') is not None:
            print(f"Furnished: {'Yes' if state['furnished'] else 'No'}")
        
        if prop["description"]:
            print(f"\nDescription:\n{prop['description']}")
        
        if prop["events"]:
            print(f"\nEvent History ({len(prop['events'])} events):")
            for event in prop["events"][-3:]:  # Show last 3 events
                print(f"  {event['ts']}: {event['type']} by {event.get('actor', 'unknown')}")
    
    def _print_stats(self, stats: Dict):
        """Print storage statistics"""
        print(f"OneMinuta Storage Statistics")
        print(f"Storage Path: {stats['storage_path']}")
        print()
        
        print(f"Total Users: {stats.get('total_users', 0)}")
        print(f"Total Properties: {stats['total_properties']}")
        print(f"Geo Indexes: {stats['geo_indexes']}")
        print()
        
        if stats['by_area']:
            print("Properties by Area:")
            for area, count in sorted(stats['by_area'].items()):
                print(f"  {area}: {count}")
            print()
        
        if stats['by_type']:
            print("Properties by Type:")
            for ptype, count in sorted(stats['by_type'].items()):
                print(f"  {ptype}: {count}")
            print()
        
        if stats['by_status']:
            print("Properties by Status:")
            for status, count in sorted(stats['by_status'].items()):
                print(f"  {status}: {count}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="OneMinuta Property Search CLI")
    parser.add_argument("--storage", default="./storage", help="Storage directory path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for properties")
    search_parser.add_argument("--lat", type=float, required=True, help="Latitude")
    search_parser.add_argument("--lon", type=float, required=True, help="Longitude")
    search_parser.add_argument("--radius", type=float, default=5000, help="Search radius in meters")
    search_parser.add_argument("--rent", action="store_true", help="Only rental properties")
    search_parser.add_argument("--sale", action="store_true", help="Only sale properties")
    search_parser.add_argument("--min-price", type=float, help="Minimum price")
    search_parser.add_argument("--max-price", type=float, help="Maximum price")
    search_parser.add_argument("--type", help="Asset type (condo, villa, house, etc.)")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show property details")
    show_parser.add_argument("id", help="Property ID (user_id:prop_id)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show storage statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        cli = OneMinutaCLI(args.storage)
        
        if args.command == "search":
            cli.search(
                lat=args.lat,
                lon=args.lon,
                radius_m=args.radius,
                rent=args.rent,
                sale=args.sale,
                min_price=args.min_price,
                max_price=args.max_price,
                asset_type=args.type,
                limit=args.limit,
                json_output=args.json
            )
        
        elif args.command == "show":
            cli.show(args.id, json_output=args.json)
        
        elif args.command == "stats":
            cli.stats(json_output=args.json)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()