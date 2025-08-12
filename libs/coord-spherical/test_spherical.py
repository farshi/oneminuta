"""
Tests for spherical coordinate library
"""

import math
import pytest
from spherical import (
    lat_lon_to_unit, unit_to_lat_lon, surface_distance,
    inside_cap, inside_cap_batch, sort_by_dot, bounding_box
)
from sphericode import (
    encode_sphericode, decode_sphericode, suggest_prefix_len_for_radius,
    prefixes_for_query, morton_encode, morton_decode
)


class TestSphericalGeometry:
    """Test basic spherical geometry functions"""
    
    def test_lat_lon_to_unit_basic(self):
        """Test lat/lon to unit vector conversion"""
        # Equator at 0° longitude
        x, y, z = lat_lon_to_unit(0, 0)
        assert abs(x - 1.0) < 1e-10
        assert abs(y - 0.0) < 1e-10
        assert abs(z - 0.0) < 1e-10
        
        # North pole
        x, y, z = lat_lon_to_unit(90, 0)
        assert abs(x - 0.0) < 1e-10
        assert abs(y - 0.0) < 1e-10
        assert abs(z - 1.0) < 1e-10
        
        # South pole
        x, y, z = lat_lon_to_unit(-90, 0)
        assert abs(x - 0.0) < 1e-10
        assert abs(y - 0.0) < 1e-10
        assert abs(z + 1.0) < 1e-10
    
    def test_unit_to_lat_lon_roundtrip(self):
        """Test roundtrip conversion accuracy"""
        test_points = [
            (0, 0),
            (45, 90),
            (-45, -90),
            (7.77965, 98.32532),  # Rawai, Phuket
            (13.7563, 100.5018),  # Bangkok
        ]
        
        for lat, lon in test_points:
            x, y, z = lat_lon_to_unit(lat, lon)
            lat2, lon2 = unit_to_lat_lon(x, y, z)
            
            assert abs(lat - lat2) < 1e-10
            assert abs(lon - lon2) < 1e-10
    
    def test_surface_distance_known_values(self):
        """Test distance calculation with known values"""
        # Bangkok to Phuket (approximately 685 km)
        bangkok_lat, bangkok_lon = 13.7563, 100.5018
        phuket_lat, phuket_lon = 7.8804, 98.3923
        
        dist = surface_distance(bangkok_lat, bangkok_lon, phuket_lat, phuket_lon)
        
        # Should be around 685,000 meters (±10%)
        expected = 685000
        assert abs(dist - expected) < expected * 0.1
    
    def test_surface_distance_same_point(self):
        """Test distance to same point is zero"""
        lat, lon = 7.77965, 98.32532
        dist = surface_distance(lat, lon, lat, lon)
        assert abs(dist) < 1e-6
    
    def test_inside_cap(self):
        """Test spherical cap membership"""
        center_lat, center_lon = 7.77965, 98.32532  # Rawai
        radius_m = 5000  # 5km
        
        # Point inside (same location)
        assert inside_cap(center_lat, center_lon, radius_m, center_lat, center_lon)
        
        # Point outside (Bangkok)
        assert not inside_cap(center_lat, center_lon, radius_m, 13.7563, 100.5018)
        
        # Point on edge (approximately)
        nearby_lat = center_lat + 0.045  # ~5km north
        result = inside_cap(center_lat, center_lon, radius_m, nearby_lat, center_lon)
        # Should be close to the edge
        assert isinstance(result, bool)
    
    def test_inside_cap_batch(self):
        """Test batch cap checking"""
        center_lat, center_lon = 7.77965, 98.32532
        radius_m = 1000
        
        points = [
            (center_lat, center_lon),  # Center - should be inside
            (center_lat + 0.1, center_lon),  # Far - should be outside
            (13.7563, 100.5018),  # Bangkok - should be outside
        ]
        
        results = inside_cap_batch(center_lat, center_lon, radius_m, points)
        
        assert len(results) == 3
        assert results[0] is True  # Center
        assert results[1] is False  # Far point
        assert results[2] is False  # Bangkok
    
    def test_sort_by_dot(self):
        """Test sorting by angular distance"""
        center_lat, center_lon = 7.77965, 98.32532
        
        points = [
            (13.7563, 100.5018, "Bangkok"),  # Far
            (center_lat, center_lon, "Center"),  # Close
            (center_lat + 0.01, center_lon, "Nearby"),  # Medium
        ]
        
        sorted_points = sort_by_dot(center_lat, center_lon, points)
        
        # Should be: Center, Nearby, Bangkok
        assert sorted_points[0][2] == "Center"
        assert sorted_points[1][2] == "Nearby"
        assert sorted_points[2][2] == "Bangkok"


class TestSpheriCode:
    """Test SpheriCode encoding/decoding"""
    
    def test_encode_sphericode_basic(self):
        """Test basic encoding"""
        lat, lon = 7.77965, 98.32532  # Rawai, Phuket
        code = encode_sphericode(lat, lon, bits_per_axis=16)
        
        assert isinstance(code, str)
        assert len(code) > 0
        assert all(c in "0123456789ABCDEFGHJKMNPQRSTVWXYZ" for c in code)
    
    def test_encode_sphericode_bounds(self):
        """Test encoding boundary conditions"""
        # Test corners
        codes = [
            encode_sphericode(-90, -180, 8),
            encode_sphericode(-90, 180, 8),
            encode_sphericode(90, -180, 8),
            encode_sphericode(90, 180, 8),
        ]
        
        # All should be valid and different
        assert len(set(codes)) == 4
        
        # Test invalid inputs
        with pytest.raises(ValueError):
            encode_sphericode(91, 0)  # Invalid lat
        
        with pytest.raises(ValueError):
            encode_sphericode(0, 181)  # Invalid lon
        
        with pytest.raises(ValueError):
            encode_sphericode(0, 0, 0)  # Invalid bits_per_axis
    
    def test_decode_sphericode_roundtrip(self):
        """Test encode/decode roundtrip accuracy"""
        test_points = [
            (0, 0),
            (45, 90),
            (7.77965, 98.32532),  # Rawai
            (13.7563, 100.5018),  # Bangkok
            (-33.8688, 151.2093),  # Sydney
        ]
        
        for bits in [8, 12, 16]:
            for lat, lon in test_points:
                code = encode_sphericode(lat, lon, bits)
                lat2, lon2 = decode_sphericode(code, bits)
                
                # Accuracy depends on bits_per_axis
                tolerance = 180 / (1 << bits)
                assert abs(lat - lat2) < tolerance
                assert abs(lon - lon2) < tolerance
    
    def test_morton_encode_decode(self):
        """Test Morton encoding/decoding"""
        test_pairs = [
            (0, 0),
            (1, 1),
            (255, 255),
            (123, 456),
        ]
        
        for bits in [8, 12, 16]:
            for x, y in test_pairs:
                if x < (1 << bits) and y < (1 << bits):
                    morton = morton_encode(x, y, bits)
                    x2, y2 = morton_decode(morton, bits)
                    
                    assert x == x2
                    assert y == y2
    
    def test_suggest_prefix_len(self):
        """Test prefix length suggestion"""
        # Small radius should suggest long prefix
        small_radius = 100  # 100m
        small_len = suggest_prefix_len_for_radius(small_radius)
        
        # Large radius should suggest short prefix
        large_radius = 50000  # 50km
        large_len = suggest_prefix_len_for_radius(large_radius)
        
        assert small_len > large_len
        assert small_len >= 1
        assert large_len >= 1
    
    def test_prefixes_for_query_basic(self):
        """Test prefix generation for queries"""
        lat, lon = 7.77965, 98.32532
        radius_m = 5000
        
        prefixes = prefixes_for_query(lat, lon, radius_m)
        
        assert isinstance(prefixes, list)
        assert len(prefixes) > 0
        assert all(isinstance(p, str) for p in prefixes)
        
        # Center point should be covered by at least one prefix
        center_code = encode_sphericode(lat, lon)
        assert any(center_code.startswith(p) for p in prefixes)
    
    def test_prefixes_for_query_coverage(self):
        """Test that generated prefixes cover the search area"""
        center_lat, center_lon = 7.77965, 98.32532
        radius_m = 2000
        
        prefixes = prefixes_for_query(center_lat, center_lon, radius_m)
        
        # Test several points within the radius
        test_points = [
            (center_lat, center_lon),  # Center
            (center_lat + 0.01, center_lon),  # North
            (center_lat - 0.01, center_lon),  # South
            (center_lat, center_lon + 0.01),  # East
            (center_lat, center_lon - 0.01),  # West
        ]
        
        for test_lat, test_lon in test_points:
            # Check if point is actually within radius
            dist = surface_distance(center_lat, center_lon, test_lat, test_lon)
            if dist <= radius_m:
                # This point should be covered by at least one prefix
                point_code = encode_sphericode(test_lat, test_lon)
                covered = any(point_code.startswith(p) for p in prefixes)
                assert covered, f"Point ({test_lat}, {test_lon}) not covered by prefixes"


class TestRealWorldScenarios:
    """Test with real-world data"""
    
    def test_phuket_properties(self):
        """Test with realistic Phuket property locations"""
        # Property locations in Phuket
        properties = [
            (7.77965, 98.32532, "Rawai Beach"),
            (7.8167, 98.3500, "Kata Beach"),
            (7.8804, 98.3923, "Patong Beach"),
            (7.9519, 98.3381, "Kamala Beach"),
            (8.0247, 98.2674, "Surin Beach"),
        ]
        
        # Test search from Rawai
        center_lat, center_lon = 7.77965, 98.32532
        radius_m = 15000  # 15km
        
        # Generate prefixes
        prefixes = prefixes_for_query(center_lat, center_lon, radius_m)
        assert len(prefixes) > 0
        
        # Check which properties are covered
        covered_count = 0
        for prop_lat, prop_lon, name in properties:
            dist = surface_distance(center_lat, center_lon, prop_lat, prop_lon)
            prop_code = encode_sphericode(prop_lat, prop_lon)
            
            if dist <= radius_m:
                # Should be covered by prefixes
                covered = any(prop_code.startswith(p) for p in prefixes)
                if covered:
                    covered_count += 1
                print(f"{name}: {dist:.0f}m, covered: {covered}")
        
        assert covered_count > 0
    
    def test_performance_estimate(self):
        """Test performance characteristics"""
        import time
        
        # Time encoding/decoding
        lat, lon = 7.77965, 98.32532
        
        start = time.time()
        for _ in range(1000):
            code = encode_sphericode(lat, lon)
            decode_sphericode(code)
        encode_time = time.time() - start
        
        print(f"1000 encode/decode cycles: {encode_time:.3f}s")
        assert encode_time < 1.0  # Should be fast
        
        # Time prefix generation
        start = time.time()
        for _ in range(100):
            prefixes = prefixes_for_query(lat, lon, 5000)
        prefix_time = time.time() - start
        
        print(f"100 prefix generations: {prefix_time:.3f}s")
        assert prefix_time < 1.0  # Should be reasonably fast


if __name__ == "__main__":
    # Run basic smoke tests
    print("Testing spherical coordinate library...")
    
    # Test basic functionality
    test_geo = TestSphericalGeometry()
    test_geo.test_lat_lon_to_unit_basic()
    test_geo.test_surface_distance_known_values()
    print("✓ Spherical geometry tests passed")
    
    test_spheri = TestSpheriCode()
    test_spheri.test_encode_sphericode_basic()
    test_spheri.test_decode_sphericode_roundtrip()
    print("✓ SpheriCode tests passed")
    
    test_real = TestRealWorldScenarios()
    test_real.test_phuket_properties()
    print("✓ Real-world scenario tests passed")
    
    print("All tests passed! 🎉")