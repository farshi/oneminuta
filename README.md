# OneMinuta - Property Marketplace Platform (v1)

## Overview
A geo-indexed property marketplace built on a revolutionary file-based architecture with spherical coordinate sharding. Users manage property listings through natural folder structures while the system provides lightning-fast location-based search.

**Current Focus**: Properties only (condos, villas, houses, land)  
**Future Vision**: Extensible to all asset types (vehicles, time slots, tickets)

## Key Principles & Constraints

### 1) Feasibility
- **Scraping**: Use Telegram client (MTProto) API with user account via Telethon/Pyrogram to join public channels and read posts/history
- **Bot Limitations**: Bot API can't read arbitrary channels unless member/admin. Cannot self-add to channels
- **User Engagement**: Bots cannot DM users first. Users must initiate contact via Start button, deep-link, or QR code

**Strategy**: Scrape with user client, engage customers with opt-in bot

### 2) Platform Rules
- **No cold outreach**: Bots can't start conversations. Use deep links/QR for opt-in (t.me/yourbot?start=foo)
- **Anti-spam**: Unsolicited commercial DMs result in blocks/reports
- **Rate limits**: 
  - ~1 msg/sec per user chat
  - ≤20 msgs/min per group
  - ~30 msgs/sec bulk broadcast

### 3) Common Pitfalls to Avoid
1. **Cold DMs/scraping for outreach** → Use deep-links/QR/ads for opt-in
2. **Userbot mass-messaging** → Use user accounts only for reading, not sending
3. **Bot can't read channels** → Scrape with Telethon from normal account
4. **Flooding** → Queue + backoff, respect rate limits
5. **Privacy violations** → Store only public content, provide opt-out
6. **Low-quality leads** → Dedupe, normalize, score freshness

## Architecture Components

### A. Collector Service (collector-listings/)
**Technology**: Python + Telethon (MTProto client)
- Join target public channels/groups
- Pull history + subscribe to new posts
- Save: text, photos, post URL, message_id, channel, date
- Output: Raw event stream to property folders

### B. Parser Service (parser/)
**Technology**: Python
- Extract: location (e.g., "Phuket/Rawai"), price, currency, bedrooms, contacts
- Flag suspected listings (has price + location + image)
- De-duplicate by (channel, message_id)
- Emit normalized events

### C. Indexer Service (indexer/)
**Technology**: Python
- Replay events to compute state
- Maintain agent and geo indexes
- Handle property relocations
- Update spherical geo-shards

### D. Bot Service (bot/)
**Technology**: Python + aiogram
- Onboarding with deep-links
- Search flows: area → budget → beds → notifications
- Commands: /start, /search, /stop, /frequency
- Respect rate limits, batch notifications

### E. API Service (api/)
**Technology**: Python + FastAPI
- Read-only REST endpoints
- File-based queries (no DB)
- Endpoints:
  - GET /search?lat&lon&radius&assetType&rentOrSale
  - GET /property/{id}

### F. Notifier Service (notifier/)
**Technology**: Python
- Scheduled digest delivery
- Match new listings to user filters
- Handle rate limiting with backoff

### G. Geo-Spherical Library (libs/geo-spherical/)
**Technology**: Python
- Spherical geometry calculations
- SpheriCode encoding (Morton-interleaved lat/lon)
- Cap queries for radius search
- Geo-sharding support

## Storage Architecture

### File-Based System (Zero Database)
```
storage/
  agents/
    @agent_handle/
      assets/
        <property-id>/
          meta.json        # id, agent, assetType, location
          state.json       # price, status, availability
          events.ndjson    # append-only event log
          description.md
          photos/
  geo/
    <country>/
      spheri/
        <prefix>/         # nested geo-shards
          properties/
          index.json
  users/
    <user-id>/
      filters.json
      sent.json
      cursor.json
  global/
    recent_events.ndjson
```

## Bot Conversation Flow

1. "สวัสดีครับ/ค่ะ 😊 Where are you looking? (e.g., Phuket › Rawai)"
2. "Budget range?"
3. "Bedrooms?"
4. "How often do you want updates? (Daily / 2-3 per week / Only top picks)"
5. "You can stop anytime with /stop."

## Growth Strategy (No Spam)
- Telegram Ads → deep-link
- QR codes on physical leaflets
- Pin posts in own channel with "Find property" button
- Organic sharing through satisfied users

## Development Setup

### Prerequisites
- Python 3.10+
- Telegram API credentials (api_id, api_hash)
- Bot token from @BotFather

### Installation
```bash
# Clone repository
git clone <repo-url>
cd oneminuta

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration
Create `.env` file with:
```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
STORAGE_PATH=./storage
```

## Component Status

| Component | Purpose | Status |
|-----------|---------|--------|
| libs/geo-spherical | Geo calculations & sharding | ✅ **Complete** |
| services/analytics | Telegram user analytics | ✅ **Complete** |
| services/collector | Property collection from channels | ✅ **Complete** |
| services/cli | Command-line interface | ✅ **Complete** |
| specs/schemas | Data formats | ✅ **Complete** |
| services/bot | User interaction | 🔴 Not started |
| services/api | REST endpoints | 🔴 Not started |
| services/notifier | Send digests | 🔴 Not started |

## Current Implementation (v1.0)

The OneMinuta MVP is **fully operational** with the following completed features:

### ✅ Analytics & Client Scoring System
- **LLM-powered analysis** of Telegram users to identify hot property clients
- **Confidence scoring** for client hotness (0-100 scale)
- **Support for English and Russian** languages
- **5-day message history** analysis

### ✅ Property Collection System  
- **Automatic extraction** from Telegram channel messages
- **Multi-language support** (English/Russian) for property listings
- **Confidence scoring** for property detection (minimum 40/100)
- **Asset validation** with mandatory fields (location, price, assetType)

### ✅ Geo-Sharding with SpheriCode
- **Revolutionary geo-indexing** using spherical coordinates
- **Nested folder structure** for performance: `3/g/6/f/b/s/r`
- **Hierarchical location mapping**: District → City → Province
- **Fast radius searches** using Morton-encoded coordinates

### ✅ File-Based Storage (Zero Database)
- **Complete property metadata** in JSON format
- **User-based organization** for property ownership with permissions
- **Global indexing** with statistics and search capabilities
- **Telegram metadata preservation** for audit trails

## CLI Commands & Usage

The OneMinuta CLI provides comprehensive commands for analytics, property collection, and asset management.

### 📊 Analytics Commands

#### Analyze Channel Users (Client Scoring)
```bash
# Analyze users in specific channels for client hotness
python -m services.cli.analytics analyze-channel @phuketgidsell @sabay_property

# Analyze with custom settings
python -m services.cli.analytics analyze-channel @phuketgidsell --days-back 7 --min-messages 3

# Get analytics summary
python -m services.cli.analytics summary
```

**Output**: Client hotness scores (0-100), interaction patterns, and property interest indicators.

#### View User Analytics
```bash
# View specific user analysis
python -m services.cli.analytics view-user 123456789

# Export analytics data
python -m services.cli.analytics export --format json
```

### 🏠 Property Collection Commands

#### Collect Properties from Channels
```bash
# Collect properties from default channels
python -m services.cli.collector collect-properties

# Collect from specific channels with limits
python -m services.cli.collector collect-properties @phuketgidsell @sabay_property --limit 50 --days-back 3

# Collect with custom confidence threshold
python -m services.cli.collector collect-properties --min-confidence 60
```

**Output**: Extracted properties stored in geo-sharded structure with full metadata.

#### Property Collection Status
```bash
# View collection statistics
python -m services.cli.collector stats

# Show recent collections
python -m services.cli.collector recent --limit 10
```

### 🗺️ Asset Management Commands

#### Search Properties by Location
```bash
# Search within radius of coordinates
python -m services.cli.assets search-geo --lat 7.77965 --lon 98.32532 --radius 5000

# Search in Rawai area (5km radius)
python -m services.cli.assets search-area rawai --radius 5000

# Search with filters
python -m services.cli.assets search-geo --lat 7.77965 --lon 98.32532 --radius 10000 --asset-type CONDO --max-price 10000000
```

#### Country-wide Property Search
```bash
# Search all properties in Thailand
python -m services.cli.assets search-country TH

# Search with filters
python -m services.cli.assets search-country TH --asset-type VILLA --rent-or-sale RENT

# Search by price range
python -m services.cli.assets search-country TH --min-price 5000000 --max-price 15000000
```

#### Asset Statistics
```bash
# View comprehensive asset statistics
python -m services.cli.assets stats

# View by agent
python -m services.cli.assets agent-stats tg_phuketgidsell

# View by location
python -m services.cli.assets location-stats
```

#### Asset Details
```bash
# View specific property details
python -m services.cli.assets view <asset-id>

# List properties by agent
python -m services.cli.assets list-by-agent tg_phuketgidsell
```

### 🔍 Advanced Queries

#### Geo-Spatial Analysis
```bash
# Find properties near multiple locations
python -m services.cli.assets multi-location-search "rawai,kata,patong" --radius 3000

# Analyze property density in areas
python -m services.cli.assets density-analysis --lat 7.77965 --lon 98.32532 --radius 20000

# Export geo data for mapping
python -m services.cli.assets export-geo --format geojson --area phuket
```

#### Market Analysis
```bash
# Price analysis by area
python -m services.cli.analytics price-analysis --area rawai

# Market trends over time
python -m services.cli.analytics market-trends --days 30

# Agent performance comparison
python -m services.cli.analytics agent-comparison
```

### 🛠️ System Management

#### Storage Management
```bash
# Check storage health
python -m services.cli.system storage-health

# Rebuild indexes
python -m services.cli.system rebuild-indexes

# Clean up orphaned files
python -m services.cli.system cleanup
```

#### Configuration
```bash
# Show current configuration
python -m services.cli.system config

# Update channel mappings
python -m services.cli.system update-channels

# Reset storage (⚠️ destructive)
python -m services.cli.system reset-storage --confirm
```

### 📋 Common Use Cases

#### 1. Daily Property Collection
```bash
# Collect new properties from all monitored channels
python -m services.cli.collector collect-properties --days-back 1
python -m services.cli.collector stats
```

#### 2. Client Analysis for Hot Leads
```bash
# Analyze recent user activity for hot clients
python -m services.cli.analytics analyze-channel @phuketgidsell --days-back 3
python -m services.cli.analytics export --hot-only --format csv
```

#### 3. Market Research in Specific Area
```bash
# Research Rawai property market
python -m services.cli.assets search-area rawai --radius 5000
python -m services.cli.analytics price-analysis --area rawai
python -m services.cli.assets density-analysis --lat 7.77965 --lon 98.32532 --radius 5000
```

#### 4. User Performance Monitoring
```bash
# Check user property collection performance
python -m services.cli.assets user-stats tg_phuketgidsell
python -m services.cli.collector recent --user tg_phuketgidsell
```

### 🔧 Environment Configuration

Required environment variables in `.env`:
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
OPENAI_API_KEY=sk-proj-...
STORAGE_PATH=./storage
DEFAULT_CHANNELS=@phuketgidsell,@sabay_property
```

### 📁 Storage Structure Created

After running commands, your storage will look like:
```
storage/
├── users/
│   ├── tg_phuketgidsell/
│   │   ├── <asset-id>_meta.json
│   │   ├── <asset-id>_state.json
│   │   ├── <asset-id>_telegram.json
│   │   └── meta.json (user permissions)
│   └── tg_sabay_property/
├── geo/
│   └── TH/
│       └── spheri/
│           └── 3/g/6/f/b/s/r/  # Nested SpheriCode structure
│               └── properties/
│                   └── <agent>_<asset>.json
├── analytics/
│   ├── users/
│   │   └── <user-id>.json
│   └── channels/
│       └── <channel>.json
└── global/
    └── asset_index.json
```

## Legal & Compliance
- Respect Telegram ToS (no cold DMs, no spam)
- PDPA compliance (Thailand data protection)
- Store only public information
- Provide clear opt-out mechanisms
- No automated mass messaging

## Performance Guidelines
- Atomic writes via rename
- UTC ISO timestamps everywhere
- Keep folders ≤2k entries
- Batch operations where possible
- Cache with TTL for API responses

## Next Steps
1. Implement coord-spherical library for geo operations
2. Set up collector with Telethon for channel monitoring
3. Build parser for listing extraction
4. Create bot with aiogram for user interaction
5. Implement file-based storage and indexing
6. Add API service for programmatic access
7. Set up notifier for scheduled updates