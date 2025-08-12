"""
Coord-Spherical Library
Geometry and encoding helpers for spherical indexing and cone/cap queries
"""

from .spherical import (
    lat_lon_to_unit,
    unit_to_lat_lon,
    surface_distance,
    inside_cap,
    inside_cap_batch,
    sort_by_dot,
)
from .sphericode import (
    encode_sphericode,
    decode_sphericode,
    prefixes_for_query,
    suggest_prefix_len_for_radius,
)

__version__ = "1.0.0"
__all__ = [
    "lat_lon_to_unit",
    "unit_to_lat_lon", 
    "surface_distance",
    "inside_cap",
    "inside_cap_batch",
    "sort_by_dot",
    "encode_sphericode",
    "decode_sphericode",
    "prefixes_for_query",
    "suggest_prefix_len_for_radius",
]