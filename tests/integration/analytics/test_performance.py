#!/usr/bin/env python3
"""
Performance tests for OneMinuta storage system
"""

import time
import sys
from pathlib import Path

# Add project root to path  
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now we can import from tests
sys.path.insert(0, str(project_root / "tests"))
from test_helpers import TestStorageHelper, TestFixtureManager, skip_if_no_fixtures


@skip_if_no_fixtures()
def test_search_performance():
    """Test search performance with various queries"""
    print("Testing OneMinuta Search Performance")
    print("=" * 50)
    
    helper = TestStorageHelper()
    test_cases = TestFixtureManager.get_search_scenarios()
    
    # Add additional test cases with filters
    locations = TestFixtureManager.get_sample_locations()
    additional_cases = [
        {
            "name": "With filters - Rent only, max 30k",
            "lat": locations['rawai']['lat'],
            "lon": locations['rawai']['lon'], 
            "radius_m": 10000,
            "filters": {"transaction_type": "rent", "max_price": 30000}
        }
    ]
    
    all_test_cases = test_cases + additional_cases
    
    total_time = 0
    
    for i, test_case in enumerate(all_test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        # Run the search multiple times for better average
        times = []
        for run in range(5):
            start = time.time()
            
            # Use new search system
            filters = test_case.get("filters", {})
            results = helper.search_test_properties(
                lat=test_case["lat"],
                lon=test_case["lon"],
                radius_m=test_case.get("radius_m", test_case.get("radius", 5000)),
                **filters
            )
            
            elapsed = time.time() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        total_time += avg_time
        
        result_count = len(results)
        
        print(f"   Results: {result_count} properties")
        print(f"   Performance: {avg_time:.1f}ms avg ({min_time:.1f}-{max_time:.1f}ms)")
        
        # Check if we met expected minimums
        expected_min = test_case.get("expected_min", 0)
        if result_count >= expected_min:
            print(f"   ✅ Expected >= {expected_min}, got {result_count}")
        else:
            print(f"   ⚠️  Expected >= {expected_min}, got {result_count}")
    
    print(f"\n{'='*50}")
    print(f"PERFORMANCE SUMMARY:")
    print(f"Total test time: {total_time:.1f}ms")
    print(f"Average per search: {total_time/len(all_test_cases):.1f}ms")
    print(f"Tests passed: {len(all_test_cases)}")
    
    # Performance targets
    print(f"\nTARGET ANALYSIS:")
    avg_per_search = total_time / len(all_test_cases)
    if avg_per_search < 100:
        print(f"✅ EXCELLENT: {avg_per_search:.1f}ms < 100ms target")
    elif avg_per_search < 200:
        print(f"✅ GOOD: {avg_per_search:.1f}ms < 200ms")
    else:
        print(f"⚠️  SLOW: {avg_per_search:.1f}ms > 200ms")


@skip_if_no_fixtures()
def test_scaling_properties():
    """Test how performance scales with more properties"""
    print(f"\n{'='*50}")
    print("SCALING TEST")
    print("=" * 50)
    
    helper = TestStorageHelper()
    
    # Get stats first
    stats = helper.get_test_stats()
    print(f"Current dataset: {stats['total_assets']} assets")
    print(f"Available assets: {stats['available_assets']}")
    print(f"Users: {stats['users']}")
    
    # Test same query multiple times to see consistency
    locations = TestFixtureManager.get_sample_locations()
    rawai = locations['rawai']
    
    lat, lon = rawai['lat'], rawai['lon']
    radius = 10000  # 10km
    
    print(f"\nRunning 20 identical searches (lat={lat}, lon={lon}, radius={radius}m):")
    
    times = []
    for i in range(20):
        start = time.time()
        results = helper.search_test_properties(lat=lat, lon=lon, radius_m=radius)
        elapsed = time.time() - start
        times.append(elapsed * 1000)
        
        if i == 0:
            result_count = len(results)
            print(f"Results per query: {result_count}")
    
    print(f"\nTiming results (ms):")
    print(f"  Min: {min(times):.1f}")
    print(f"  Max: {max(times):.1f}")
    print(f"  Avg: {sum(times)/len(times):.1f}")
    print(f"  Std dev: {(sum((t - sum(times)/len(times))**2 for t in times) / len(times))**0.5:.1f}")
    
    # Consistency check
    variance = max(times) - min(times)
    if variance < 5:
        print(f"✅ CONSISTENT: {variance:.1f}ms variance")
    else:
        print(f"⚠️  VARIABLE: {variance:.1f}ms variance")


@skip_if_no_fixtures()
def test_memory_usage():
    """Basic memory usage estimation"""
    print(f"\n{'='*50}")
    print("MEMORY USAGE ESTIMATION")
    print("=" * 50)
    
    helper = TestStorageHelper()
    stats = helper.get_test_stats()
    
    # Estimate file sizes
    storage_path = helper.fixtures_path
    
    total_size = 0
    file_counts = {}
    
    for file_path in storage_path.rglob("*"):
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            
            suffix = file_path.suffix
            file_counts[suffix] = file_counts.get(suffix, 0) + 1
    
    print(f"Total storage size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print(f"Total assets: {stats['total_assets']}")
    print(f"Available assets: {stats['available_assets']}")
    
    if stats['total_assets'] > 0:
        print(f"Bytes per asset: {total_size/stats['total_assets']:.0f}")
    
    print(f"\nFile type distribution:")
    for suffix, count in sorted(file_counts.items()):
        print(f"  {suffix or '(no extension)'}: {count} files")
    
    # Estimate scaling
    print(f"\nScaling estimates:")
    if stats['total_assets'] > 0:
        bytes_per_asset = total_size / stats['total_assets']
        for asset_count in [100, 1000, 10000]:
            estimated_size = asset_count * bytes_per_asset
            print(f"  {asset_count:,} assets: ~{estimated_size/1024/1024:.1f} MB")
    
    # Show storage structure stats
    print(f"\nStorage structure:")
    print(f"  Users: {stats['users']}")
    print(f"  Indexed symlinks: {stats['indexed_symlinks']}")
    print(f"  By asset type: {stats['by_asset_type']}")


if __name__ == "__main__":
    try:
        test_search_performance()
        test_scaling_properties() 
        test_memory_usage()
        
        print(f"\n🎉 All performance tests completed!")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)