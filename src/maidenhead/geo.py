# maidenhead/geo.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Tuple, Union, overload

from .errors import MissingDependencyError
if TYPE_CHECKING:
    from .mh_types import GridSquare, LocatorLike
else:
    LocatorLike = Union[str, object]

# Mean Earth radius in km (IUGG recommended mean radius)
EARTH_RADIUS_KM: float = 6371.0088

# Distance method options.
DistanceMethod = Literal["haversine", "geodesic"]

# We allow either a locator-like or explicit lat/lon pair.
PointLike = Union[LocatorLike, Tuple[float, float]]


def _deg2rad(deg: float) -> float:
    return deg * (math.pi / 180.0)


def _rad2deg(rad: float) -> float:
    return rad * (180.0 / math.pi)


def _normalize_lon(lon: float) -> float:
    """Normalize longitude to [-180, 180)."""
    # Using modulo wrap; careful with Python negative modulo.
    lon = (lon + 180.0) % 360.0 - 180.0
    # Keep -180 as 180? convention: return -180 inclusive ok.
    return lon


def _resolve_point(p: PointLike) -> tuple[float, float]:
    """
    Resolve a PointLike (locator/GridSquare/(lat,lon)) to (lat, lon) in degrees.
    """
    from .mh_types import GridSquare
    if isinstance(p, GridSquare):
        from .core import to_center_latlon
        return to_center_latlon(p)

    if isinstance(p, str):
        from .core import to_center_latlon
        return to_center_latlon(p)

    # Assume (lat, lon)
    if (
        isinstance(p, tuple)
        and len(p) == 2
        and isinstance(p[0], (int, float))
        and isinstance(p[1], (int, float))
    ):
        return (float(p[0]), float(p[1]))

    raise TypeError(f"Unsupported point type: {type(p).__name__}")


def haversine_distance_km(
    a: PointLike,
    b: PointLike,
    *,
    radius_km: float = EARTH_RADIUS_KM,
) -> float:
    """
    Great-circle distance between points using the haversine formula.
    Inputs may be Maidenhead locators/GridSquare or explicit (lat, lon) tuples.
    """
    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)

    φ1 = _deg2rad(lat1)
    φ2 = _deg2rad(lat2)
    dφ = _deg2rad(lat2 - lat1)
    dλ = _deg2rad(_normalize_lon(lon2 - lon1))

    sin_dφ2 = math.sin(dφ / 2.0)
    sin_dλ2 = math.sin(dλ / 2.0)

    h = sin_dφ2 * sin_dφ2 + math.cos(φ1) * math.cos(φ2) * sin_dλ2 * sin_dλ2
    # Guard against tiny floating overshoots.
    h = min(1.0, max(0.0, h))
    return 2.0 * radius_km * math.asin(math.sqrt(h))


def geodesic_distance_km(a: PointLike, b: PointLike) -> float:
    """
    High-accuracy ellipsoidal distance using GeographicLib (WGS84).
    Requires: geographiclib
    """
    try:
        from geographiclib.geodesic import Geodesic  # type: ignore
    except Exception as e:  # ImportError and any packaging weirdness
        raise MissingDependencyError(
            "geodesic distance requires 'geographiclib' (pip install geographiclib)"
        ) from e

    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)
    inv = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)
    # inv["s12"] is meters
    return float(inv["s12"]) / 1000.0


def distance_km(
    a: PointLike,
    b: PointLike,
    *,
    method: DistanceMethod = "haversine",
) -> float:
    """
    Distance between two points in kilometers.

    method:
      - "haversine" (default): fast, no dependencies (spherical approximation)
      - "geodesic": accurate on WGS84 ellipsoid (requires geographiclib)
    """
    if method == "haversine":
        return haversine_distance_km(a, b)
    if method == "geodesic":
        return geodesic_distance_km(a, b)
    raise ValueError(f"Unknown method: {method!r}")


def bearing_deg(a: PointLike, b: PointLike) -> float:
    """
    Initial bearing (forward azimuth) from point a to b, in degrees [0, 360).

    Uses spherical trig (consistent with haversine). If you need an ellipsoidal
    bearing, use geographiclib directly or add a geodesic-bearing option later.
    """
    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)

    φ1 = _deg2rad(lat1)
    φ2 = _deg2rad(lat2)
    λ1 = _deg2rad(lon1)
    λ2 = _deg2rad(lon2)

    dλ = λ2 - λ1

    y = math.sin(dλ) * math.cos(φ2)
    x = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(dλ)

    θ = math.atan2(y, x)
    brng = (_rad2deg(θ) + 360.0) % 360.0
    return brng


def midpoint(a: PointLike, b: PointLike) -> tuple[float, float]:
    """
    Great-circle midpoint between two points, returned as (lat, lon) in degrees.

    This is the midpoint along the great-circle (spherical) path, not the
    arithmetic average of lat/lon.
    """
    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)

    φ1 = _deg2rad(lat1)
    λ1 = _deg2rad(lon1)
    φ2 = _deg2rad(lat2)
    λ2 = _deg2rad(lon2)

    dλ = λ2 - λ1

    bx = math.cos(φ2) * math.cos(dλ)
    by = math.cos(φ2) * math.sin(dλ)

    φ3 = math.atan2(
        math.sin(φ1) + math.sin(φ2),
        math.sqrt((math.cos(φ1) + bx) ** 2 + by**2),
    )
    λ3 = λ1 + math.atan2(by, math.cos(φ1) + bx)

    lat3 = _rad2deg(φ3)
    lon3 = _normalize_lon(_rad2deg(λ3))
    return (lat3, lon3)


def great_circle_path(a: PointLike, b: PointLike, n: int = 100) -> list[tuple[float, float]]:
    """
    Return points along the great-circle path from a to b.
    """
    if n < 2:
        raise ValueError("n must be >= 2")
    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)

    φ1 = _deg2rad(lat1)
    λ1 = _deg2rad(lon1)
    φ2 = _deg2rad(lat2)
    λ2 = _deg2rad(lon2)

    d = 2.0 * math.asin(
        math.sqrt(
            math.sin((φ2 - φ1) / 2.0) ** 2
            + math.cos(φ1) * math.cos(φ2) * math.sin((λ2 - λ1) / 2.0) ** 2
        )
    )
    if d == 0.0:
        return [(lat1, lon1)] * n

    points: list[tuple[float, float]] = []
    for i in range(n):
        f = i / (n - 1)
        a_coeff = math.sin((1.0 - f) * d) / math.sin(d)
        b_coeff = math.sin(f * d) / math.sin(d)
        x = a_coeff * math.cos(φ1) * math.cos(λ1) + b_coeff * math.cos(φ2) * math.cos(λ2)
        y = a_coeff * math.cos(φ1) * math.sin(λ1) + b_coeff * math.cos(φ2) * math.sin(λ2)
        z = a_coeff * math.sin(φ1) + b_coeff * math.sin(φ2)
        lat = _rad2deg(math.atan2(z, math.sqrt(x * x + y * y)))
        lon = _normalize_lon(_rad2deg(math.atan2(y, x)))
        points.append((lat, lon))
    return points


def bearing_bin(a: PointLike, b: PointLike, bin_size: float = 5.0) -> float:
    """
    Return the bearing bin start angle (degrees).
    """
    if bin_size <= 0:
        raise ValueError("bin_size must be > 0")
    bearing = bearing_deg(a, b)
    return math.floor(bearing / bin_size) * bin_size


def azimuthal_sector(a: PointLike, b: PointLike, width_deg: float) -> tuple[float, float]:
    """
    Return (start_deg, end_deg) sector around the bearing.
    """
    if width_deg <= 0:
        raise ValueError("width_deg must be > 0")
    center = bearing_deg(a, b)
    half = width_deg / 2.0
    start = (center - half) % 360.0
    end = (center + half) % 360.0
    return (start, end)

def geodesic_midpoint(a: PointLike, b: PointLike) -> tuple[float, float]:
    """
    Ellipsoidal midpoint using GeographicLib (WGS84).
    Requires: geographiclib
    """
    try:
        from geographiclib.geodesic import Geodesic  # type: ignore
    except Exception as e:
        raise MissingDependencyError(
            "geodesic midpoint requires 'geographiclib' (pip install geographiclib)"
        ) from e

    lat1, lon1 = _resolve_point(a)
    lat2, lon2 = _resolve_point(b)

    line = Geodesic.WGS84.InverseLine(lat1, lon1, lat2, lon2)
    # Total distance in meters along the geodesic:
    s_total = line.s13
    pos = line.Position(s_total / 2.0, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
    return (float(pos["lat2"]), _normalize_lon(float(pos["lon2"])))
