# maidenhead/__init__.py
from __future__ import annotations

"""
Maidenhead grid square utilities.

Public API is intentionally small:
- parsing/validation/normalization
- locator <-> lat/lon conversion
- bbox/center helpers
- neighborhood/topology helpers
- basic geodesy helpers (distance/bearing/midpoint)

Everything else is available from submodules (core, geo, vector, mh_types).
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

# ---- Version ----
try:
    __version__ = _pkg_version("maidenhead")
except PackageNotFoundError:  # pragma: no cover (common in editable/dev mode)
    __version__ = "0.1.0.dev2"


# ---- Public types/exceptions ----
from .errors import MaidenheadError, InvalidLocatorError, OutOfRangeError, PrecisionError
from .mh_types import GridSquare

# ---- Core API ----
from .bulk import cell_size_many, from_latlon_many, normalize_many, to_bbox_many, to_center_many
from .core import (
    adjacent,
    azimuth,
    cell_size,
    cell_size_deg,
    cell_size_km,
    area_km2,
    diagonal_km,
    children,
    contains,
    corners,
    from_latlon,
    format_locator,
    initial_bearing,
    is_valid,
    neighbors,
    normalize,
    step,
    parent,
    parse,
    precision_of,
    to_bbox,
    to_bbox_split,
    to_center_latlon,
    to_geojson_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_bbox,
    to_geojson_envelope,
    to_wkt,
)

# ---- Geodesy helpers ----
from .geo import bearing_deg, distance_km, midpoint

__all__ = [
    # meta
    "__version__",
    # types
    "GridSquare",
    # exceptions
    "MaidenheadError",
    "InvalidLocatorError",
    "PrecisionError",
    "OutOfRangeError",
    # core
    "parse",
    "is_valid",
    "normalize",
    "normalize_many",
    "precision_of",
    "from_latlon",
    "format_locator",
    "from_latlon_many",
    "initial_bearing",
    "cell_size",
    "cell_size_deg",
    "cell_size_km",
    "area_km2",
    "diagonal_km",
    "cell_size_many",
    "to_center_latlon",
    "to_geojson_polygon",
    "to_geojson_feature",
    "to_geojson_feature_collection",
    "to_geojson_bbox",
    "to_geojson_envelope",
    "to_wkt",
    "to_center_many",
    "to_bbox",
    "to_bbox_split",
    "to_bbox_many",
    "corners",
    "azimuth",
    "adjacent",
    "contains",
    "neighbors",
    "step",
    "parent",
    "children",
    # geo
    "distance_km",
    "bearing_deg",
    "midpoint",
]
