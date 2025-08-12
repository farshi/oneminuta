"""
Spherical geometry calculations for geographic coordinates
"""

import math
from typing import Tuple, List, Optional

# Earth radius in meters
EARTH_RADIUS_M = 6371000


def lat_lon_to_unit(lat: float, lon: float) -> Tuple[float, float, float]:
    """
    Convert latitude/longitude to unit vector (x, y, z) on unit sphere.
    
    Args:
        lat: Latitude in degrees [-90, 90]
        lon: Longitude in degrees [-180, 180]
    
    Returns:
        Unit vector (x, y, z)
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    
    x = math.cos(lat_rad) * math.cos(lon_rad)
    y = math.cos(lat_rad) * math.sin(lon_rad)
    z = math.sin(lat_rad)
    
    return (x, y, z)


def unit_to_lat_lon(x: float, y: float, z: float) -> Tuple[float, float]:
    """
    Convert unit vector back to latitude/longitude.
    
    Args:
        x, y, z: Unit vector components
    
    Returns:
        (latitude, longitude) in degrees
    """
    lat_rad = math.asin(min(1.0, max(-1.0, z)))  # Clamp to avoid floating point errors
    lon_rad = math.atan2(y, x)
    
    lat = math.degrees(lat_rad)
    lon = math.degrees(lon_rad)
    
    return (lat, lon)


def surface_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point coordinates in degrees
        lat2, lon2: Second point coordinates in degrees
    
    Returns:
        Distance in meters
    """
    # Convert to unit vectors
    v1 = lat_lon_to_unit(lat1, lon1)
    v2 = lat_lon_to_unit(lat2, lon2)
    
    # Compute dot product
    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    
    # Clamp to avoid numerical errors with acos
    dot = min(1.0, max(-1.0, dot))
    
    # Angular distance in radians
    angle_rad = math.acos(dot)
    
    # Convert to meters
    return angle_rad * EARTH_RADIUS_M


def inside_cap(center_lat: float, center_lon: float, radius_m: float,
               point_lat: float, point_lon: float) -> bool:
    """
    Check if a point is inside a spherical cap (circle on sphere).
    
    Args:
        center_lat, center_lon: Center of cap in degrees
        radius_m: Radius of cap in meters
        point_lat, point_lon: Point to test in degrees
    
    Returns:
        True if point is inside cap
    """
    dist = surface_distance(center_lat, center_lon, point_lat, point_lon)
    return dist <= radius_m


def inside_cap_batch(center_lat: float, center_lon: float, radius_m: float,
                     points: List[Tuple[float, float]]) -> List[bool]:
    """
    Check multiple points against a spherical cap.
    
    Args:
        center_lat, center_lon: Center of cap in degrees
        radius_m: Radius of cap in meters
        points: List of (lat, lon) tuples
    
    Returns:
        List of booleans indicating which points are inside
    """
    return [inside_cap(center_lat, center_lon, radius_m, lat, lon) 
            for lat, lon in points]


def sort_by_dot(center_lat: float, center_lon: float,
                points: List[Tuple[float, float, any]]) -> List[Tuple[float, float, any]]:
    """
    Sort points by angular distance from center (using dot product for efficiency).
    Higher dot product = closer.
    
    Args:
        center_lat, center_lon: Center point in degrees
        points: List of (lat, lon, data) tuples
    
    Returns:
        Sorted list (closest first)
    """
    center_vec = lat_lon_to_unit(center_lat, center_lon)
    
    def compute_dot(point):
        lat, lon, data = point
        vec = lat_lon_to_unit(lat, lon)
        dot = center_vec[0] * vec[0] + center_vec[1] * vec[1] + center_vec[2] * vec[2]
        return -dot  # Negative because we want highest dot (closest) first
    
    return sorted(points, key=compute_dot)


def bounding_box(lat: float, lon: float, radius_m: float) -> Tuple[float, float, float, float]:
    """
    Calculate approximate bounding box for a radius query.
    This is a rough estimate for initial filtering.
    
    Args:
        lat, lon: Center point in degrees
        radius_m: Radius in meters
    
    Returns:
        (min_lat, max_lat, min_lon, max_lon)
    """
    # Rough conversion: 1 degree latitude ≈ 111,111 meters
    lat_delta = radius_m / 111111.0
    
    # Longitude varies by latitude
    lon_delta = radius_m / (111111.0 * math.cos(math.radians(lat)))
    
    min_lat = lat - lat_delta
    max_lat = lat + lat_delta
    min_lon = lon - lon_delta
    max_lon = lon + lon_delta
    
    # Clamp latitude to valid range
    min_lat = max(-90, min_lat)
    max_lat = min(90, max_lat)
    
    # Handle longitude wrapping
    if min_lon < -180:
        min_lon += 360
    if max_lon > 180:
        max_lon -= 360
    
    return (min_lat, max_lat, min_lon, max_lon)


def angular_radius(radius_m: float) -> float:
    """
    Convert radius in meters to angular radius in radians.
    
    Args:
        radius_m: Radius in meters
    
    Returns:
        Angular radius in radians
    """
    return radius_m / EARTH_RADIUS_M