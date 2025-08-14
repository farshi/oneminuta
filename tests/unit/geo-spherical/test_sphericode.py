#!/usr/bin/env python3
"""
Test SpheriCode functionality
"""

import sys
import os
# Add geo-spherical libs to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, 'libs', 'geo-spherical'))

from sphericode import (
    encode_sphericode, decode_sphericode, suggest_prefix_len_for_radius,
    prefixes_for_query, morton_encode, morton_decode, CROCKFORD_BASE32
)
from spherical import surface_distance

def test_sphericode():
    print("Testing SpheriCode implementation...")
    
    # Test 1: Basic encoding
    print("1. Testing basic encoding...")
    lat, lon = 7.77965, 98.32532  # Rawai, Phuket
    
    for bits in [8, 12, 16]:
        code = encode_sphericode(lat, lon, bits)
        print(f"   {bits} bits: {code}")
        assert len(code) > 0
        assert all(c in CROCKFORD_BASE32 for c in code)
    print("   ✓ PASSED")
    
    # Test 2: Encode/decode roundtrip
    print("\n2. Testing encode/decode roundtrip...")
    test_locations = [
        (7.77965, 98.32532, "Rawai"),
        (13.7563, 100.5018, "Bangkok"),
        (0, 0, "Equator/Prime"),
        (45, 90, "Mid-lat"),
    ]
    
    for lat, lon, name in test_locations:
        for bits in [8, 12, 16]:
            code = encode_sphericode(lat, lon, bits)
            lat2, lon2 = decode_sphericode(code, bits)
            
            # Tolerance should account for quantization step size
            # For latitude: 180 degrees / (2^bits - 1) quantization levels
            # For longitude: 360 degrees / (2^bits - 1) quantization levels
            max_val = (1 << bits) - 1
            lat_tolerance = 180 / max_val  # Half step for latitude
            lon_tolerance = 360 / max_val  # Half step for longitude
            lat_error = abs(lat - lat2)
            lon_error = abs(lon - lon2)
            
            print(f"   {name} ({bits} bits): error=({lat_error:.6f}, {lon_error:.6f}), tolerance=(lat:{lat_tolerance:.6f}, lon:{lon_tolerance:.6f})")
            assert lat_error < lat_tolerance
            assert lon_error < lon_tolerance
    print("   ✓ PASSED")
    
    # Test 3: Morton encoding
    print("\n3. Testing Morton encoding...")
    test_pairs = [(0, 0), (1, 1), (15, 15), (123, 234)]
    
    for x, y in test_pairs:
        for bits in [8, 12]:
            if x < (1 << bits) and y < (1 << bits):
                morton = morton_encode(x, y, bits)
                x2, y2 = morton_decode(morton, bits)
                print(f"   ({x}, {y}) -> {morton} -> ({x2}, {y2})")
                assert x == x2 and y == y2
    print("   ✓ PASSED")
    
    # Test 4: Prefix length suggestion
    print("\n4. Testing prefix length suggestion...")
    radii = [100, 1000, 5000, 20000, 100000]
    
    for radius in radii:
        prefix_len = suggest_prefix_len_for_radius(radius)
        print(f"   {radius}m radius -> prefix length {prefix_len}")
        assert 1 <= prefix_len <= 10  # Reasonable range
    print("   ✓ PASSED")
    
    # Test 5: Prefix generation for queries
    print("\n5. Testing prefix generation...")
    center_lat, center_lon = 7.77965, 98.32532
    radius_m = 5000
    
    prefixes = prefixes_for_query(center_lat, center_lon, radius_m)
    print(f"   Center: ({center_lat}, {center_lon}), radius: {radius_m}m")
    print(f"   Generated {len(prefixes)} prefixes: {prefixes[:5]}{'...' if len(prefixes) > 5 else ''}")
    
    assert len(prefixes) > 0
    assert len(prefixes) < 100  # Should not be too many
    
    # Verify center is covered
    center_code = encode_sphericode(center_lat, center_lon)
    covered = any(center_code.startswith(p) for p in prefixes)
    print(f"   Center code: {center_code}")
    print(f"   Center covered by prefixes: {covered}")
    assert covered
    print("   ✓ PASSED")
    
    print("\n✅ All SpheriCode tests passed!")

def test_real_world_scenario():
    print("\nTesting real-world scenario...")
    
    # Property search in Phuket
    print("Scenario: Property search in Phuket")
    
    # Search center: Rawai Beach
    search_lat, search_lon = 7.77965, 98.32532
    search_radius = 10000  # 10km
    
    # Sample properties in Phuket
    properties = [
        (7.77965, 98.32532, "Rawai Condo", "prop_001"),
        (7.8167, 98.3500, "Kata Villa", "prop_002"),
        (7.8804, 98.3923, "Patong Apartment", "prop_003"),
        (7.9519, 98.3381, "Kamala House", "prop_004"),
        (8.0247, 98.2674, "Surin Land", "prop_005"),
        (13.7563, 100.5018, "Bangkok Office", "prop_006"),  # Outside search area
    ]
    
    print(f"Search center: ({search_lat}, {search_lon}) Rawai")
    print(f"Search radius: {search_radius}m")
    
    # Generate prefixes for search
    prefixes = prefixes_for_query(search_lat, search_lon, search_radius)
    print(f"Generated {len(prefixes)} prefixes")
    
    # Check each property
    print("\nProperty analysis:")
    results = []
    
    for lat, lon, name, prop_id in properties:
        # Calculate actual distance
        distance = surface_distance(search_lat, search_lon, lat, lon)
        within_radius = distance <= search_radius
        
        # Check if covered by prefixes
        prop_code = encode_sphericode(lat, lon)
        covered_by_prefix = any(prop_code.startswith(p) for p in prefixes)
        
        print(f"  {name}:")
        print(f"    Distance: {distance:.0f}m")
        print(f"    Within radius: {within_radius}")
        print(f"    Code: {prop_code}")
        print(f"    Covered by prefixes: {covered_by_prefix}")
        
        if within_radius:
            assert covered_by_prefix, f"Property {name} should be covered by prefixes"
            results.append((prop_id, name, distance))
        
        print()
    
    print(f"Found {len(results)} properties within {search_radius}m:")
    for prop_id, name, distance in sorted(results, key=lambda x: x[2]):
        print(f"  {prop_id}: {name} ({distance:.0f}m)")
    
    print("✅ Real-world scenario test passed!")

if __name__ == "__main__":
    try:
        test_sphericode()
        test_real_world_scenario()
        print("\n🎉 All SpheriCode tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)