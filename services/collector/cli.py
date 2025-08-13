"""
Property Collection CLI
Extends the analytics CLI with property collection capabilities
"""

import logging
from datetime import datetime
from typing import List

from services.analytics.telegram_monitor import TelegramPropertyMonitor
from services.analytics.config import get_config
from .property_extractor import PropertyExtractor, ExtractedProperty
from .asset_manager import AssetManager


class PropertyCollectionCLI:
    """CLI for property collection operations"""

    def __init__(self):
        self.config = get_config()
        self.extractor = PropertyExtractor()
        self.asset_manager = AssetManager(self.config.STORAGE_PATH)
        self.logger = logging.getLogger(__name__)

    async def collect_properties(
        self,
        channels: List[str] = None,
        days_back: int = 7,
        limit: int = 100,
        dry_run: bool = False,
    ) -> dict:
        """
        Collect properties from Telegram channels

        Args:
            channels: List of channels to collect from
            days_back: Number of days to look back
            limit: Maximum messages per channel
            dry_run: If True, don't store assets, just show what would be collected
        """

        channels = channels or self.config.DEFAULT_CHANNELS

        print("🏠 PROPERTY COLLECTION")
        print("=" * 50)
        print(f"📅 Collecting from last {days_back} days")
        print(f"📱 Channels: {', '.join(channels)}")
        print(f"📝 Max {limit} messages per channel")
        if dry_run:
            print("🧪 DRY RUN MODE - No assets will be stored")
        print()

        # Initialize Telegram monitor
        monitor = TelegramPropertyMonitor(
            self.config.TELEGRAM_API_ID, self.config.TELEGRAM_API_HASH, self.config.STORAGE_PATH
        )

        total_messages = 0
        total_properties = 0
        total_stored = 0
        properties_by_channel = {}

        for channel in channels:
            print(f"📱 Processing {channel}...")

            try:
                # Get ALL messages from channel (including owner/listing messages)
                messages = await monitor.get_channel_all_messages(
                    channel, limit=limit, days_back=days_back
                )

                channel_properties = 0
                channel_stored = 0

                for message in messages:
                    total_messages += 1

                    # Extract property information
                    extracted = self.extractor.extract_property_details(
                        message_text=message["text"],
                        channel=channel,
                        message_id=message["message_id"],
                        sender_id=message["user_id"],
                        message_date=message["date"],
                    )

                    if extracted:
                        total_properties += 1
                        channel_properties += 1

                        if not dry_run:
                            # Convert to asset and store
                            asset = self.asset_manager.convert_to_asset(extracted)
                            if asset and self.asset_manager.store_asset(asset):
                                total_stored += 1
                                channel_stored += 1
                        else:
                            # In dry run, assume it would be stored
                            channel_stored += 1
                            total_stored += 1

                            # Show what would be extracted
                            print(
                                f"   📋 Would extract: {extracted.asset_type.value if extracted.asset_type else 'Unknown'} "
                                f"- {extracted.rent_or_sale.value if extracted.rent_or_sale else 'Unknown'} "
                                f"- {extracted.price} {extracted.currency if extracted.price else ''} "
                                f"- {extracted.location_text or 'No location'}"
                            )

                properties_by_channel[channel] = {
                    "messages": len(messages),
                    "properties": channel_properties,
                    "stored": channel_stored,
                }

                print(
                    f"   ✅ {len(messages)} messages, {channel_properties} properties found, {channel_stored} {'would be ' if dry_run else ''}stored"
                )

            except Exception as e:
                print(f"   ❌ Error processing {channel}: {e}")
                properties_by_channel[channel] = {
                    "messages": 0,
                    "properties": 0,
                    "stored": 0,
                    "error": str(e),
                }

        # Summary
        print("\n📊 COLLECTION SUMMARY")
        print("=" * 30)
        print(f"📨 Total messages processed: {total_messages}")
        print(f"🏠 Properties identified: {total_properties}")
        print(f"💾 Properties {'would be ' if dry_run else ''}stored: {total_stored}")
        print(
            f"📈 Success rate: {(total_stored/total_properties*100):.1f}%"
            if total_properties > 0
            else "0%"
        )

        if not dry_run and total_stored > 0:
            # Show updated asset statistics
            stats = self.asset_manager.get_asset_stats()
            print("\n📊 UPDATED ASSET STATS")
            print(f"   Total assets in system: {stats['total_assets']}")
            print(f"   By source: {dict(stats['by_source'])}")
            print(f"   By type: {dict(stats['by_type'])}")

        return {
            "total_messages": total_messages,
            "total_properties": total_properties,
            "total_stored": total_stored,
            "by_channel": properties_by_channel,
            "dry_run": dry_run,
        }

    async def list_properties(self, limit: int = 20, filters: dict = None) -> List[dict]:
        """List collected properties with optional filters"""

        print("📋 PROPERTY LISTINGS")
        print("=" * 40)

        if filters:
            print(f"🔍 Filters: {filters}")

        results = self.asset_manager.search_assets(filters or {})

        if not results:
            print("📭 No properties found matching criteria")
            return []

        # Sort by creation date (newest first)
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Show results
        shown = 0
        for asset in results[:limit]:
            shown += 1
            asset_type = asset.get("asset_type", "Unknown")
            transaction = asset.get("rent_or_sale", "Unknown")
            price = asset.get("price", 0)
            location = asset.get("location_area", "Unknown location")

            print(f"\n{shown}. {asset_type.upper()} for {transaction.upper()}")
            print(f"   💰 Price: {price:,.0f} (approx)")
            print(f"   📍 Location: {location}")
            print(f"   🆔 ID: {asset.get('id', 'Unknown')}")
            print(f"   👤 User: {asset.get('user_id', 'Unknown')}")
            print(f"   📅 Added: {asset.get('created_at', 'Unknown')[:10]}")

        if len(results) > limit:
            print(f"\n... and {len(results) - limit} more properties")

        return results[:limit]

    def show_stats(self) -> dict:
        """Show collection statistics"""

        print("📊 ASSET COLLECTION STATISTICS")
        print("=" * 50)

        stats = self.asset_manager.get_asset_stats()

        print(f"📈 Total Assets: {stats['total_assets']}")
        print(f"🕐 Last Updated: {stats.get('last_updated', 'Never')[:19]}")
        print()

        print("📱 By Source:")
        for source, count in stats["by_source"].items():
            print(f"   {source}: {count}")
        print()

        print("🏠 By Type:")
        for asset_type, count in stats["by_type"].items():
            print(f"   {asset_type}: {count}")
        print()

        print("💼 By User:")
        for user, count in stats["by_user"].items():
            print(f"   {user}: {count}")
        print()

        print("💰 By Transaction:")
        for transaction, count in stats["by_transaction"].items():
            print(f"   {transaction}: {count}")

        return stats

    async def test_geo_search(self, lat: float, lon: float, radius_m: float) -> List[dict]:
        """Test geo-spatial search using SpheriCode"""
        
        print("🌍 TESTING GEO-SPATIAL SEARCH")
        print("=" * 40)
        print(f"📍 Center: {lat:.5f}, {lon:.5f}")
        print(f"📏 Radius: {radius_m}m")
        print()
        
        results = self.asset_manager.search_assets_by_location(lat, lon, radius_m)
        
        if not results:
            print("📭 No assets found in search area")
            return []
        
        print(f"✅ Found {len(results)} assets:")
        for i, asset in enumerate(results[:10], 1):  # Show first 10
            print(f"   {i}. {asset.get('asset_type', 'Unknown')} - {asset.get('price', 0):,.0f} {asset.get('currency', 'THB')}")
            print(f"      📍 {asset.get('lat', 0):.5f}, {asset.get('lon', 0):.5f}")
            print(f"      🆔 {asset.get('user_id', 'Unknown')}:{asset.get('asset_id', 'Unknown')}")
        
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
        
        return results
    
    async def test_country_search(self, country: str = "TH") -> List[dict]:
        """Test country-wide asset search"""
        
        print(f"🌍 TESTING COUNTRY-WIDE SEARCH ({country})")
        print("=" * 50)
        
        results = self.asset_manager.search_assets_countrywide(country)
        
        if not results:
            print(f"📭 No assets found in {country}")
            return []
        
        print(f"✅ Found {len(results)} assets in {country}:")
        for i, asset in enumerate(results[:10], 1):  # Show first 10
            print(f"   {i}. {asset.get('asset_type', 'Unknown')} - {asset.get('price', 0):,.0f} {asset.get('currency', 'THB')}")
            print(f"      📍 {asset.get('lat', 0):.5f}, {asset.get('lon', 0):.5f}")
            print(f"      🆔 {asset.get('user_id', 'Unknown')}:{asset.get('asset_id', 'Unknown')}")
            print(f"      📊 SpheriCode: {asset.get('spheri_code', 'Unknown')}")
        
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more")
        
        return results
    
    async def test_extraction(self, sample_text: str) -> ExtractedProperty:
        """Test property extraction on sample text"""

        print("🧪 TESTING PROPERTY EXTRACTION")
        print("=" * 40)
        print(f"📝 Sample text: {sample_text[:100]}...")
        print()

        # Test extraction
        extracted = self.extractor.extract_property_details(
            message_text=sample_text,
            channel="test_channel",
            message_id=12345,
            sender_id="test_user",
            message_date=datetime.utcnow(),
        )

        if not extracted:
            print("❌ Text not identified as property listing")
            return None

        print("✅ Property listing detected!")
        print(f"   🏠 Type: {extracted.asset_type.value if extracted.asset_type else 'Unknown'}")
        print(
            f"   💱 Transaction: {extracted.rent_or_sale.value if extracted.rent_or_sale else 'Unknown'}"
        )
        print(f"   💰 Price: {extracted.price} {extracted.currency}")
        print(f"   🛏️  Bedrooms: {extracted.bedrooms or 'Not specified'}")
        print(f"   🚿 Bathrooms: {extracted.bathrooms or 'Not specified'}")
        print(
            f"   📐 Size: {extracted.size_sqm} sqm"
            if extracted.size_sqm
            else "   📐 Size: Not specified"
        )
        print(
            f"   📍 Locations: {', '.join(extracted.extracted_locations) if extracted.extracted_locations else 'None detected'}"
        )
        print(
            f"   ✨ Features: {', '.join(extracted.features) if extracted.features else 'None detected'}"
        )
        print(f"   📞 Contacts: {len(extracted.contact_info)} found")
        print(f"   🎯 Confidence: {extracted.extraction_confidence:.1f}%")

        return extracted
