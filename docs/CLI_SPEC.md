# OneMinuta CLI Specification

## Overview
Command-line interface for managing and querying the OneMinuta property marketplace.

## Implementation Status
- ✅ **Working** - Fully implemented and tested
- 🚧 **Partial** - Basic implementation, needs enhancement  
- 🔴 **Not implemented** - Planned for future releases

### Currently Available Commands ✅
```bash
# Core functionality ready for use:
oneminuta search --lat 7.78 --lon 98.33 --radius 5000   # Geo search
oneminuta search --area "Phuket" --rent --max-price 30000  # Area search  
oneminuta show --id user_id:property_id                    # Property details
oneminuta stats                                             # Storage statistics
oneminuta reindex                                           # Rebuild indexes
oneminuta watch --verbose --log-file watch.log             # File monitoring

# All search filters supported:
# --rent, --sale, --min-price, --max-price, --bedrooms, --bathrooms, --type, --limit
```

## Installation
```bash
# Method 1: Direct usage (currently working)
python oneminuta_cli.py --help

# Method 2: Using wrapper script  
./oneminuta --help

# Method 3: Package installation (in development)
pip install -e .
```

## Core Commands

### 1. System Initialization 🔴
```bash
# Initialize storage structure
oneminuta init --root ./storage

# Seed with mock data
oneminuta seed --count 12 --area Rawai
# Creates 12 sample properties in Rawai area with realistic data
```

### 2. User Management 🔴
```bash
# Create new user profile
oneminuta init-user --user u_123 --handle @john_agent --public true
# Creates: storage/users/u_123/profile.json and folder structure

# Set user preferences
oneminuta set-pref --user u_123 --language en --radius 3000
```

### 3. Property Management 🔴
```bash
# Add new property (interactive)
oneminuta add-property --user u_123
# Prompts for: location, price, type, description
# Creates proper folder structure and files

# Update property
oneminuta update-property --id u_123:prop_001 --price 25000
# Appends price_updated event to events.ndjson

# List user's properties
oneminuta list --user u_123
```

### 4. Search Operations ✅
```bash
# Basic search by location ✅ WORKING
oneminuta search --lat 7.78 --lon 98.33 --radius 3000

# Advanced search with filters ✅ WORKING
oneminuta search \
  --lat 7.78 --lon 98.33 --radius 5000 \
  --rent \                    # or --sale
  --min-price 20000 \
  --max-price 40000 \
  --bedrooms 2 \
  --bathrooms 1 \
  --limit 10

# Search by area name (uses area aliases) ✅ WORKING
oneminuta search --area "Rawai" --rent --max-price 30000

# Available areas: rawai, kata, patong, phuket, bangkok

# Show property details ✅ WORKING
oneminuta show --id user_id:property_id
# Displays: meta, state, location, description preview
```

**Test Results:**
- ✅ Found 6 properties in 1km radius search
- ✅ Area-based search working with predefined locations
- ✅ All filters working: rent/sale, price range, bedrooms, bathrooms
- ✅ Search time: 1-3ms (excellent performance)

### 5. Indexing & Maintenance ✅
```bash
# Rebuild all indexes from events ✅ WORKING
oneminuta reindex
# Scans all assets and rebuilds geo-spatial indexes

# Reindex specific geo cell 🚧 PARTIAL  
oneminuta reindex --cell 37DTTR
# Basic implementation, needs geo cell validation

# Verify data integrity 🔴
oneminuta verify
# Checks: file structure, JSON validity, index consistency

# Show statistics ✅ WORKING
oneminuta stats
# Displays: total properties, by area, by type, by user
```

**Test Results:**
- ✅ Full reindex: 113ms for 3 assets, 4 geo cells
- ✅ Statistics showing user-based organization
- ✅ Proper user/geo index structure

### 6. File Watching & Auto-indexing ✅
```bash
# Start file watcher (daemon mode) ✅ WORKING
oneminuta watch
# Monitors storage/users/ for changes
# Auto-reindexes when property files are modified
# Press Ctrl+C to stop

# Watch with specific actions ✅ WORKING
oneminuta watch --verbose --log-file watch.log
# Verbose mode shows detected file changes
# Logs reindex events to specified file
```

**Test Results:**
- ✅ Real-time file monitoring working
- ✅ Auto-reindex triggers on file changes
- ✅ Verbose logging and file output
- ✅ Graceful shutdown with Ctrl+C

### 7. Wishlist Management 🔴
```bash
# Add wish (what user wants)
oneminuta add-wish --user u_123 --type rent --area Rawai --max-price 25000
# Updates storage/users/u_123/wishlist.json

# Match wishes with available properties
oneminuta match-wishes --user u_123
# Shows properties matching user's wishlist
```

### 8. Development & Testing 🔴
```bash
# Generate mock data
oneminuta mock-gen --properties 50 --users 10

# Benchmark search performance
oneminuta benchmark --queries 1000

# Export data for analysis
oneminuta export --format json --output data.json
```

## Output Formats

### Default (Human-readable)
```
Found 3 properties within 3.0km:

1. Condo in Rawai (550m away)
   Rent: 28,000 THB/month
   2 bed, 1 bath, 65 sqm
   ID: u_123:prop_001

2. Villa in Rawai (1.2km away)
   Sale: 8,500,000 THB
   3 bed, 2 bath, 180 sqm
   ID: u_234:prop_002
```

### JSON Output (--json flag)
```json
{
  "results": [
    {
      "id": "u_123:prop_001",
      "distance_m": 550,
      "location": {"lat": 7.779, "lon": 98.325},
      "price": {"value": 28000, "currency": "THB", "period": "month"},
      "type": "condo",
      "bedrooms": 2
    }
  ],
  "total": 3,
  "query_time_ms": 42
}
```

### CSV Output (--csv flag)
```csv
id,distance_m,lat,lon,price,currency,type,bedrooms
u_123:prop_001,550,7.779,98.325,28000,THB,condo,2
u_234:prop_002,1200,7.781,98.330,8500000,THB,villa,3
```

## Error Handling

### Common Errors
```bash
# Missing required parameters
oneminuta search
Error: --lat and --lon are required for location search

# Invalid coordinates
oneminuta search --lat 200 --lon 98
Error: Latitude must be between -90 and 90

# Property not found
oneminuta show --id invalid_id
Error: Property 'invalid_id' not found

# Storage not initialized
oneminuta search --lat 7.78 --lon 98.33
Error: Storage not initialized. Run 'oneminuta init' first
```

## Configuration

### Config File (.oneminuta.yml)
```yaml
storage_root: ./storage
default_radius: 3000
default_limit: 20
log_level: INFO
watch:
  interval_ms: 1000
  batch_size: 100
```

### Environment Variables
```bash
ONEMINUTA_STORAGE_ROOT=./storage
ONEMINUTA_LOG_LEVEL=DEBUG
ONEMINUTA_DEFAULT_RADIUS=5000
```

## Performance Targets

- Search < 100ms for 10,000 properties
- Reindex single property < 50ms
- Full reindex < 5s for 10,000 properties
- File watch latency < 1s

## Future Commands (v2+)

```bash
# Vehicle support (future)
oneminuta search --type vehicle --subtype car
> "Currently we only support property listings. Vehicle support coming soon!"

# Time slot booking (future)
oneminuta book --property u_123:prop_001 --date 2025-01-15 --time 15:00
> "Booking features are not yet available. Please contact the agent directly."

# Multi-language (future)
oneminuta search --area ราไว --lang th
> "Thai language support coming soon. Please use English area names."
```

## Implementation Notes

1. **All commands should**:
   - Validate inputs before processing
   - Use atomic file operations
   - Log actions for debugging
   - Provide helpful error messages
   - Support --json and --csv output formats

2. **Search optimization**:
   - Use spherical coordinate prefixes for initial filtering
   - Load only necessary files (lazy loading)
   - Cache frequently accessed data in memory
   - Parallelize file reads when possible

3. **Watch mode**:
   - Use efficient file system watchers (inotify/FSEvents)
   - Batch changes to avoid thrashing
   - Implement exponential backoff for errors
   - Provide clear logs of what's being indexed