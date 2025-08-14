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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "geo-spherical"))

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
               min_price: float = None, asset_type: str = None, bedrooms: int = None,
               bathrooms: int = None, limit: int = 20, json_output: bool = False) -> List[Dict]:
        """
        Search for properties by location and filters
        """
        start_time = time.time()
        
        # Generate prefixes for the search area
        prefixes = prefixes_for_query(lat, lon, radius_m)
        
        # Find all properties in those geo cells using nested structure
        candidate_properties = []
        cells_found = 0
        
        for prefix in prefixes:
            # Build nested geo path: geo/TH/spheri/3/g/6/f/b/s/
            nested_chars = list(prefix.lower())
            nested_path = "/".join(nested_chars)
            
            geo_cell_path = self.storage_path / "geo" / "TH" / "spheri" / nested_path
            
            # Search this path and all nested subdirectories for property files
            found_props_in_cell = False
            for properties_dir in geo_cell_path.rglob("properties"):
                if properties_dir.is_dir():
                    found_props_in_cell = True
                    # Read all property reference files
                    for prop_file in properties_dir.glob("*.json"):
                        try:
                            with open(prop_file) as f:
                                prop_ref = json.load(f)
                            candidate_properties.append(prop_ref)
                        except (json.JSONDecodeError, FileNotFoundError):
                            continue
            
            if found_props_in_cell:
                cells_found += 1
        
        # Load property details and apply filters
        results = []
        properties_loaded = 0
        
        for prop_ref in candidate_properties:
            user_id = prop_ref.get("user_id")
            asset_id = prop_ref.get("asset_id")
            
            if not user_id or not asset_id:
                continue
            
            # Load property files from users directory  
            user_dir = self.storage_path / "users" / user_id
            
            if not user_dir.exists():
                continue
                
            try:
                # Load meta and state files
                meta_file = user_dir / f"{asset_id}_meta.json"
                state_file = user_dir / f"{asset_id}_state.json"
                
                if not meta_file.exists() or not state_file.exists():
                    continue
                
                with open(meta_file) as f:
                    meta = json.load(f)
                with open(state_file) as f:
                    state = json.load(f)
                
                properties_loaded += 1
                
                # Check distance filter (already have coords from prop_ref)
                prop_lat = prop_ref["lat"]
                prop_lon = prop_ref["lon"]
                distance = surface_distance(lat, lon, prop_lat, prop_lon)
                
                if distance > radius_m:
                    continue
                
                # Apply filters
                if rent and prop_ref.get("rent_or_sale", "").lower() != "rent":
                    continue
                if sale and prop_ref.get("rent_or_sale", "").lower() != "sale":
                    continue
                
                if asset_type and prop_ref.get("asset_type") != asset_type.upper():
                    continue
                
                price_value = prop_ref.get("price", 0)
                if min_price and price_value < min_price:
                    continue
                if max_price and price_value > max_price:
                    continue
                
                # Only show available properties
                if prop_ref.get("status", "").lower() != "available":
                    continue
                
                # Apply bedroom filter
                if bedrooms and state.get("bedrooms") != bedrooms:
                    continue
                    
                # Apply bathroom filter
                if bathrooms and state.get("bathrooms") != bathrooms:
                    continue
                
                # Build result from available data
                result = {
                    "id": f"{user_id}:{asset_id}",
                    "distance_m": round(distance),
                    "location": {
                        "lat": prop_lat,
                        "lon": prop_lon,
                        "area": meta["location"]["area"],
                        "city": meta["location"]["city"]
                    },
                    "price": {
                        "value": price_value,
                        "currency": prop_ref.get("currency", "THB")
                    },
                    "type": prop_ref.get("asset_type", "").lower(),
                    "for_rent_or_sale": prop_ref.get("rent_or_sale", "").lower(),
                    "bedrooms": state.get("bedrooms"),
                    "bathrooms": state.get("bathrooms"),
                    "area_sqm": state.get("area_sqm"),
                    "furnished": state.get("furnished"),
                    "last_updated": prop_ref.get("created_at"),
                    "description": ""  # Could load telegram metadata for description
                }
                
                results.append(result)
                
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                print(f"Warning: Could not load property {user_id}:{asset_id}: {e}", file=sys.stderr)
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
        
        # Read from global index if available
        global_index_file = self.storage_path / "global" / "asset_index.json"
        if global_index_file.exists():
            try:
                with open(global_index_file) as f:
                    global_index = json.load(f)
                
                stats["total_properties"] = global_index.get("total_count", 0)
                stats["last_updated"] = global_index.get("last_updated")
                
                # Aggregate by area, type, status from global index
                by_area = {}
                by_type = {}
                by_status = {}
                by_user = {}
                
                for asset in global_index.get("assets", []):
                    area = asset.get("location_area", "unknown")
                    asset_type = asset.get("asset_type", "unknown")
                    user_id = asset.get("user_id", "unknown")
                    
                    by_area[area] = by_area.get(area, 0) + 1
                    by_type[asset_type] = by_type.get(asset_type, 0) + 1
                    by_user[user_id] = by_user.get(user_id, 0) + 1
                    
                stats.update({
                    "by_area": by_area,
                    "by_type": by_type,
                    "by_user": by_user
                })
                
            except (json.JSONDecodeError, FileNotFoundError):
                # Fallback to manual counting
                stats = self._count_properties_manually()
        else:
            # Manual counting if no global index
            stats = self._count_properties_manually()
        
        # Count geo indexes
        geo_dir = self.storage_path / "geo"
        geo_indexes = 0
        if geo_dir.exists():
            for index_file in geo_dir.glob("**/index.json"):
                geo_indexes += 1
        
        stats["geo_indexes"] = geo_indexes
        stats["storage_path"] = str(self.storage_path)
        
        if json_output:
            return stats
        else:
            self._print_stats(stats)
            return stats
    
    def _count_properties_manually(self) -> Dict:
        """Manually count properties from agents directory"""
        total_properties = 0
        by_area = {}
        by_type = {}
        by_user = {}
        
        agents_dir = self.storage_path / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                
                user_id = agent_dir.name
                user_props = 0
                
                # Count meta files for this agent
                for meta_file in agent_dir.glob("*_meta.json"):
                    try:
                        with open(meta_file) as f:
                            meta = json.load(f)
                        
                        total_properties += 1
                        user_props += 1
                        
                        area = meta.get("location", {}).get("area", "unknown")
                        by_area[area] = by_area.get(area, 0) + 1
                        
                        asset_type = meta.get("asset_type", "unknown")
                        by_type[asset_type] = by_type.get(asset_type, 0) + 1
                        
                    except (json.JSONDecodeError, KeyError, FileNotFoundError):
                        continue
                
                if user_props > 0:
                    by_user[user_id] = user_props
        
        return {
            "total_properties": total_properties,
            "by_area": by_area,
            "by_type": by_type,
            "by_user": by_user
        }
    
    def watch(self, verbose: bool = False, log_file: str = None) -> None:
        """Watch storage directory for changes and auto-reindex"""
        import time
        import os
        from pathlib import Path
        
        print("Starting OneMinuta file watcher...")
        print(f"Monitoring: {self.storage_path}")
        
        if log_file:
            print(f"Logging to: {log_file}")
        
        if verbose:
            print("Verbose mode enabled")
        
        # Simple file watching implementation
        # In production, this would use inotify/FSEvents for better performance
        
        last_modified = {}
        
        def scan_for_changes():
            changes = []
            
            # Check for changes in users directory
            users_dir = self.storage_path / "users"
            if users_dir.exists():
                for file_path in users_dir.rglob("*.json"):
                    try:
                        mtime = os.path.getmtime(file_path)
                        if file_path not in last_modified or last_modified[file_path] != mtime:
                            last_modified[file_path] = mtime
                            changes.append(str(file_path))
                    except (OSError, FileNotFoundError):
                        continue
            
            return changes
        
        print("File watcher started. Press Ctrl+C to stop.")
        
        try:
            # Initial scan
            scan_for_changes()
            
            while True:
                changes = scan_for_changes()
                
                if changes:
                    if verbose:
                        print(f"Detected {len(changes)} file changes:")
                        for change in changes:
                            print(f"  - {change}")
                    
                    print("Auto-reindexing...")
                    reindex_result = self.reindex(verbose=verbose)
                    
                    if log_file:
                        with open(log_file, "a") as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Reindexed {reindex_result['assets_processed']} assets\n")
                    
                    if not reindex_result["errors"]:
                        print("✅ Auto-reindex completed successfully")
                    else:
                        print(f"⚠️ Auto-reindex completed with {len(reindex_result['errors'])} errors")
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n🛑 File watcher stopped")
            return

    def reindex(self, cell: str = None, verbose: bool = False) -> Dict:
        """Rebuild indexes from current storage"""
        print("Rebuilding OneMinuta indexes...")
        start_time = time.time()
        
        results = {
            "assets_processed": 0,
            "geo_cells_created": 0,
            "errors": [],
            "duration_ms": 0
        }
        
        if cell:
            print(f"Reindexing specific cell: {cell}")
            # TODO: Implement specific cell reindexing
            results["errors"].append("Specific cell reindexing not implemented yet")
        else:
            # Full reindex
            print("Performing full reindex...")
            
            # Import asset manager to use existing reindexing logic
            sys.path.insert(0, str(Path(__file__).parent))
            from services.collector.asset_manager import AssetManager
            
            try:
                asset_manager = AssetManager(str(self.storage_path))
                
                # Get current asset statistics
                current_stats = asset_manager.get_asset_stats()
                results["assets_processed"] = current_stats.get("total_assets", 0)
                
                print(f"Found {results['assets_processed']} assets in storage")
                
                # Count geo indexes created
                geo_dir = self.storage_path / "geo"
                if geo_dir.exists():
                    results["geo_cells_created"] = len(list(geo_dir.glob("**/index.json")))
                
                print(f"Geo-spatial indexes: {results['geo_cells_created']} cells")
                
            except Exception as e:
                error_msg = f"Reindex failed: {e}"
                results["errors"].append(error_msg)
                print(f"Error: {error_msg}")
        
        results["duration_ms"] = round((time.time() - start_time) * 1000, 1)
        
        if results["errors"]:
            print(f"Reindex completed with {len(results['errors'])} errors in {results['duration_ms']}ms")
            for error in results["errors"]:
                print(f"  Error: {error}")
        else:
            print(f"Reindex completed successfully in {results['duration_ms']}ms")
            print(f"  Assets processed: {results['assets_processed']}")
            print(f"  Geo cells: {results['geo_cells_created']}")
        
        return results
    
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
        
        if stats.get('by_type'):
            print("Properties by Type:")
            for ptype, count in sorted(stats['by_type'].items()):
                print(f"  {ptype}: {count}")
            print()
        
        if stats.get('by_status'):
            print("Properties by Status:")
            for status, count in sorted(stats['by_status'].items()):
                print(f"  {status}: {count}")
    
    async def chatbot_interactive(self, openai_api_key: str):
        """Start interactive chatbot session"""
        try:
            from services.chatbot.chatbot_manager import OneMinutaChatbotManager
            
            print("🤖 OneMinuta Smart Chatbot")
            print("=" * 40)
            print("Type 'quit' to exit, 'reset' to restart")
            print()
            
            chatbot = OneMinutaChatbotManager(str(self.storage_path), openai_api_key)
            
            user_id = input("Enter user ID (default: 'user'): ").strip() or "user"
            print(f"Chat started with: {user_id}")
            print("-" * 30)
            
            while True:
                user_input = input(f"\n{user_id}: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'reset':
                    await chatbot.reset_conversation(user_id)
                    print("🔄 Conversation reset")
                    continue
                
                print("🤖: ", end="", flush=True)
                response = await chatbot.process_message(user_id, user_input)
                print(response['reply'])
                
                if response.get('session_complete'):
                    print("\n✅ Conversation completed!")
                    break
                    
        except ImportError:
            print("❌ Chatbot not available. Install dependencies: pip install openai")
        except Exception as e:
            print(f"❌ Chatbot error: {e}")
    
    async def chatbot_stats(self):
        """Show chatbot session statistics"""
        try:
            from services.chatbot.session_manager import ChatbotSessionManager
            
            session_manager = ChatbotSessionManager(str(self.storage_path))
            stats = await session_manager.get_session_stats()
            
            print("🤖 Chatbot Session Statistics")
            print("=" * 40)
            
            if not stats:
                print("No chatbot sessions found")
                return
            
            print(f"Total Sessions: {stats['total_sessions']}")
            print(f"Total Messages: {stats['total_messages']}")
            print(f"Average Messages/Session: {stats['avg_messages']}")
            print()
            
            if stats['by_stage']:
                print("Sessions by Stage:")
                for stage, count in stats['by_stage'].items():
                    print(f"  {stage}: {count}")
                print()
                
            if stats['by_status']:
                print("Sessions by Status:")
                for status, count in stats['by_status'].items():
                    print(f"  {status}: {count}")
                    
        except ImportError:
            print("❌ Chatbot not available")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="OneMinuta Property Search CLI")
    parser.add_argument("--storage", default="./storage", help="Storage directory path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for properties")
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument("--lat", type=float, help="Latitude (requires --lon)")
    search_group.add_argument("--area", help="Area name (e.g., 'Rawai', 'Phuket')")
    search_parser.add_argument("--lon", type=float, help="Longitude (required with --lat)")
    search_parser.add_argument("--radius", type=float, default=5000, help="Search radius in meters")
    search_parser.add_argument("--rent", action="store_true", help="Only rental properties")
    search_parser.add_argument("--sale", action="store_true", help="Only sale properties")
    search_parser.add_argument("--min-price", type=float, help="Minimum price")
    search_parser.add_argument("--max-price", type=float, help="Maximum price")
    search_parser.add_argument("--bedrooms", type=int, help="Number of bedrooms")
    search_parser.add_argument("--bathrooms", type=int, help="Number of bathrooms")
    search_parser.add_argument("--type", help="Asset type (condo, villa, house, etc.)")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show property details")
    show_parser.add_argument("id", help="Property ID (user_id:prop_id)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show storage statistics")
    
    # Reindex command
    reindex_parser = subparsers.add_parser("reindex", help="Rebuild storage indexes")
    reindex_parser.add_argument("--cell", help="Reindex specific geo cell")
    reindex_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch storage for changes and auto-reindex")
    watch_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    watch_parser.add_argument("--log-file", help="Log file path for watch events")
    
    # Chatbot commands
    chat_parser = subparsers.add_parser("chat", help="Start interactive chatbot session")
    chat_parser.add_argument("--openai-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    
    chatbot_stats_parser = subparsers.add_parser("chat-stats", help="Show chatbot session statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        cli = OneMinutaCLI(args.storage)
        
        if args.command == "search":
            # Handle area-based search vs lat/lon search
            if args.area:
                # Convert area to lat/lon using area mapping
                area_mapping = {
                    "rawai": (7.77965, 98.32532),
                    "kata": (7.8167, 98.3500),
                    "patong": (7.8980, 98.2940),
                    "phuket": (7.8804, 98.3923),
                    "bangkok": (13.7563, 100.5018),
                }
                area_key = args.area.lower()
                if area_key in area_mapping:
                    lat, lon = area_mapping[area_key]
                else:
                    print(f"Unknown area '{args.area}'. Available areas: {', '.join(area_mapping.keys())}")
                    return
            else:
                # Validate lat/lon requirements
                if args.lat is None or args.lon is None:
                    print("Error: --lat and --lon are both required for coordinate search")
                    return
                lat, lon = args.lat, args.lon
            
            cli.search(
                lat=lat,
                lon=lon,
                radius_m=args.radius,
                rent=args.rent,
                sale=args.sale,
                min_price=args.min_price,
                max_price=args.max_price,
                asset_type=args.type,
                bedrooms=args.bedrooms,
                bathrooms=args.bathrooms,
                limit=args.limit,
                json_output=args.json
            )
        
        elif args.command == "show":
            cli.show(args.id, json_output=args.json)
        
        elif args.command == "stats":
            cli.stats(json_output=args.json)
        
        elif args.command == "reindex":
            cli.reindex(cell=args.cell, verbose=args.verbose)
        
        elif args.command == "watch":
            cli.watch(verbose=args.verbose, log_file=getattr(args, 'log_file', None))
        
        elif args.command == "chat":
            import os
            import asyncio
            
            # Load from .env or command line argument
            openai_key = getattr(args, 'openai_key', None) or os.getenv('OPENAI_API_KEY')
            if not openai_key:
                print("❌ Error: OpenAI API key required. Add to .env file or use --openai-key")
                print("Add to .env: OPENAI_API_KEY=your_key_here")
                return
            
            asyncio.run(cli.chatbot_interactive(openai_key))
        
        elif args.command == "chat-stats":
            import asyncio
            asyncio.run(cli.chatbot_stats())
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()