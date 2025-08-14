#!/usr/bin/env python3
"""
OneMinuta CLI - Basic implementation for testing
"""

import json
import sys
import os
import time
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "geo-spherical"))

from spherical import surface_distance, inside_cap
from sphericode import encode_sphericode, prefixes_for_query

# Import analytics and Telegram components
from services.analytics.channel_analytics import ChannelAnalytics, GrowthPeriod
from services.analytics.client_analyzer import PropertyClientAnalyzer
from services.collector.asset_manager import AssetManager


class OneMinutaCLI:
    """OneMinuta CLI for property search"""
    
    def __init__(self, storage_path: str = "./storage"):
        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Storage path {storage_path} does not exist")
        
        # Initialize analytics components
        self.analytics = ChannelAnalytics(storage_path)
        self.client_analyzer = PropertyClientAnalyzer(storage_path)
        self.asset_manager = AssetManager(storage_path)
    
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
    
    async def list_partners(self, json_output: bool = False) -> Dict:
        """List all configured partners and their channels"""
        try:
            partners_data = {
                "total_partners": len(self.asset_manager.partners),
                "partners": [],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            for partner_id, partner_info in self.asset_manager.partners.items():
                partner_summary = {
                    "partner_id": partner_id,
                    "name": partner_info["name"],
                    "channels": partner_info["channels"],
                    "channel_count": len(partner_info["channels"]),
                    "contact": partner_info["contact"],
                    "commission_rate": partner_info["commission_rate"],
                    "active": partner_info["active"],
                    "languages": partner_info["languages"],
                    "joined": partner_info["joined"]
                }
                partners_data["partners"].append(partner_summary)
            
            if json_output:
                return partners_data
            else:
                self._print_partners_list(partners_data)
                return partners_data
                
        except Exception as e:
            print(f"Error listing partners: {e}")
            return {}
    
    def _print_partners_list(self, data: Dict):
        """Pretty print partners list"""
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
        print("🤝 ONEMINUTA PARTNER DIRECTORY")
        print("="*60)
        
        print(f"\n📈 Summary")
        print(f"  Total Partners: {data.get('total_partners', 0)}")
        print(f"  Generated: {data.get('generated_at', 'N/A')[:19]}")
        
        partners = data.get("partners", [])
        if partners:
            print(f"\n📁 Partner Details")
            print("-" * 80)
            print(f"{'Name':<25} {'Channels':<8} {'Rate':<8} {'Contact':<15} {'Status':<10}")
            print("-" * 80)
            
            for partner in partners:
                name = partner.get('name', 'Unknown')[:24]
                channels = partner.get('channel_count', 0)
                rate = f"{partner.get('commission_rate', 0)*100:.1f}%"
                contact = partner.get('contact', 'N/A')[:14]
                status = "✅ Active" if partner.get('active') else "❌ Inactive"
                
                print(f"{name:<25} {channels:<8} {rate:<8} {contact:<15} {status:<10}")
                
                # Show channels for each partner
                partner_channels = partner.get('channels', [])
                if partner_channels:
                    channels_str = ", ".join(partner_channels)
                    print(f"  📢 Channels: {channels_str}")
                    print()
        
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
    
    async def channel_analytics(self, channel_id: str = None, partner_id: str = None, 
                                period: str = "weekly", json_output: bool = False) -> Dict:
        """
        Display channel analytics with growth metrics - supports partner view
        
        Args:
            channel_id: Specific channel ID or 'all' for all channels
            partner_id: Show analytics for specific partner's channels
            period: 'daily', 'weekly', or 'monthly'
            json_output: Return raw JSON data
        """
        try:
            # Map period string to enum
            period_map = {
                "daily": GrowthPeriod.DAILY,
                "weekly": GrowthPeriod.WEEKLY,
                "monthly": GrowthPeriod.MONTHLY
            }
            growth_period = period_map.get(period.lower(), GrowthPeriod.WEEKLY)
            
            if channel_id and channel_id != "all":
                # Get metrics for specific channel
                metrics = await self.analytics.get_channel_metrics(channel_id)
                report = await self.analytics.generate_growth_report(channel_id, growth_period)
                
                if json_output:
                    return report
                else:
                    self._print_channel_analytics(report)
                    return report
            else:
                # Get channels - either for specific partner or all channels
                if partner_id:
                    # Get channels for specific partner
                    partner_channels = self.asset_manager.get_partner_channels(partner_id)
                    if not partner_channels:
                        print(f"No channels found for partner {partner_id}")
                        return {}
                    
                    # Convert channel names to IDs (remove @ prefix, add - prefix for storage)
                    channel_ids = []
                    for channel in partner_channels:
                        # This is a simplified conversion - in practice you'd need proper channel ID mapping
                        if channel.startswith("@"):
                            # Mock conversion for demo - in practice, use actual Telegram channel IDs
                            mock_id = f"-100{hash(channel) % 1000000000}"
                            channel_ids.append(mock_id)
                    
                    # Generate partner-specific dashboard
                    partner_data = self.asset_manager.partners.get(partner_id, {})
                    dashboard = await self.analytics.get_partner_dashboard(
                        channel_ids, partner_data.get("name", partner_id)
                    )
                
                else:
                    # Get all channels from analytics directory
                    analytics_dir = self.storage_path / "analytics" / "channels"
                    channel_ids = []
                    
                    if analytics_dir.exists():
                        for channel_dir in analytics_dir.iterdir():
                            if channel_dir.is_dir() and channel_dir.name.startswith("-"):
                                channel_ids.append(channel_dir.name)
                    
                    if not channel_ids:
                        print("No channels found in analytics. Add bot to channels to start tracking.")
                        return {}
                    
                    # Generate multi-channel dashboard
                    dashboard = await self.analytics.get_multi_channel_dashboard(channel_ids)
                
                if json_output:
                    return dashboard
                else:
                    self._print_multi_channel_dashboard(dashboard)
                    return dashboard
                    
        except Exception as e:
            print(f"Error getting channel analytics: {e}")
            return {}
    
    async def official_channel_analytics(self, json_output: bool = False) -> Dict:
        """Display OneMinuta official channel analytics only"""
        try:
            # Get official channel dashboard
            dashboard = await self.analytics.get_official_channel_dashboard()
            
            if json_output:
                return dashboard
            else:
                self._print_multi_channel_dashboard(dashboard)
                return dashboard
                
        except Exception as e:
            print(f"Error getting official channel analytics: {e}")
            return {}
    
    async def hot_clients(self, min_score: float = 61.0, limit: int = 20, 
                         json_output: bool = False) -> List[Dict]:
        """
        Display hot property clients with scores
        
        Args:
            min_score: Minimum hotness score (0-100)
            limit: Number of clients to show
            json_output: Return raw JSON data
        """
        try:
            hot_clients = await self.client_analyzer.get_hot_clients(min_score, limit)
            
            if json_output:
                return [self._client_to_dict(c) for c in hot_clients]
            else:
                self._print_hot_clients(hot_clients)
                return hot_clients
                
        except Exception as e:
            print(f"Error getting hot clients: {e}")
            return []
    
    async def client_report(self, json_output: bool = False) -> Dict:
        """Generate comprehensive client analytics report"""
        try:
            report = await self.client_analyzer.generate_daily_report()
            
            if json_output:
                return report
            else:
                self._print_client_report(report)
                return report
                
        except Exception as e:
            print(f"Error generating client report: {e}")
            return {}
    
    def _print_channel_analytics(self, report: Dict):
        """Pretty print channel analytics"""
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
        print(f"📊 CHANNEL ANALYTICS - {report.get('channel_name', 'Unknown')}")
        print("="*60)
        
        summary = report.get("summary", {})
        print(f"\n📈 Summary ({report.get('period', 'Period')})")
        print(f"  Total Members: {summary.get('total_members', 0):,}")
        print(f"  Net Growth: {summary.get('net_growth', 0):+,}")
        print(f"  Growth Rate: {summary.get('growth_rate', 'N/A')}")
        print(f"  Health Score: {summary.get('health_score', 'N/A')}")
        
        growth = report.get("growth_metrics", {})
        new_members = growth.get("new_members", {})
        lost_members = growth.get("lost_members", {})
        
        print(f"\n👥 Member Activity")
        print(f"  New Today: {new_members.get('today', 0)}")
        print(f"  New This Week: {new_members.get('this_week', 0)}")
        print(f"  New This Month: {new_members.get('this_month', 0)}")
        print(f"  Left Today: {lost_members.get('today', 0)}")
        print(f"  Left This Week: {lost_members.get('this_week', 0)}")
        
        engagement = report.get("engagement_metrics", {})
        print(f"\n⚡ Engagement")
        print(f"  Active Members: {engagement.get('active_members', 0)}")
        print(f"  Messages Today: {engagement.get('messages_today', 0)}")
        print(f"  Bot Interactions: {engagement.get('bot_interactions', 0)}")
        
        leads = report.get("lead_generation", {})
        print(f"\n🔥 Lead Generation")
        print(f"  Hot Leads: {leads.get('hot_leads', 0)}")
        print(f"  Warm Leads: {leads.get('warm_leads', 0)}")
        print(f"  Estimated Value: {leads.get('estimated_value', '$0')}")
        
        peak = report.get("peak_activity", {})
        print(f"\n⏰ Peak Activity")
        print(f"  Best Join Hour: {peak.get('peak_join_hour', 'N/A')}")
        print(f"  Best Join Day: {peak.get('peak_join_day', 'N/A')}")
        
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations")
            for rec in recommendations[:3]:
                print(f"  • {rec}")
        
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
    
    def _print_multi_channel_dashboard(self, dashboard: Dict):
        """Pretty print multi-channel dashboard"""
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
        print("📊 MULTI-CHANNEL ANALYTICS DASHBOARD")
        print("="*60)
        
        agg = dashboard.get("aggregate_metrics", {})
        print(f"\n📈 Overall Statistics")
        print(f"  Total Channels: {dashboard.get('total_channels', 0)}")
        print(f"  Total Members: {agg.get('total_members_all', 0):,}")
        print(f"  New Today: {agg.get('total_new_today', 0):,}")
        print(f"  New This Week: {agg.get('total_new_week', 0):,}")
        print(f"  Avg Growth Rate: {agg.get('avg_growth_rate', 'N/A')}")
        print(f"  Total Hot Leads: {agg.get('total_hot_leads', 0)}")
        print(f"  Est. Total Value: ${agg.get('total_estimated_value', 0):,.2f}")
        
        channels = dashboard.get("channels", [])
        if channels:
            print(f"\n📱 Channel Performance")
            print("-" * 60)
            print(f"{'Channel':<25} {'Members':<10} {'New':<8} {'Growth':<10} {'Status':<15}")
            print("-" * 60)
            
            for ch in channels:
                name = ch.get('channel_name', 'Unknown')[:24]
                members = ch.get('members', 0)
                new_today = ch.get('new_today', 0)
                growth = ch.get('growth_rate_display', 'N/A')
                status = ch.get('status', 'Unknown')
                
                print(f"{name:<25} {members:<10,} {new_today:<8} {growth:<10} {status:<15}")
        
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
    
    def _print_hot_clients(self, clients):
        """Pretty print hot clients list"""
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
        print("🔥 HOT PROPERTY CLIENTS")
        print("="*60)
        
        if not clients:
            print("\nNo hot clients found. Lower the score threshold to see more.")
            return
        
        print(f"\n{'Rank':<6} {'User ID':<15} {'Score':<8} {'Level':<10} {'Budget':<15} {'Locations'}")
        print("-" * 80)
        
        for i, client in enumerate(clients, 1):
            user_id = client.user_id[:14] if len(client.user_id) > 14 else client.user_id
            score = f"{client.total_score:.1f}"
            level = client.hotness_level.value
            
            if client.budget_range:
                budget = f"${client.budget_range[0]:,.0f}-${client.budget_range[1]:,.0f}"
            else:
                budget = "Not specified"
            
            locations = ", ".join(list(client.preferred_locations)[:2]) if client.preferred_locations else "Any"
            
            # Add emoji based on level
            level_emoji = {
                "burning": "🔥",
                "hot": "⚡",
                "warm": "☀️",
                "cold": "❄️"
            }.get(level, "")
            
            print(f"{i:<6} {user_id:<15} {score:<8} {level_emoji} {level:<9} {budget:<15} {locations}")
        
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
    
    def _print_client_report(self, report: Dict):
        """Pretty print client analytics report"""
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
        print("📊 CLIENT ANALYTICS REPORT")
        print("="*60)
        
        print(f"\n📈 Overview")
        print(f"  Total Clients: {report.get('total_clients', 0)}")
        
        stats = report.get('stats_by_level', {})
        if stats:
            print(f"\n🌡️ Client Distribution")
            for level, data in stats.items():
                emoji = {
                    "burning": "🔥",
                    "hot": "⚡",
                    "warm": "☀️",
                    "cold": "❄️"
                }.get(level, "")
                print(f"  {emoji} {level.capitalize()}: {data.get('count', 0)} clients (avg score: {data.get('avg_score', 0):.1f})")
        
        locations = report.get('top_locations', [])
        if locations:
            print(f"\n📍 Top Locations")
            for loc, count in locations[:5]:
                print(f"  • {loc}: {count} clients")
        
        budget = report.get('avg_budget_range', {})
        if budget:
            print(f"\n💰 Average Budget Range")
            print(f"  Min: ${budget.get('min', 0):,.0f}")
            print(f"  Max: ${budget.get('max', 0):,.0f}")
        
        print("\n" + "="*60)
        
        # Partner performance details
        channel_performance = dashboard.get("channel_performance")
        if channel_performance and dashboard.get("dashboard_type") == "partner":
            print(f"\n📉 Detailed Channel Performance")
            for channel_id, perf in channel_performance.items():
                channel_name = next((ch['channel_name'] for ch in channels if ch['channel_id'] == channel_id), channel_id)
                print(f"  • {channel_name}:")
                print(f"    Lead Conversion: {perf['lead_conversion_rate']:.1f}%")
                print(f"    Growth Trend: {perf['growth_trend']}")
                print(f"    Member Value: ${perf['avg_member_value']:.2f}")
            print("\n" + "="*60)
    
    def _client_to_dict(self, client) -> Dict:
        """Convert client object to dictionary"""
        return {
            "user_id": client.user_id,
            "score": client.total_score,
            "level": client.hotness_level.value,
            "budget_range": client.budget_range,
            "locations": list(client.preferred_locations) if client.preferred_locations else [],
            "urgency": client.urgency_indicators,
            "last_active": client.last_active.isoformat() if client.last_active else None
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
    
    # Analytics commands
    analytics_parser = subparsers.add_parser("analytics", help="Show channel analytics")
    analytics_parser.add_argument("--channel", help="Channel ID or 'all' for all channels")
    analytics_parser.add_argument("--partner", help="Partner ID for partner-specific analytics")
    analytics_parser.add_argument("--official", action="store_true", help="Show only OneMinuta official channel analytics")
    analytics_parser.add_argument("--period", choices=["daily", "weekly", "monthly"], default="weekly", help="Analytics period")
    
    hot_clients_parser = subparsers.add_parser("hot-clients", help="Show hot property clients")
    hot_clients_parser.add_argument("--min-score", type=float, default=61.0, help="Minimum hotness score (0-100)")
    hot_clients_parser.add_argument("--limit", type=int, default=20, help="Number of clients to show")
    
    client_report_parser = subparsers.add_parser("client-report", help="Generate client analytics report")
    
    # Partner management
    partners_parser = subparsers.add_parser("partners", help="List all configured partners")
    
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
        
        elif args.command == "analytics":
            import asyncio
            channel_id = getattr(args, 'channel', None) or "all"
            partner_id = getattr(args, 'partner', None)
            official_only = getattr(args, 'official', False)
            period = getattr(args, 'period', 'weekly')
            
            if official_only:
                # Show only OneMinuta official channel
                asyncio.run(cli.official_channel_analytics(json_output=args.json))
            else:
                asyncio.run(cli.channel_analytics(channel_id, partner_id, period, json_output=args.json))
        
        elif args.command == "hot-clients":
            import asyncio
            min_score = getattr(args, 'min_score', 61.0)
            limit = getattr(args, 'limit', 20)
            asyncio.run(cli.hot_clients(min_score, limit, json_output=args.json))
        
        elif args.command == "client-report":
            import asyncio
            asyncio.run(cli.client_report(json_output=args.json))
        
        elif args.command == "partners":
            import asyncio
            asyncio.run(cli.list_partners(json_output=args.json))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()