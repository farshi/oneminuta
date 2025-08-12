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

### G. Coord-Spherical Library (libs/coord-spherical/)
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
| libs/coord-spherical | Geo calculations & sharding | 🔴 Not started |
| services/collector-listings | Scrape Telegram channels | 🔴 Not started |
| services/parser | Normalize listings | 🔴 Not started |
| services/indexer | Maintain indexes | 🔴 Not started |
| services/bot | User interaction | 🔴 Not started |
| services/api | REST endpoints | 🔴 Not started |
| services/notifier | Send digests | 🔴 Not started |
| specs/schemas | Data formats | 🔴 Not started |
| specs/storage | File structure | 🔴 Not started |

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