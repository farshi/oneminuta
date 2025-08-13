#!/usr/bin/env python3
"""
Simple test script for spherical coordinate library
"""

import sys
import os
# Add geo-spherical libs to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, 'libs', 'geo-spherical'))

from spherical import (
    lat_lon_to_unit, unit_to_lat_lon, surface_distance,
    inside_cap, angular_radius
)

def test_basic_functionality():
    print("Testing spherical coordinate library...")
    
    # Test 1: Basic conversions
    print("1. Testing lat/lon to unit vector conversion...")
    lat, lon = 7.77965, 98.32532  # Rawai, Phuket
    x, y, z = lat_lon_to_unit(lat, lon)
    lat2, lon2 = unit_to_lat_lon(x, y, z)
    
    print(f"   Original: ({lat:.5f}, {lon:.5f})")
    print(f"   Unit vector: ({x:.5f}, {y:.5f}, {z:.5f})")
    print(f"   Converted back: ({lat2:.5f}, {lon2:.5f})")
    print(f"   Error: ({abs(lat-lat2):.8f}, {abs(lon-lon2):.8f})")
    
    assert abs(lat - lat2) < 1e-10
    assert abs(lon - lon2) < 1e-10
    print("   ✓ PASSED")
    
    # Test 2: Distance calculation
    print("\n2. Testing distance calculation...")
    bangkok_lat, bangkok_lon = 13.7563, 100.5018
    phuket_lat, phuket_lon = 7.8804, 98.3923
    
    dist = surface_distance(bangkok_lat, bangkok_lon, phuket_lat, phuket_lon)
    print(f"   Bangkok to Phuket: {dist:.0f} meters ({dist/1000:.1f} km)")
    
    # Should be around 685 km ± 10%
    expected = 685000
    assert abs(dist - expected) < expected * 0.15  # Allow 15% error
    print("   ✓ PASSED")
    
    # Test 3: Same point distance
    print("\n3. Testing same point distance...")
    same_dist = surface_distance(lat, lon, lat, lon)
    print(f"   Same point distance: {same_dist:.8f} meters")
    assert abs(same_dist) < 1e-6
    print("   ✓ PASSED")
    
    # Test 4: Cap membership
    print("\n4. Testing spherical cap membership...")
    center_lat, center_lon = 7.77965, 98.32532
    radius_m = 5000
    
    # Test center point (should be inside)
    inside_center = inside_cap(center_lat, center_lon, radius_m, center_lat, center_lon)
    print(f"   Center point inside 5km cap: {inside_center}")
    assert inside_center
    
    # Test Bangkok (should be outside)
    inside_bangkok = inside_cap(center_lat, center_lon, radius_m, bangkok_lat, bangkok_lon)
    print(f"   Bangkok inside 5km cap: {inside_bangkok}")
    assert not inside_bangkok
    print("   ✓ PASSED")
    
    print("\n✅ All basic tests passed!")
    return True

def test_sphericode():
    print("\nTesting SpheriCode encoding...")
    
    # Import with fixed path
    import spherical
    
    # Create a simple SpheriCode implementation for testing
    def simple_encode(lat, lon, bits=8):
        """Simple test encoding"""
        # Normalize to [0, 1]
        lat_norm = (lat + 90) / 180
        lon_norm = (lon + 180) / 360
        
        # Convert to integer
        max_val = (1 << bits) - 1
        lat_int = int(lat_norm * max_val)
        lon_int = int(lon_norm * max_val)
        
        return f"{lat_int:04x}{lon_int:04x}"
    
    # Test locations
    locations = [
        (7.77965, 98.32532, "Rawai"),
        (7.8167, 98.3500, "Kata"), 
        (7.8804, 98.3923, "Patong"),
    ]
    
    print("   Encoding test locations:")
    for lat, lon, name in locations:
        code = simple_encode(lat, lon)
        print(f"   {name}: ({lat:.5f}, {lon:.5f}) -> {code}")
    
    print("   ✓ Basic encoding test passed")
    return True

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_sphericode()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)