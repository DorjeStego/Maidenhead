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
from .bulk import (
    area_km2_many,
    azimuth_many,
    cell_size_deg_many,
    cell_size_km_many,
    cell_size_many,
    children_many,
    contains_many,
    contains_point_many,
    corners_many,
    diagonal_km_many,
    from_latlon_many,
    neighbors_many,
    normalize_many,
    adjacent_many,
    parent_many,
    precision_many,
    intersects_bbox_many,
    intersects_polygon_many,
    initial_bearing_many,
    to_geojson_bbox_many,
    to_geojson_envelope_many,
    to_geojson_feature_collection_many,
    to_geojson_feature_many,
    to_geojson_polygon_many,
    to_utm_zone_many,
    split_bbox_many,
    to_bbox_many,
    to_center_many,
    to_wkt_many,
)
from .core import (
    adjacent,
    azimuth,
    cover_circle,
    cover_line,
    contains_point,
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
    split_bbox_list,
    split_bbox,
    to_center_latlon,
    to_geojson_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_bbox,
    to_geojson_envelope,
    intersects_bbox,
    intersects_polygon,
    to_utm_zone,
    to_wkt,
)

# ---- Geodesy helpers ----
from .geo import azimuthal_sector, bearing_bin, bearing_deg, distance_km, great_circle_path, midpoint

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
    "cover_circle",
    "cover_line",
    "contains_point",
    "intersects_bbox",
    "intersects_polygon",
    "to_utm_zone",
    "cell_size_many",
    "cell_size_deg_many",
    "cell_size_km_many",
    "area_km2_many",
    "diagonal_km_many",
    "parent_many",
    "children_many",
    "to_wkt_many",
    "azimuth_many",
    "contains_point_many",
    "contains_many",
    "corners_many",
    "split_bbox_many",
    "neighbors_many",
    "adjacent_many",
    "precision_many",
    "intersects_bbox_many",
    "intersects_polygon_many",
    "initial_bearing_many",
    "to_utm_zone_many",
    "to_geojson_polygon_many",
    "to_geojson_feature_many",
    "to_geojson_feature_collection_many",
    "to_geojson_bbox_many",
    "to_geojson_envelope_many",
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
    "split_bbox_list",
    "split_bbox",
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
    "great_circle_path",
    "bearing_bin",
    "azimuthal_sector",
]
