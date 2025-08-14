# OneMinuta Platform - Implementation Planning

## Project Vision
A geo-indexed marketplace platform that will eventually support all asset types, but **v1 focuses exclusively on properties**.

## Development Phases

### Phase 1: MVP - Property-Only Platform (Current Focus)
**Goal**: Build a working property marketplace with geo-sharding and file-based storage

#### Core Components to Build:
1. **Spherical Coordinate Library** ✅ (Structure ready)
   - SpheriCode encoding/decoding
   - Radius queries with prefix generation
   - Distance calculations

2. **Mock Data Generator**
   - Create 10-12 sample properties in Phuket areas (Rawai, Kata, Chalong)
   - Generate realistic meta.json, state.json, events.ndjson
   - Populate geo-sharded folder structure

3. **CLI Tool for Testing**
   ```bash
   oneminuta search --lat 7.78 --lon 98.33 --radius 3000 --rent
   oneminuta show --id u_123:prop_001
   oneminuta reindex
   ```

4. **File Watcher Service**
   - Monitor storage/ for changes
   - Auto-reindex on file modifications
   - Trigger action pipeline

5. **Basic Telegram Bot**
   - Property search only
   - "We currently only support properties" for other requests
   - User onboarding flow

#### Storage Structure (v1):
```
storage/
  users/
    <userId>/
      profile.json
      preferences.json
      assets/
        property/           # Only this in v1
          <propertyId>/
            meta.json
            state.json
            events.ndjson
            description.txt
            photos/
      wishlist.json        # Property wishes only
  geo/
    spheri/
      <prefix>/
        properties/
        index.json
```

#### User Interactions (v1):
- **Supported**: "I want to rent a condo in Rawai"
- **Not Supported**: "I want to rent a car" → "We currently only support property listings"

### Phase 2: Enhanced Property Features
- Agent time management (property viewings)
- Calendar integration for inspections
- LLM-powered description parsing
- Photo analysis and categorization

### Phase 3: Multi-Asset Support (Future)
- Extend to vehicles (cars, bikes)
- Add time slots as assets
- Support event tickets
- Implement mobile asset tracking

## Implementation Priority (Next Steps)

### Week 1: Foundation
1. ✅ Project structure setup
2. 🔴 Implement coord-spherical library
3. 🔴 Create mock data generator
4. 🔴 Build basic CLI search

### Week 2: Storage & Indexing
1. 🔴 Implement file watcher
2. 🔴 Build indexer service
3. 🔴 Create parser for descriptions
4. 🔴 Test geo-sharding performance

### Week 3: User Interface
1. 🔴 Basic Telegram bot
2. 🔴 User onboarding flow
3. 🔴 Search interface
4. 🔴 Property listing flow

### Week 4: Polish & Deploy
1. 🔴 Error handling
2. 🔴 Rate limiting
3. 🔴 Backup system
4. 🔴 Production deployment

## Key Design Decisions

### Why File-Based Storage?
- Zero database dependency
- Easy backup/restore
- Transparent data format
- Git-friendly for versioning
- Natural folder organization

### Why Spherical Coordinates?
- Location is primary index
- Efficient radius queries
- Natural geo-sharding
- Scales globally

### Why Properties First?
- Clear use case
- Known market need
- Simpler regulations
- Stationary assets (easier to index)

## Success Metrics (v1)
- [ ] CLI can search 1000 properties < 100ms
- [ ] File changes trigger reindex < 1s
- [ ] Bot responds to queries < 2s
- [ ] System handles 100 concurrent users
- [ ] Zero database queries

## Technical Constraints
- Python 3.10+ only
- File system as single source of truth
- All writes atomic (write .tmp, then rename)
- Folders < 2000 entries
- Index files < 1MB

## Non-Goals for v1
- ❌ Vehicle listings
- ❌ Time slot booking
- ❌ Payment processing
- ❌ Multi-language support (English only)
- ❌ Web interface
- ❌ Mobile app

## Risk Mitigation
1. **File system limits**: Monitor folder sizes, split when needed
2. **Concurrent writes**: Use file locks and atomic operations
3. **Data corruption**: Regular backups, event replay capability
4. **Spam**: Rate limiting, user verification
5. **Scale**: Start with Phuket only, expand gradually

## Development Principles
1. **Start simple**: Properties only, add complexity later
2. **File-first**: Everything is a file, no hidden state
3. **User-centric**: Folders mirror user mental model
4. **Extensible**: Design for future asset types
5. **Observable**: Log everything, make debugging easy