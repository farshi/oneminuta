# OneMinuta CLI Commands Reference

Complete reference for all available CLI commands in the OneMinuta property marketplace system.

## Quick Start

```bash
# First-time setup - analyze users and collect properties
python -m services.cli.analytics analyze-channel @phuketgidsell @sabay_property
python -m services.cli.collector collect-properties --limit 50
python -m services.cli.assets stats

# Daily operations
python -m services.cli.collector collect-properties --days-back 1
python -m services.cli.analytics summary
```

## 📊 Analytics Commands

### User & Client Analysis

#### `analyze-channel` - Analyze Telegram Channel Users
```bash
# Basic usage
python -m services.cli.analytics analyze-channel @phuketgidsell

# Multiple channels
python -m services.cli.analytics analyze-channel @phuketgidsell @sabay_property

# Custom parameters
python -m services.cli.analytics analyze-channel @phuketgidsell \
  --days-back 7 \
  --min-messages 3 \
  --limit 100
```

**Parameters:**
- `--days-back` (default: 5) - How many days of history to analyze
- `--min-messages` (default: 1) - Minimum messages required per user
- `--limit` (default: 50) - Maximum users to analyze per channel

**Output:** User hotness scores (0-100), interaction patterns, property keywords

#### `summary` - Analytics Summary
```bash
python -m services.cli.analytics summary
```

**Output:** Total users analyzed, average hotness scores, top channels

#### `view-user` - View Specific User Analysis
```bash
python -m services.cli.analytics view-user 123456789
python -m services.cli.analytics view-user 123456789 --detailed
```

#### `export` - Export Analytics Data
```bash
# Export all data
python -m services.cli.analytics export --format json

# Export only hot clients (score >= 70)
python -m services.cli.analytics export --hot-only --format csv

# Export by date range
python -m services.cli.analytics export --from-date 2024-01-01 --to-date 2024-01-31
```

**Formats:** `json`, `csv`, `xlsx`

### Market Analysis

#### `price-analysis` - Property Price Analysis
```bash
# Price analysis by area
python -m services.cli.analytics price-analysis --area rawai
python -m services.cli.analytics price-analysis --area phuket

# Price trends over time
python -m services.cli.analytics price-analysis --days 30 --trend
```

#### `market-trends` - Market Trend Analysis
```bash
# Overall market trends
python -m services.cli.analytics market-trends --days 30

# By asset type
python -m services.cli.analytics market-trends --asset-type CONDO --days 60
```

#### `agent-comparison` - Agent Performance Comparison
```bash
python -m services.cli.analytics agent-comparison
python -m services.cli.analytics agent-comparison --period 7d
```

## 🏠 Property Collection Commands

### Collection Operations

#### `collect-properties` - Collect Properties from Channels
```bash
# Collect from default channels
python -m services.cli.collector collect-properties

# Specific channels
python -m services.cli.collector collect-properties @phuketgidsell @sabay_property

# With parameters
python -m services.cli.collector collect-properties \
  --limit 100 \
  --days-back 3 \
  --min-confidence 60
```

**Parameters:**
- `--limit` (default: 50) - Maximum messages to process per channel
- `--days-back` (default: 5) - Days of message history to analyze
- `--min-confidence` (default: 40) - Minimum confidence score for property detection

#### `stats` - Collection Statistics
```bash
python -m services.cli.collector stats
python -m services.cli.collector stats --detailed
```

**Output:** Total properties collected, by agent, by date, success rates

#### `recent` - Recent Collections
```bash
# Recent collections (all agents)
python -m services.cli.collector recent --limit 10

# By specific agent
python -m services.cli.collector recent --agent tg_phuketgidsell --limit 5

# By date
python -m services.cli.collector recent --date 2024-01-15
```

## 🗺️ Asset Management Commands

### Geo-Spatial Search

#### `search-geo` - Search by Coordinates
```bash
# Basic radius search
python -m services.cli.assets search-geo --lat 7.77965 --lon 98.32532 --radius 5000

# With filters
python -m services.cli.assets search-geo \
  --lat 7.77965 --lon 98.32532 --radius 10000 \
  --asset-type CONDO \
  --max-price 10000000 \
  --rent-or-sale SALE
```

**Parameters:**
- `--lat`, `--lon` - Coordinates (required)
- `--radius` - Search radius in meters (required)
- `--asset-type` - CONDO, VILLA, HOUSE, LAND, APARTMENT
- `--rent-or-sale` - RENT, SALE
- `--min-price`, `--max-price` - Price range
- `--bedrooms` - Number of bedrooms
- `--status` - AVAILABLE, SOLD, RENTED

#### `search-area` - Search by Area Name
```bash
# Search in named areas
python -m services.cli.assets search-area rawai --radius 5000
python -m services.cli.assets search-area "bang tao" --radius 3000

# With filters
python -m services.cli.assets search-area patong \
  --radius 2000 \
  --asset-type VILLA \
  --min-price 5000000
```

#### `search-country` - Country-wide Search
```bash
# All properties in Thailand
python -m services.cli.assets search-country TH

# With filters
python -m services.cli.assets search-country TH \
  --asset-type CONDO \
  --rent-or-sale RENT \
  --max-price 50000

# Export results
python -m services.cli.assets search-country TH --export results.json
```

### Asset Information

#### `stats` - Asset Statistics
```bash
# Overall statistics
python -m services.cli.assets stats

# Detailed breakdown
python -m services.cli.assets stats --detailed
```

**Output:** Total assets, by type, by location, by price range, by agent

#### `view` - View Asset Details
```bash
# View specific asset
python -m services.cli.assets view a1b2c3d4e5f6

# View with full metadata
python -m services.cli.assets view a1b2c3d4e5f6 --full

# View with Telegram metadata
python -m services.cli.assets view a1b2c3d4e5f6 --telegram
```

#### `list-by-agent` - List Agent's Properties
```bash
# List all properties by agent
python -m services.cli.assets list-by-agent tg_phuketgidsell

# With pagination
python -m services.cli.assets list-by-agent tg_phuketgidsell --page 2 --per-page 20

# With filters
python -m services.cli.assets list-by-agent tg_phuketgidsell --asset-type CONDO
```

### Agent Statistics

#### `agent-stats` - Agent Performance
```bash
# Specific agent statistics
python -m services.cli.assets agent-stats tg_phuketgidsell

# All agents comparison
python -m services.cli.assets agent-stats --all

# Agent performance over time
python -m services.cli.assets agent-stats tg_phuketgidsell --period 30d
```

#### `location-stats` - Location Statistics
```bash
# Statistics by location
python -m services.cli.assets location-stats

# By specific area
python -m services.cli.assets location-stats --area rawai

# Geographic distribution
python -m services.cli.assets location-stats --geo-distribution
```

## 🔍 Advanced Analysis Commands

### Multi-Location Operations

#### `multi-location-search` - Search Multiple Areas
```bash
# Search multiple locations
python -m services.cli.assets multi-location-search "rawai,kata,patong" --radius 3000

# With filters
python -m services.cli.assets multi-location-search "rawai,bang tao" \
  --radius 5000 \
  --asset-type VILLA \
  --max-price 20000000
```

#### `density-analysis` - Property Density Analysis
```bash
# Analyze property density
python -m services.cli.assets density-analysis \
  --lat 7.77965 --lon 98.32532 --radius 20000

# Generate heatmap data
python -m services.cli.assets density-analysis \
  --lat 7.77965 --lon 98.32532 --radius 20000 \
  --heatmap --export heatmap.json
```

### Data Export

#### `export-geo` - Export Geo Data
```bash
# Export as GeoJSON
python -m services.cli.assets export-geo --format geojson --area phuket

# Export specific asset types
python -m services.cli.assets export-geo \
  --format geojson \
  --asset-type CONDO \
  --output condos.geojson

# Export with price ranges
python -m services.cli.assets export-geo \
  --format kml \
  --min-price 5000000 \
  --max-price 15000000
```

**Formats:** `geojson`, `kml`, `csv`, `json`

## 🛠️ System Management Commands

### Storage Management

#### `storage-health` - Check Storage Health
```bash
# Basic health check
python -m services.cli.system storage-health

# Detailed analysis
python -m services.cli.system storage-health --detailed

# Fix issues automatically
python -m services.cli.system storage-health --fix
```

#### `rebuild-indexes` - Rebuild Storage Indexes
```bash
# Rebuild all indexes
python -m services.cli.system rebuild-indexes

# Rebuild specific index
python -m services.cli.system rebuild-indexes --type geo
python -m services.cli.system rebuild-indexes --type global
python -m services.cli.system rebuild-indexes --type agent
```

#### `cleanup` - Clean Up Storage
```bash
# Clean orphaned files
python -m services.cli.system cleanup

# Clean with confirmation
python -m services.cli.system cleanup --confirm

# Dry run (show what would be cleaned)
python -m services.cli.system cleanup --dry-run
```

### Configuration

#### `config` - Show Configuration
```bash
# Show all configuration
python -m services.cli.system config

# Show specific section
python -m services.cli.system config --section telegram
python -m services.cli.system config --section storage
```

#### `update-channels` - Update Channel Mappings
```bash
# Update channel to agent mappings
python -m services.cli.system update-channels

# Add new channel
python -m services.cli.system update-channels --add @new_channel:tg_new_agent

# Remove channel
python -m services.cli.system update-channels --remove @old_channel
```

#### `reset-storage` - Reset Storage (⚠️ Destructive)
```bash
# Reset all storage (requires confirmation)
python -m services.cli.system reset-storage --confirm

# Reset specific components
python -m services.cli.system reset-storage --section analytics --confirm
python -m services.cli.system reset-storage --section geo --confirm
```

## 📋 Command Combinations & Workflows

### Daily Operations Workflow
```bash
#!/bin/bash
# Daily property collection and analysis

echo "Collecting new properties..."
python -m services.cli.collector collect-properties --days-back 1

echo "Analyzing recent user activity..."
python -m services.cli.analytics analyze-channel @phuketgidsell @sabay_property --days-back 1

echo "Generating reports..."
python -m services.cli.assets stats
python -m services.cli.analytics summary
```

### Market Research Workflow
```bash
#!/bin/bash
# Market research for specific area

AREA="rawai"
RADIUS=5000

echo "Researching $AREA property market..."

# Search properties in area
python -m services.cli.assets search-area $AREA --radius $RADIUS

# Price analysis
python -m services.cli.analytics price-analysis --area $AREA

# Density analysis
python -m services.cli.assets density-analysis --lat 7.77965 --lon 98.32532 --radius $RADIUS

# Export data
python -m services.cli.assets export-geo --format geojson --area $AREA
```

### Data Migration Workflow
```bash
#!/bin/bash
# Data migration and index rebuild

echo "Backing up current data..."
cp -r storage storage_backup_$(date +%Y%m%d)

echo "Rebuilding all indexes..."
python -m services.cli.system rebuild-indexes

echo "Checking storage health..."
python -m services.cli.system storage-health --fix

echo "Verifying data integrity..."
python -m services.cli.assets stats
```

## 🔧 Command Options & Filters

### Global Options
Available for most commands:
- `--verbose` - Verbose output
- `--quiet` - Suppress non-error output  
- `--config CONFIG_FILE` - Use custom config file
- `--storage PATH` - Override storage path

### Filter Options
Available for search and export commands:

**Asset Filters:**
- `--asset-type` - CONDO, VILLA, HOUSE, LAND, APARTMENT
- `--rent-or-sale` - RENT, SALE
- `--status` - AVAILABLE, SOLD, RENTED
- `--bedrooms` - Number of bedrooms
- `--bathrooms` - Number of bathrooms
- `--furnished` - Furnished status (true/false)

**Price Filters:**
- `--min-price` - Minimum price
- `--max-price` - Maximum price
- `--currency` - THB, USD (default: THB)

**Location Filters:**
- `--area` - Area name
- `--city` - City name
- `--country` - Country code (default: TH)
- `--lat`, `--lon` - Coordinates
- `--radius` - Search radius in meters

**Date Filters:**
- `--from-date` - Start date (YYYY-MM-DD)
- `--to-date` - End date (YYYY-MM-DD)
- `--days-back` - Days back from today

### Output Options
- `--format` - Output format (json, csv, xlsx, geojson, kml)
- `--output FILE` - Output file path
- `--export FILE` - Export results to file
- `--page`, `--per-page` - Pagination

## 📚 Examples by Use Case

### Property Investor Analysis
```bash
# Find luxury villas in premium areas
python -m services.cli.assets search-country TH \
  --asset-type VILLA \
  --min-price 20000000 \
  --rent-or-sale SALE

# Analyze investment hotspots
python -m services.cli.assets multi-location-search "rawai,kata,bang tao" \
  --radius 3000 \
  --min-price 10000000

# Export for analysis
python -m services.cli.assets export-geo \
  --format geojson \
  --asset-type VILLA \
  --min-price 20000000 \
  --output luxury_villas.geojson
```

### Rental Market Research
```bash
# Rental properties in tourist areas
python -m services.cli.assets search-area patong \
  --radius 2000 \
  --rent-or-sale RENT \
  --max-price 50000

# Monthly rental trends
python -m services.cli.analytics market-trends \
  --days 90 \
  --rent-or-sale RENT

# Agent performance for rentals
python -m services.cli.assets agent-stats --all \
  --rent-or-sale RENT
```

### Real Estate Agent Tools
```bash
# Monitor new listings daily
python -m services.cli.collector collect-properties --days-back 1

# Track client interest
python -m services.cli.analytics analyze-channel @your_channel --days-back 3

# Generate client report
python -m services.cli.analytics export --hot-only --format xlsx

# Market comparison
python -m services.cli.analytics agent-comparison --period 30d
```

### Development & Debugging
```bash
# Check system health
python -m services.cli.system storage-health --detailed

# Verify geo-sharding
python -m services.cli.assets search-geo \
  --lat 7.77965 --lon 98.32532 --radius 1000 \
  --verbose

# Debug specific asset
python -m services.cli.assets view <asset-id> --full --telegram
```

## 🚀 Performance Tips

1. **Large datasets**: Use `--limit` and pagination for large results
2. **Geo searches**: Smaller radius = faster search
3. **Country-wide**: Use filters to reduce result size
4. **Regular cleanup**: Run `system cleanup` weekly
5. **Index maintenance**: Rebuild indexes monthly
6. **Export optimization**: Use specific filters before export

## 🛡️ Error Handling

Common error scenarios and solutions:

### "No properties found"
- Check if data has been collected: `collector stats`
- Verify search parameters are not too restrictive
- Run `storage-health` to check for issues

### "Channel not found"  
- Ensure channel exists and is accessible
- Check Telegram API credentials
- Verify channel name format (@channelname)

### "Storage corruption"
- Run `storage-health --fix`
- If severe: `rebuild-indexes`
- Last resort: restore from backup

### "Permission denied"
- Check file permissions in storage directory
- Ensure user has write access
- Verify storage path exists

---

## 📞 Getting Help

For detailed help on any command:
```bash
python -m services.cli.COMMAND --help
```

For system status:
```bash
python -m services.cli.system config
```

For troubleshooting:
```bash
python -m services.cli.system storage-health --detailed
```