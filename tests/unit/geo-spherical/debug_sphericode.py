#!/usr/bin/env python3
"""
Debug SpheriCode implementation
"""

import sys
import os
# Add geo-spherical libs to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, 'libs', 'geo-spherical'))

from sphericode import encode_sphericode, decode_sphericode, morton_encode, morton_decode

def debug_encoding():
    print("Debugging SpheriCode encoding...")
    
    lat, lon = 7.77965, 98.32532
    bits = 8
    
    print(f"Original: lat={lat}, lon={lon}")
    
    # Manual encoding steps
    lat_norm = (lat + 90) / 180
    lon_norm = (lon + 180) / 360
    print(f"Normalized: lat_norm={lat_norm:.6f}, lon_norm={lon_norm:.6f}")
    
    max_val = (1 << bits) - 1
    lat_int = int(lat_norm * max_val)
    lon_int = int(lon_norm * max_val)
    print(f"Integer coords: lat_int={lat_int}, lon_int={lon_int} (max={max_val})")
    
    # Morton encode
    morton = morton_encode(lat_int, lon_int, bits)
    print(f"Morton code: {morton} (binary: {bin(morton)})")
    
    # Test morton decode
    lat_int2, lon_int2 = morton_decode(morton, bits)
    print(f"Decoded ints: lat_int2={lat_int2}, lon_int2={lon_int2}")
    
    # Convert back to normalized
    lat_norm2 = lat_int2 / max_val
    lon_norm2 = lon_int2 / max_val
    print(f"Decoded normalized: lat_norm2={lat_norm2:.6f}, lon_norm2={lon_norm2:.6f}")
    
    # Convert back to degrees
    lat2 = lat_norm2 * 180 - 90
    lon2 = lon_norm2 * 360 - 180
    print(f"Decoded: lat2={lat2:.6f}, lon2={lon2:.6f}")
    
    # Errors
    lat_error = abs(lat - lat2)
    lon_error = abs(lon - lon2)
    print(f"Errors: lat_error={lat_error:.6f}, lon_error={lon_error:.6f}")
    
    # Expected precision
    lat_precision = 180 / (1 << bits)
    lon_precision = 360 / (1 << bits)
    print(f"Expected precision: lat={lat_precision:.6f}, lon={lon_precision:.6f}")
    
    # Test with library function
    print("\nTesting library functions:")
    code = encode_sphericode(lat, lon, bits)
    lat3, lon3 = decode_sphericode(code, bits)
    print(f"Library result: lat3={lat3:.6f}, lon3={lon3:.6f}")
    print(f"Library errors: {abs(lat-lat3):.6f}, {abs(lon-lon3):.6f}")

def test_morton_directly():
    print("\nTesting Morton encoding directly:")
    
    test_cases = [
        (0, 0),
        (1, 0),
        (0, 1),
        (1, 1),
        (2, 3),
        (15, 15),
    ]
    
    for x, y in test_cases:
        morton = morton_encode(x, y, 4)
        x2, y2 = morton_decode(morton, 4)
        print(f"({x}, {y}) -> {morton} -> ({x2}, {y2}) OK: {x==x2 and y==y2}")

if __name__ == "__main__":
    debug_encoding()
    test_morton_directly()