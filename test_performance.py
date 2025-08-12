#!/usr/bin/env python3
"""
Performance tests for OneMinuta CLI
"""

import time
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from oneminuta_cli import OneMinutaCLI


def test_search_performance():
    """Test search performance with various queries"""
    print("Testing OneMinuta Search Performance")
    print("=" * 50)
    
    cli = OneMinutaCLI("./test_storage")
    
    # Test scenarios
    test_cases = [
        {
            "name": "Small radius (1km) - Rawai center",
            "lat": 7.77965, "lon": 98.32532, "radius": 1000
        },
        {
            "name": "Medium radius (5km) - Rawai center", 
            "lat": 7.77965, "lon": 98.32532, "radius": 5000
        },
        {
            "name": "Large radius (15km) - Rawai center",
            "lat": 7.77965, "lon": 98.32532, "radius": 15000
        },
        {
            "name": "Small radius (2km) - Kata center",
            "lat": 7.8167, "lon": 98.3500, "radius": 2000
        },
        {
            "name": "Medium radius (10km) - Patong center",
            "lat": 7.8804, "lon": 98.3923, "radius": 10000
        },
        {
            "name": "With filters - Rent only, max 30k",
            "lat": 7.77965, "lon": 98.32532, "radius": 10000,
            "rent": True, "max_price": 30000
        }
    ]
    
    total_time = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        # Run the search multiple times for better average
        times = []
        for run in range(5):
            start = time.time()
            
            results = cli.search(
                lat=test_case["lat"],
                lon=test_case["lon"], 
                radius_m=test_case.get("radius", 5000),
                rent=test_case.get("rent"),
                sale=test_case.get("sale"),
                min_price=test_case.get("min_price"),
                max_price=test_case.get("max_price"),
                asset_type=test_case.get("asset_type"),
                json_output=True
            )
            
            elapsed = time.time() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        total_time += avg_time
        
        query_info = results["query"]
        result_count = len(results["results"])
        
        print(f"   Results: {result_count} properties")
        print(f"   Performance: {avg_time:.1f}ms avg ({min_time:.1f}-{max_time:.1f}ms)")
        print(f"   Prefixes: {query_info['prefixes_generated']}")
        print(f"   Cells found: {query_info['cells_found']}")
        print(f"   Properties loaded: {query_info['properties_loaded']}")
    
    print(f"\n{'='*50}")
    print(f"PERFORMANCE SUMMARY:")
    print(f"Total test time: {total_time:.1f}ms")
    print(f"Average per search: {total_time/len(test_cases):.1f}ms")
    print(f"Tests passed: {len(test_cases)}")
    
    # Performance targets from PLANNING.md
    print(f"\nTARGET ANALYSIS:")
    avg_per_search = total_time / len(test_cases)
    if avg_per_search < 100:
        print(f"✅ EXCELLENT: {avg_per_search:.1f}ms < 100ms target")
    elif avg_per_search < 200:
        print(f"✅ GOOD: {avg_per_search:.1f}ms < 200ms")
    else:
        print(f"⚠️  SLOW: {avg_per_search:.1f}ms > 200ms")


def test_scaling_properties():
    """Test how performance scales with more properties"""
    print(f"\n{'='*50}")
    print("SCALING TEST")
    print("=" * 50)
    
    cli = OneMinutaCLI("./test_storage")
    
    # Get stats first
    stats = cli.stats(json_output=True)
    print(f"Current dataset: {stats['total_properties']} properties")
    
    # Test same query multiple times to see consistency
    lat, lon = 7.77965, 98.32532  # Rawai center
    radius = 10000  # 10km
    
    print(f"\nRunning 20 identical searches (lat={lat}, lon={lon}, radius={radius}m):")
    
    times = []
    for i in range(20):
        start = time.time()
        results = cli.search(lat=lat, lon=lon, radius_m=radius, json_output=True)
        elapsed = time.time() - start
        times.append(elapsed * 1000)
        
        if i == 0:
            result_count = len(results["results"])
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


def test_memory_usage():
    """Basic memory usage estimation"""
    print(f"\n{'='*50}")
    print("MEMORY USAGE ESTIMATION")
    print("=" * 50)
    
    cli = OneMinutaCLI("./test_storage")
    stats = cli.stats(json_output=True)
    
    # Estimate file sizes
    storage_path = Path("./test_storage")
    
    total_size = 0
    file_counts = {}
    
    for file_path in storage_path.rglob("*"):
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            
            suffix = file_path.suffix
            file_counts[suffix] = file_counts.get(suffix, 0) + 1
    
    print(f"Total storage size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print(f"Properties: {stats['total_properties']}")
    print(f"Bytes per property: {total_size/stats['total_properties']:.0f}")
    
    print(f"\nFile type distribution:")
    for suffix, count in sorted(file_counts.items()):
        print(f"  {suffix or '(no extension)'}: {count} files")
    
    # Estimate scaling
    print(f"\nScaling estimates:")
    bytes_per_prop = total_size / stats['total_properties']
    for prop_count in [100, 1000, 10000]:
        estimated_size = prop_count * bytes_per_prop
        print(f"  {prop_count:,} properties: ~{estimated_size/1024/1024:.1f} MB")


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