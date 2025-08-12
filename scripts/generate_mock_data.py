#!/usr/bin/env python3
"""
Generate mock data for OneMinuta platform testing
"""

import json
import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "coord-spherical"))

from sphericode import encode_sphericode

# Phuket area coordinates and property data
PHUKET_AREAS = {
    "Rawai": {
        "center": (7.77965, 98.32532),
        "radius": 0.02,  # ~2km spread
        "properties": [
            {"type": "condo", "bedrooms": [1, 2, 3], "price_range": (15000, 45000), "period": "month"},
            {"type": "villa", "bedrooms": [2, 3, 4], "price_range": (3000000, 12000000), "period": None},
            {"type": "townhouse", "bedrooms": [2, 3], "price_range": (25000, 60000), "period": "month"},
        ]
    },
    "Kata": {
        "center": (7.8167, 98.3500),
        "radius": 0.015,
        "properties": [
            {"type": "condo", "bedrooms": [1, 2], "price_range": (20000, 50000), "period": "month"},
            {"type": "villa", "bedrooms": [3, 4, 5], "price_range": (5000000, 18000000), "period": None},
            {"type": "house", "bedrooms": [2, 3], "price_range": (30000, 80000), "period": "month"},
        ]
    },
    "Patong": {
        "center": (7.8804, 98.3923),
        "radius": 0.02,
        "properties": [
            {"type": "condo", "bedrooms": [1, 2], "price_range": (25000, 65000), "period": "month"},
            {"type": "shophouse", "bedrooms": [2, 3], "price_range": (4000000, 8000000), "period": None},
            {"type": "house", "bedrooms": [2, 3, 4], "price_range": (35000, 90000), "period": "month"},
        ]
    },
    "Chalong": {
        "center": (7.8950, 98.3550),
        "radius": 0.025,
        "properties": [
            {"type": "land", "bedrooms": [0], "price_range": (2000000, 15000000), "period": None},
            {"type": "house", "bedrooms": [2, 3, 4], "price_range": (20000, 55000), "period": "month"},
            {"type": "villa", "bedrooms": [3, 4, 5], "price_range": (4000000, 16000000), "period": None},
        ]
    }
}

SAMPLE_AGENTS = [
    {"handle": "@phuket_properties", "name": "Phuket Properties Co."},
    {"handle": "@rawai_realty", "name": "Rawai Realty"},
    {"handle": "@kata_homes", "name": "Kata Homes"},
    {"handle": "@patong_condos", "name": "Patong Condos"},
    {"handle": "@chalong_land", "name": "Chalong Land & Villas"},
]

PROPERTY_DESCRIPTIONS = {
    "condo": [
        "Modern condo with sea view and swimming pool. Fully furnished with Western kitchen.",
        "Luxury condominium in prime location. Features gym, pool, and 24/7 security.",
        "Beachfront condo with stunning ocean views. Walking distance to restaurants and shops.",
        "New development condo with modern amenities. Pool, gym, parking included.",
    ],
    "villa": [
        "Stunning private villa with pool and garden. Perfect for families or groups.",
        "Luxury villa with panoramic sea views. Private pool, maid service available.",
        "Traditional Thai-style villa with modern amenities. Peaceful location.",
        "Contemporary villa design with infinity pool. Walking distance to beach.",
    ],
    "house": [
        "Comfortable family house in quiet neighborhood. Garden and parking included.",
        "Modern house with tropical garden. Close to international schools.",
        "Traditional Thai house with Western comfort. Pool and covered parking.",
        "Two-story house with roof terrace. Great for long-term rental.",
    ],
    "townhouse": [
        "Modern townhouse in gated community. Shared pool and security.",
        "Spacious townhouse with private garden. Family-friendly location.",
        "New townhouse development. Close to shopping and transportation.",
    ],
    "shophouse": [
        "Commercial shophouse in busy area. Ground floor shop, upper floors residence.",
        "Restored shophouse with modern interior. Great for business or residence.",
    ],
    "land": [
        "Prime development land with Chanote title. Ready to build.",
        "Hillside land with sea view potential. Perfect for villa development.",
        "Flat land plot in growing area. Utilities nearby, easy access.",
    ]
}


def generate_random_location(center_lat, center_lon, radius):
    """Generate random location within radius of center"""
    # Simple random distribution (not perfectly uniform on sphere, but good enough for mock data)
    lat_offset = random.uniform(-radius, radius)
    lon_offset = random.uniform(-radius, radius)
    
    lat = center_lat + lat_offset
    lon = center_lon + lon_offset
    
    # Clamp to valid ranges
    lat = max(-90, min(90, lat))
    lon = max(-180, min(180, lon))
    
    return lat, lon


def generate_property_id():
    """Generate unique property ID"""
    return f"prop_{uuid.uuid4().hex[:8]}"


def generate_user_id():
    """Generate unique user ID"""
    return f"u_{uuid.uuid4().hex[:8]}"


def generate_events(property_data, created_at):
    """Generate realistic event history for a property"""
    events = []
    current_time = created_at
    
    # Created event
    events.append({
        "ts": current_time.isoformat() + "Z",
        "type": "created",
        "data": {
            "initial": True,
            "for_rent_or_sale": property_data["for_rent_or_sale"],
            "price": property_data["price"]
        },
        "actor": "collector"
    })
    
    # Maybe some price updates
    if random.random() < 0.3:  # 30% chance of price change
        days_later = random.randint(5, 30)
        current_time += timedelta(days=days_later)
        
        # Price change (±10%)
        old_price = property_data["price"]["value"]
        change = random.uniform(0.9, 1.1)
        new_price = int(old_price * change)
        
        events.append({
            "ts": current_time.isoformat() + "Z",
            "type": "price_updated",
            "data": {
                "price": {
                    "value": new_price,
                    "currency": property_data["price"]["currency"],
                    "period": property_data["price"]["period"]
                }
            },
            "actor": "parser"
        })
        
        # Update property data
        property_data["price"]["value"] = new_price
    
    # Maybe status change
    if random.random() < 0.1:  # 10% chance of status change
        days_later = random.randint(10, 60)
        current_time += timedelta(days=days_later)
        
        new_status = random.choice(["leased", "sold", "pending"])
        
        events.append({
            "ts": current_time.isoformat() + "Z",
            "type": "status_updated",
            "data": {"status": new_status},
            "actor": "indexer"
        })
        
        property_data["status"] = new_status
    
    return events


def create_property(area_name, area_data, agent):
    """Create a single property with all files"""
    
    # Choose property type and specs
    prop_template = random.choice(area_data["properties"])
    
    # Generate location
    center_lat, center_lon = area_data["center"]
    lat, lon = generate_random_location(center_lat, center_lon, area_data["radius"])
    
    # Generate property data
    property_id = generate_property_id()
    bedrooms = random.choice(prop_template["bedrooms"]) if prop_template["bedrooms"] else 0
    price_min, price_max = prop_template["price_range"]
    price_value = random.randint(price_min, price_max)
    
    created_at = datetime.now() - timedelta(days=random.randint(1, 180))
    
    # Determine rent or sale
    for_rent_or_sale = "rent" if prop_template["period"] else "sale"
    
    # Create meta.json (immutable)
    meta = {
        "id": property_id,
        "owner_user_id": agent["user_id"],
        "asset_type": prop_template["type"],
        "location": {
            "city": "Phuket",
            "area": area_name,
            "lat": lat,
            "lon": lon,
            "country": "TH"
        },
        "created_at": created_at.isoformat() + "Z"
    }
    
    # Compute SpheriCode
    spheri_code = encode_sphericode(lat, lon, 16)
    
    # Create state.json (mutable)
    state = {
        "for_rent_or_sale": for_rent_or_sale,
        "price": {
            "value": price_value,
            "currency": "THB",
            "period": prop_template["period"]
        },
        "status": "available",
        "last_updated": created_at.isoformat() + "Z",
        "spheri": {
            "code": spheri_code,
            "bits_per_axis": 16,
            "prefix_len": 8
        },
        "media": {
            "telegram_file_ids": [],
            "cloud_urls": [],
            "local_paths": []
        },
        "bedrooms": bedrooms if bedrooms > 0 else None,
        "bathrooms": random.randint(1, max(1, bedrooms)) if bedrooms > 0 else None,
        "area_sqm": random.randint(30, 200) if prop_template["type"] != "land" else random.randint(100, 2000),
        "furnished": random.choice([True, False, None]),
        "parking": random.randint(0, 2) if random.random() > 0.3 else None
    }
    
    # Generate events
    events = generate_events(state, created_at)
    
    # Create description
    description = random.choice(PROPERTY_DESCRIPTIONS[prop_template["type"]])
    if bedrooms > 0:
        description += f" {bedrooms} bedroom{'s' if bedrooms > 1 else ''}"
    if state["bathrooms"]:
        description += f", {state['bathrooms']} bathroom{'s' if state['bathrooms'] > 1 else ''}"
    description += f". {state['area_sqm']} sqm."
    if state["furnished"]:
        description += " Fully furnished."
    description += f" Contact {agent['handle']} for viewing."
    
    return {
        "property_id": property_id,
        "meta": meta,
        "state": state,
        "events": events,
        "description": description,
        "spheri_code": spheri_code
    }


def create_storage_structure(base_path):
    """Create the storage directory structure"""
    base = Path(base_path)
    
    # Main directories
    (base / "users").mkdir(parents=True, exist_ok=True)
    (base / "geo").mkdir(parents=True, exist_ok=True)
    (base / "global").mkdir(parents=True, exist_ok=True)
    
    print(f"Created storage structure at {base}")


def save_property_files(property_data, base_path, user_id):
    """Save all files for a property"""
    base = Path(base_path)
    
    # Property directory
    prop_dir = base / "users" / user_id / "assets" / "property" / property_data["property_id"]
    prop_dir.mkdir(parents=True, exist_ok=True)
    
    # Save meta.json
    with open(prop_dir / "meta.json", "w") as f:
        json.dump(property_data["meta"], f, indent=2)
    
    # Save state.json
    with open(prop_dir / "state.json", "w") as f:
        json.dump(property_data["state"], f, indent=2)
    
    # Save events.ndjson
    with open(prop_dir / "events.ndjson", "w") as f:
        for event in property_data["events"]:
            f.write(json.dumps(event) + "\n")
    
    # Save description.txt
    with open(prop_dir / "description.txt", "w") as f:
        f.write(property_data["description"])
    
    # Create photos directory
    (prop_dir / "photos").mkdir(exist_ok=True)
    
    return prop_dir


def create_geo_index(properties, base_path):
    """Create geo-sharded indexes"""
    base = Path(base_path)
    
    # Group properties by SpheriCode prefix
    geo_groups = {}
    
    for prop in properties:
        code = prop["spheri_code"]
        
        # Create nested prefixes (2, 4, 6, 8 chars)
        for prefix_len in [2, 4, 6, 8]:
            prefix = code[:prefix_len]
            if prefix not in geo_groups:
                geo_groups[prefix] = []
            geo_groups[prefix].append(prop)
    
    # Create geo directory structure and indexes
    for prefix, props in geo_groups.items():
        # Create nested path: geo/TH/spheri/37/DT/TR/JK/
        path_parts = ["geo", "TH", "spheri"]
        
        # Split prefix into pairs
        for i in range(0, len(prefix), 2):
            path_parts.append(prefix[i:i+2])
        
        geo_dir = base
        for part in path_parts:
            geo_dir = geo_dir / part
        
        geo_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index.json
        by_status = {}
        by_asset_type = {}
        property_refs = []
        
        for prop in props:
            # Count by status
            status = prop["state"]["status"]
            by_status[status] = by_status.get(status, 0) + 1
            
            # Count by asset type
            asset_type = prop["state"]["for_rent_or_sale"]
            by_asset_type[asset_type] = by_asset_type.get(asset_type, 0) + 1
            
            # Add property reference
            user_id = prop["meta"]["owner_user_id"]
            prop_id = prop["property_id"]
            property_refs.append(f"{user_id}:{prop_id}")
        
        index_data = {
            "cell": prefix,
            "count": len(props),
            "by_status": by_status,
            "by_asset_type": by_asset_type,
            "properties": property_refs,
            "children": [],  # Would be computed in real system
            "last_indexed": datetime.now().isoformat() + "Z"
        }
        
        with open(geo_dir / "index.json", "w") as f:
            json.dump(index_data, f, indent=2)
    
    print(f"Created {len(geo_groups)} geo indexes")


def create_user_profiles(agents, base_path):
    """Create user profiles for agents"""
    base = Path(base_path)
    
    for agent in agents:
        user_dir = base / "users" / agent["user_id"]
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Create assets/property directory
        (user_dir / "assets" / "property").mkdir(parents=True, exist_ok=True)
        
        # Profile
        profile = {
            "user_id": agent["user_id"],
            "handle": agent["handle"],
            "public": True,
            "created_at": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat() + "Z",
            "verified": True
        }
        
        with open(user_dir / "profile.json", "w") as f:
            json.dump(profile, f, indent=2)
        
        # Preferences
        preferences = {
            "language": "en",
            "notify_hours_local": [9, 18],
            "radius_default_m": 5000,
            "timezone": "Asia/Bangkok"
        }
        
        with open(user_dir / "preferences.json", "w") as f:
            json.dump(preferences, f, indent=2)
        
        # Wishlist (empty for now)
        with open(user_dir / "wishlist.json", "w") as f:
            json.dump([], f, indent=2)


def main():
    """Generate mock data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate mock data for OneMinuta")
    parser.add_argument("--count", type=int, default=12, help="Number of properties to generate")
    parser.add_argument("--storage", default="./storage", help="Storage directory path")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible data")
    
    args = parser.parse_args()
    
    if args.seed:
        random.seed(args.seed)
    
    print(f"Generating {args.count} mock properties...")
    
    # Create storage structure
    create_storage_structure(args.storage)
    
    # Create user profiles for agents
    agents = []
    for i, agent_template in enumerate(SAMPLE_AGENTS):
        agent = {
            "user_id": generate_user_id(),
            "handle": agent_template["handle"],
            "name": agent_template["name"]
        }
        agents.append(agent)
    
    create_user_profiles(agents, args.storage)
    print(f"Created {len(agents)} agent profiles")
    
    # Generate properties
    all_properties = []
    properties_per_area = args.count // len(PHUKET_AREAS)
    
    for area_name, area_data in PHUKET_AREAS.items():
        area_count = properties_per_area
        if area_name == list(PHUKET_AREAS.keys())[-1]:
            # Add remainder to last area
            area_count += args.count % len(PHUKET_AREAS)
        
        print(f"Generating {area_count} properties in {area_name}...")
        
        for i in range(area_count):
            agent = random.choice(agents)
            prop = create_property(area_name, area_data, agent)
            
            # Save property files
            save_property_files(prop, args.storage, agent["user_id"])
            all_properties.append(prop)
    
    # Create geo indexes
    create_geo_index(all_properties, args.storage)
    
    # Create global stats
    global_dir = Path(args.storage) / "global"
    global_dir.mkdir(exist_ok=True)
    
    stats = {
        "total_properties": len(all_properties),
        "total_users": len(agents),
        "by_area": {area: len([p for p in all_properties if p["meta"]["location"]["area"] == area]) 
                   for area in PHUKET_AREAS.keys()},
        "generated_at": datetime.now().isoformat() + "Z"
    }
    
    with open(global_dir / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ Generated {len(all_properties)} properties successfully!")
    print(f"Storage location: {args.storage}")
    print("\nArea distribution:")
    for area, count in stats["by_area"].items():
        print(f"  {area}: {count} properties")
    
    print(f"\nTo test the data:")
    print(f"  cd {args.storage}")
    print(f"  find . -name 'meta.json' | wc -l  # Should show {len(all_properties)}")
    print(f"  find geo -name 'index.json' | head -5  # Show some geo indexes")


if __name__ == "__main__":
    main()