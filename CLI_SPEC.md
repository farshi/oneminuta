# OneMinuta CLI Specification

## Overview
Command-line interface for managing and querying the OneMinuta property marketplace.

## Installation
```bash
pip install -e .
# or
python -m oneminuta
```

## Core Commands

### 1. System Initialization
```bash
# Initialize storage structure
oneminute init --root ./storage

# Seed with mock data
oneminute seed --count 12 --area Rawai
# Creates 12 sample properties in Rawai area with realistic data
```

### 2. User Management
```bash
# Create new user profile
oneminute init-user --user u_123 --handle @john_agent --public true
# Creates: storage/users/u_123/profile.json and folder structure

# Set user preferences
oneminute set-pref --user u_123 --language en --radius 3000
```

### 3. Property Management
```bash
# Add new property (interactive)
oneminute add-property --user u_123
# Prompts for: location, price, type, description
# Creates proper folder structure and files

# Update property
oneminute update-property --id u_123:prop_001 --price 25000
# Appends price_updated event to events.ndjson

# List user's properties
oneminute list --user u_123
```

### 4. Search Operations
```bash
# Basic search by location
oneminute search --lat 7.78 --lon 98.33 --radius 3000

# Advanced search with filters
oneminute search \
  --lat 7.78 --lon 98.33 --radius 5000 \
  --rent \                    # or --sale
  --min-price 20000 \
  --max-price 40000 \
  --bedrooms 2 \
  --limit 10

# Search by area name (uses area aliases)
oneminute search --area "Rawai" --rent --max-price 30000

# Show property details
oneminute show --id u_123:prop_001
# Displays: meta, state, location, description preview
```

### 5. Indexing & Maintenance
```bash
# Rebuild all indexes from events
oneminute reindex
# Scans all events.ndjson files and rebuilds state.json and indexes

# Reindex specific geo cell
oneminute reindex --cell 37DTTR

# Verify data integrity
oneminute verify
# Checks: file structure, JSON validity, index consistency

# Show statistics
oneminute stats
# Displays: total properties, by status, by area, by type
```

### 6. File Watching & Auto-indexing
```bash
# Start file watcher (daemon mode)
oneminute watch
# Monitors storage/ for changes
# Auto-reindexes affected cells
# Logs actions to console/file

# Watch with specific actions
oneminute watch --verbose --log-file watch.log
```

### 7. Wishlist Management
```bash
# Add wish (what user wants)
oneminute add-wish --user u_123 --type rent --area Rawai --max-price 25000
# Updates storage/users/u_123/wishlist.json

# Match wishes with available properties
oneminute match-wishes --user u_123
# Shows properties matching user's wishlist
```

### 8. Development & Testing
```bash
# Generate mock data
oneminute mock-gen --properties 50 --users 10

# Benchmark search performance
oneminute benchmark --queries 1000

# Export data for analysis
oneminute export --format json --output data.json
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
oneminute search
Error: --lat and --lon are required for location search

# Invalid coordinates
oneminute search --lat 200 --lon 98
Error: Latitude must be between -90 and 90

# Property not found
oneminute show --id invalid_id
Error: Property 'invalid_id' not found

# Storage not initialized
oneminute search --lat 7.78 --lon 98.33
Error: Storage not initialized. Run 'oneminute init' first
```

## Configuration

### Config File (.oneminute.yml)
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
ONEMINUTE_STORAGE_ROOT=./storage
ONEMINUTE_LOG_LEVEL=DEBUG
ONEMINUTE_DEFAULT_RADIUS=5000
```

## Performance Targets

- Search < 100ms for 10,000 properties
- Reindex single property < 50ms
- Full reindex < 5s for 10,000 properties
- File watch latency < 1s

## Future Commands (v2+)

```bash
# Vehicle support (future)
oneminute search --type vehicle --subtype car
> "Currently we only support property listings. Vehicle support coming soon!"

# Time slot booking (future)
oneminute book --property u_123:prop_001 --date 2025-01-15 --time 15:00
> "Booking features are not yet available. Please contact the agent directly."

# Multi-language (future)
oneminute search --area ราไว --lang th
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