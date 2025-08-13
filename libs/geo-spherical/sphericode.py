"""
SpheriCode: Morton-interleaved lat/lon encoding to Crockford Base32
"""

import math
from typing import List, Tuple, Set
from spherical import angular_radius, inside_cap

# Crockford Base32 alphabet (excludes I, L, O, U)
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
BASE32_DECODE = {char: i for i, char in enumerate(CROCKFORD_BASE32)}


def encode_sphericode(lat: float, lon: float, bits_per_axis: int = 16) -> str:
    """
    Encode latitude/longitude to SpheriCode using Morton interleaving.
    
    Args:
        lat: Latitude in degrees [-90, 90]
        lon: Longitude in degrees [-180, 180]  
        bits_per_axis: Precision bits per coordinate (1-26)
    
    Returns:
        Fixed-length Crockford Base32 string
    """
    if not (1 <= bits_per_axis <= 26):
        raise ValueError("bits_per_axis must be between 1 and 26")
    
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude must be between -180 and 180")
    
    # Normalize to [0, 1] range
    lat_norm = (lat + 90) / 180
    lon_norm = (lon + 180) / 360
    
    # Convert to integer coordinates
    max_val = (1 << bits_per_axis) - 1
    lat_int = int(lat_norm * max_val)
    lon_int = int(lon_norm * max_val)
    
    # Morton interleave
    morton = morton_encode(lat_int, lon_int, bits_per_axis)
    
    # Convert to Base32
    return morton_to_base32(morton, bits_per_axis * 2)


def decode_sphericode(code: str, bits_per_axis: int = 16) -> Tuple[float, float]:
    """
    Decode SpheriCode back to latitude/longitude.
    
    Args:
        code: Crockford Base32 SpheriCode
        bits_per_axis: Precision bits per coordinate
    
    Returns:
        (latitude, longitude) in degrees
    """
    # Convert from Base32 to Morton code
    morton = base32_to_morton(code, bits_per_axis * 2)
    
    # Morton decode
    lat_int, lon_int = morton_decode(morton, bits_per_axis)
    
    # Convert back to normalized coordinates
    max_val = (1 << bits_per_axis) - 1
    lat_norm = lat_int / max_val
    lon_norm = lon_int / max_val
    
    # Convert back to degrees
    lat = lat_norm * 180 - 90
    lon = lon_norm * 360 - 180
    
    return (lat, lon)


def morton_encode(x: int, y: int, bits_per_axis: int) -> int:
    """
    Morton encode two integers by interleaving their bits.
    
    Args:
        x, y: Integer coordinates
        bits_per_axis: Number of bits per coordinate
    
    Returns:
        Morton encoded integer
    """
    result = 0
    for i in range(bits_per_axis):
        # Interleave bits: x bit goes to even positions, y bit goes to odd positions
        if x & (1 << i):
            result |= (1 << (2 * i))
        if y & (1 << i):
            result |= (1 << (2 * i + 1))
    return result


def morton_decode(morton: int, bits_per_axis: int) -> Tuple[int, int]:
    """
    Morton decode an integer back to two coordinates.
    
    Args:
        morton: Morton encoded integer
        bits_per_axis: Number of bits per coordinate
    
    Returns:
        (x, y) integer coordinates
    """
    x = 0
    y = 0
    for i in range(bits_per_axis):
        # Extract bits from even/odd positions
        if morton & (1 << (2 * i)):
            x |= (1 << i)
        if morton & (1 << (2 * i + 1)):
            y |= (1 << i)
    return (x, y)


def morton_to_base32(morton: int, total_bits: int) -> str:
    """
    Convert Morton code to Crockford Base32 string.
    
    Args:
        morton: Morton encoded integer
        total_bits: Total number of bits
    
    Returns:
        Crockford Base32 string (padded to fixed length)
    """
    if total_bits == 0:
        return ""
    
    # Calculate required Base32 digits (5 bits per digit)
    num_digits = (total_bits + 4) // 5
    
    result = ""
    for i in range(num_digits):
        digit = morton & 0x1F  # Extract 5 bits
        result = CROCKFORD_BASE32[digit] + result
        morton >>= 5
    
    return result


def base32_to_morton(code: str, total_bits: int) -> int:
    """
    Convert Crockford Base32 string back to Morton code.
    
    Args:
        code: Crockford Base32 string
        total_bits: Expected total number of bits
    
    Returns:
        Morton encoded integer
    """
    if not code:
        return 0
    
    # Validate characters
    for char in code.upper():
        if char not in BASE32_DECODE:
            raise ValueError(f"Invalid Base32 character: {char}")
    
    result = 0
    for char in code.upper():
        result = (result << 5) | BASE32_DECODE[char]
    
    # Mask to expected bit length
    if total_bits > 0:
        mask = (1 << total_bits) - 1
        result &= mask
    
    return result


def suggest_prefix_len_for_radius(radius_m: float, bits_per_axis: int = 16) -> int:
    """
    Suggest appropriate prefix length for a given search radius.
    
    Args:
        radius_m: Search radius in meters
        bits_per_axis: Precision bits per coordinate
    
    Returns:
        Suggested prefix length (characters)
    """
    if radius_m <= 0:
        return 1
    
    # Angular radius in radians
    angular_rad = angular_radius(radius_m)
    
    # Rough estimate: each bit halves the angular resolution
    # We want the cell size to be roughly 2x the radius for good coverage
    target_angular = angular_rad * 2
    
    # Each bit in lat/lon represents roughly pi/2^bits radians
    bits_needed = max(1, math.log2(math.pi / target_angular))
    
    # Convert to prefix length (2 bits per axis, 5 bits per Base32 char)
    total_bits = min(bits_needed * 2, bits_per_axis * 2)
    prefix_len = max(1, int(total_bits / 5))
    
    # Clamp to reasonable range
    max_len = (bits_per_axis * 2 + 4) // 5
    return min(prefix_len, max_len)


def prefixes_for_query(center_lat: float, center_lon: float, radius_m: float,
                      bits_per_axis: int = 16) -> List[str]:
    """
    Generate set of SpheriCode prefixes that cover a circular region.
    
    Args:
        center_lat, center_lon: Center of search in degrees
        radius_m: Search radius in meters
        bits_per_axis: Precision bits per coordinate
    
    Returns:
        List of prefix strings that cover the region
    """
    if radius_m <= 0:
        return []
    
    # Determine appropriate prefix length
    prefix_len = suggest_prefix_len_for_radius(radius_m, bits_per_axis)
    
    # Get center code
    center_code = encode_sphericode(center_lat, center_lon, bits_per_axis)
    center_prefix = center_code[:prefix_len]
    
    # Start with center prefix
    candidates = {center_prefix}
    
    # Explore neighboring prefixes
    _expand_prefixes(candidates, center_lat, center_lon, radius_m, 
                    prefix_len, bits_per_axis)
    
    return list(candidates)


def _expand_prefixes(candidates: Set[str], center_lat: float, center_lon: float,
                    radius_m: float, prefix_len: int, bits_per_axis: int):
    """
    Recursively expand prefix set to cover the search radius.
    """
    max_iterations = 100  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        new_candidates = set()
        
        for prefix in list(candidates):
            # Check all possible neighbors
            neighbors = _get_prefix_neighbors(prefix, prefix_len, bits_per_axis)
            
            for neighbor in neighbors:
                if neighbor not in candidates:
                    # Check if this neighbor overlaps with search area
                    if _prefix_overlaps_circle(neighbor, center_lat, center_lon, 
                                             radius_m, bits_per_axis):
                        new_candidates.add(neighbor)
        
        if not new_candidates:
            break
            
        candidates.update(new_candidates)
    

def _get_prefix_neighbors(prefix: str, prefix_len: int, bits_per_axis: int) -> List[str]:
    """
    Get neighboring prefixes (adjacent cells).
    """
    if len(prefix) < prefix_len:
        return []
    
    neighbors = []
    
    # Convert to Morton and try +/- 1 in each direction
    total_bits = prefix_len * 5
    if total_bits > bits_per_axis * 2:
        total_bits = bits_per_axis * 2
    
    try:
        morton = base32_to_morton(prefix, total_bits)
        lat_int, lon_int = morton_decode(morton, total_bits // 2)
        
        # Try adjacent cells
        for dlat in [-1, 0, 1]:
            for dlon in [-1, 0, 1]:
                if dlat == 0 and dlon == 0:
                    continue
                    
                new_lat = lat_int + dlat
                new_lon = lon_int + dlon
                
                # Check bounds
                max_coord = (1 << (total_bits // 2)) - 1
                if 0 <= new_lat <= max_coord and 0 <= new_lon <= max_coord:
                    new_morton = morton_encode(new_lat, new_lon, total_bits // 2)
                    new_prefix = morton_to_base32(new_morton, total_bits)[:prefix_len]
                    neighbors.append(new_prefix)
    
    except (ValueError, IndexError):
        pass
    
    return neighbors


def _prefix_overlaps_circle(prefix: str, center_lat: float, center_lon: float,
                           radius_m: float, bits_per_axis: int) -> bool:
    """
    Check if a prefix cell overlaps with the search circle.
    """
    try:
        # Decode prefix to get cell bounds
        total_bits = len(prefix) * 5
        if total_bits > bits_per_axis * 2:
            total_bits = bits_per_axis * 2
            
        morton = base32_to_morton(prefix, total_bits)
        lat_int, lon_int = morton_decode(morton, total_bits // 2)
        
        # Get cell center
        max_coord = (1 << (total_bits // 2)) - 1
        cell_lat = (lat_int / max_coord) * 180 - 90
        cell_lon = (lon_int / max_coord) * 360 - 180
        
        # Rough check: is cell center within expanded radius?
        # Add some buffer for cell size
        cell_size_lat = 180 / (1 << (total_bits // 2))
        cell_size_lon = 360 / (1 << (total_bits // 2))
        buffer_m = max(cell_size_lat, cell_size_lon) * 111111  # Very rough
        
        return inside_cap(center_lat, center_lon, radius_m + buffer_m,
                         cell_lat, cell_lon)
    
    except (ValueError, IndexError):
        return False