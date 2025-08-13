# OneMinuta - Key Concepts & Implementation Strategy

## Core Philosophy
**"Everything is an asset, location is king, files are the database"**

## 🎯 MVP Focus (v1)
**Properties Only** - We tell users "Currently we only support property listings" for any non-property requests.

## 🗺️ Spherical Coordinate System (SpheriCode)

### What is it?
A Morton-encoded (Z-order curve) geographic indexing system that converts lat/lon to fixed-length base32 strings, enabling hierarchical spatial queries.

### How it works:
```python
# Location: Rawai, Phuket
lat, lon = 7.77965, 98.32532
code = encode_sphericode(lat, lon, bits_per_axis=16)
# Result: "37DTTRJKL"

# File path: geo/spheri/37/DT/TR/JK/L/
```

### Benefits:
- **Prefix queries** = radius searches (longer prefix = smaller area)
- **Natural sharding** = distributed file system friendly
- **No database needed** = folders ARE the index

## 👤 User-Centric Storage

### Folder = Mental Model
```
users/u_123/
  assets/property/villa_rawai/
    description.txt    # User writes naturally
    photos/           # User drops images
    meta.json        # System generates
    state.json       # System maintains
```

### Key Innovation:
Users manage assets like managing files on their computer. No forms, no complex UIs - just folders and files.

## 👁️ "Eye of God" File Watcher

### Concept:
System continuously watches storage folder for ANY change and intelligently responds.

### Pipeline:
1. **Detect**: File change via fswatch/watchdog
2. **Classify**: What changed? (asset/user/preference)
3. **Parse**: Extract meaning (possibly with LLM)
4. **Act**: Reindex, notify, update state
5. **Log**: Append to events.ndjson

### Example Flow:
```
User drops photo → Watcher detects → Parse EXIF for location → 
Update meta.json → Compute SpheriCode → Update geo index → 
Check matching wishes → Notify interested users
```

## 🎭 Dual Interface Model

### 1. Natural (User-facing):
- Unstructured `description.txt`
- Regular photo files
- Simple folder organization

### 2. Structured (System-facing):
- Normalized `state.json`
- Event stream `events.ndjson`
- Geo-sharded indexes

The parser bridges these worlds using heuristics and potentially LLM.

## 📝 Event Sourcing Architecture

### Every change is an event:
```json
{"ts":"2025-01-10T10:00:00Z","type":"created","data":{...}}
{"ts":"2025-01-10T11:00:00Z","type":"price_updated","data":{"price":25000}}
{"ts":"2025-01-10T12:00:00Z","type":"relocated","data":{"lat":7.78,"lon":98.33}}
```

### Benefits:
- **Audit trail**: Complete history
- **Replay**: Rebuild state from events
- **Debugging**: See exactly what happened
- **Rollback**: Undo corrupted state

## 🔄 Wishlist Matching

### User wishes:
```json
{
  "kind": "rent_my_asset",
  "asset_id": "prop_001"
}
```
or
```json
{
  "kind": "find",
  "area": "Rawai",
  "max_price": 30000,
  "asset_type": "condo"
}
```

### Matching Engine:
- Continuously compares wishes with available assets
- Instant notification on match
- Bidirectional: sellers find buyers, buyers find sellers

## ⏰ Time as an Asset (Future)

### Concept:
Agent's time for property viewing = bookable asset

### Implementation:
```
users/u_123/calendar/availability.json
→ System knows when agent is free
→ Client requests viewing
→ System books slot
→ Both parties notified
```

## 🚀 Implementation Priorities

### Week 1: Core Systems
1. **SpheriCode library** - The foundation
2. **Mock data generator** - Test with realistic data
3. **CLI search** - Prove the concept works

### Week 2: Intelligence Layer
1. **File watcher** - The "Eye of God"
2. **Parser** - Extract structure from chaos
3. **Indexer** - Maintain consistency

### Week 3: User Interface
1. **Telegram bot** - Natural conversation
2. **Onboarding** - Smooth user experience
3. **Notifications** - Close the loop

## 🏗️ Architecture Principles

### 1. File-First
- No hidden state
- Everything inspectable
- Git-friendly

### 2. Eventual Consistency
- Async indexing
- Event replay
- Self-healing

### 3. Progressive Enhancement
- Start with properties
- Same architecture for vehicles/tickets/time
- Plugins, not rewrites

### 4. Human-Friendly
- Natural folder structure
- Plain text descriptions
- Drag-and-drop photos

## 🎯 Success Metrics

### Performance:
- Search 1000 properties < 100ms
- Index update < 1s after file change
- Handle 100 concurrent users

### Reliability:
- Zero data loss
- Automatic recovery from corruption
- Complete audit trail

### Usability:
- Onboard user < 2 minutes
- Find property < 3 clicks
- Zero training required

## 🚧 Current Limitations (v1)

### Not Supported:
- ❌ Vehicles ("Currently we only support properties")
- ❌ Time slots (manual coordination for now)
- ❌ Payments (contact agent directly)
- ❌ Multi-language (English only)

### Message to Users:
"We're focused on making property search perfect first. Other assets coming soon!"

## 🔮 Future Vision

### Phase 2:
- Vehicle tracking with mobile=true
- Time slot marketplace
- AI-powered description parsing

### Phase 3:
- Ticket exchange
- Service marketplace
- Cross-asset bundles

### The Dream:
A universal marketplace where location-based discovery works for EVERYTHING - from condos to concert tickets, from villa viewings to volleyball lessons.