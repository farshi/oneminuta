# Storage Structure Specification

## Overview
File-based storage system with zero database dependency. All data is stored as JSON/NDJSON files in a hierarchical folder structure.

## Directory Layout

```
storage/
├── users/                           # User-centric organization
│   └── {user_id}/
│       ├── profile.json            # User profile (handle, public flag)
│       ├── preferences.json        # Language, notification settings
│       ├── assets/
│       │   └── property/           # Properties owned by user (v1 only)
│       │       └── {property_id}/
│       │           ├── meta.json   # Immutable metadata
│       │           ├── state.json  # Current state  
│       │           ├── events.ndjson # Event log
│       │           ├── description.txt # Unstructured description
│       │           └── photos/
│       ├── wishlist.json          # User wishes/requests
│       └── calendar/
│           ├── availability.json  # Available time slots
│           └── todos.json         # Tasks/reminders
│
├── geo/                           # Geographic organization
│   └── {country_iso}/              # e.g., "TH"
│       └── spheri/                 # SpheriCode-based sharding
│           └── {prefix}/            # Nested by prefix length
│               ├── properties/      # Symlinks to actual properties
│               ├── index.json       # Cell statistics
│               └── events.ndjson    # Recent events in cell
│
├── users/                           # User data
│   └── {user_id}/
│       ├── filters.json            # Search preferences
│       ├── sent.json               # Sent notifications
│       └── cursor.json             # Last processed position
│
└── global/                          # System-wide data
    ├── recent_events.ndjson        # Global event stream
    ├── idx_by_area.json           # Area index
    └── stats.json                  # Platform statistics
```

## File Formats

### meta.json
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "rawai-condo-2br-65sqm",
  "agent": "@phuket_realty",
  "assetType": "condo",
  "location": {
    "city": "Phuket",
    "area": "Rawai",
    "lat": 7.77965,
    "lon": 98.32532,
    "country": "TH"
  },
  "createdAt": "2025-08-12T06:30:00Z",
  "sourceChannel": "phuket_properties",
  "sourceMessageId": 12345
}
```

### state.json
```json
{
  "forRentOrSale": "rent",
  "price": {
    "value": 28000,
    "currency": "THB",
    "period": "month"
  },
  "status": "available",
  "lastUpdated": "2025-08-12T06:30:00Z",
  "spheri": {
    "code": "37DTTRJKL",
    "bitsPerAxis": 16,
    "prefixLen": 8
  },
  "media": {
    "telegramFileIds": ["AAQCABOMq6cGAAQ..."],
    "cloudUrls": [],
    "localPaths": []
  },
  "bedrooms": 2,
  "bathrooms": 1,
  "areaSqm": 65,
  "floor": 3,
  "furnished": true,
  "parking": 1
}
```

### events.ndjson (newline-delimited JSON)
```json
{"ts":"2025-08-12T06:30:00Z","type":"created","data":{"initial":true},"actor":"collector"}
{"ts":"2025-08-12T07:00:00Z","type":"price_updated","data":{"price":{"value":26000,"currency":"THB","period":"month"}},"actor":"parser"}
{"ts":"2025-08-12T08:00:00Z","type":"status_updated","data":{"status":"leased"},"actor":"indexer"}
```

### index.json (geo cells)
```json
{
  "cell": "37DTTR",
  "count": 128,
  "byStatus": {
    "available": 103,
    "leased": 20,
    "sold": 5
  },
  "byAssetType": {
    "condo": 70,
    "villa": 31,
    "land": 12,
    "other": 15
  },
  "properties": [
    "@phuket_realty:550e8400-e29b-41d4",
    "@rawai_homes:660f9500-f30c-52e5"
  ],
  "children": ["37DTTRAA", "37DTTRAB", "37DTTRAC"],
  "lastIndexed": "2025-08-12T09:00:00Z"
}
```

## Operational Guidelines

### Atomic Writes
All file writes must be atomic:
1. Write to `{filename}.tmp`
2. Rename to `{filename}`

### File Limits
- Keep directories under 2000 entries
- Split large NDJSON files at 10MB
- Rotate event logs monthly

### Backup Strategy
- Incremental backups of `storage/` directory
- Keep 30 days of backups
- Test restore procedure monthly

### Indexing Rules
- Properties have ONE canonical location (agent folder)
- Geo cells contain references only
- Indexes rebuilt from events on corruption
- Cursor files track processing position

### SpheriCode Sharding
- Default: 16 bits per axis
- Prefix lengths: 2, 4, 6, 8 characters
- Deeper nesting for high-density areas
- Parent cells aggregate child statistics

## Performance Considerations

### Caching
- In-memory cache for frequently accessed files
- TTL: 5 minutes for indexes, 1 minute for state
- Invalidate on file modification time change

### Batch Operations
- Group writes by directory
- Process events in batches of 100
- Update indexes every 1000 events

### Monitoring
- Track directory entry counts
- Alert on slow file operations (>1s)
- Monitor disk space usage
- Log file access patterns