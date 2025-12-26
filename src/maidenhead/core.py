# maidenhead/core.py
from __future__ import annotations

import math
from typing import Callable, Iterable, Iterator, List, Literal, Sequence, Tuple, Union, overload

from . import constants as C
from .errors import (
    InvalidLocatorError,
    MaidenheadError,
    MissingDependencyError,
    OutOfRangeError,
    PrecisionError,
    require,
)
from .geo import bearing_deg, distance_km
from .mh_types import GridSquare, LocatorLike, validate_precision


def precision_of(locator: str | GridSquare) -> int:
    """Return locator precision (character length)."""
    if isinstance(locator, GridSquare):
        return locator.precision
    if not isinstance(locator, str):
        raise InvalidLocatorError(
            f"locator must be str or GridSquare, got {type(locator).__name__}",
            locator=locator,
        )
    return validate_precision(len(locator))


def _normalize_lon(lon: float) -> float:
    """Normalize longitude to [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _clamp_lat(lat: float) -> float:
    """Clamp latitude to [-90, 90]."""
    return max(C.LAT_MIN_DEG, min(C.LAT_MAX_DEG, lat))


def _coerce_locator_text(locator: str | GridSquare) -> str:
    return locator.locator if isinstance(locator, GridSquare) else locator


def _pair_count(precision: int) -> int:
    return precision // 2


def _decode_letter(ch: str, *, pair_index: int) -> int:
    """
    Decode a letter char to an index for the given pair index.
    Pair 1 is base18 (A-R). Other letter pairs are base24 (a-x).
    """
    if len(ch) != 1:
        raise InvalidLocatorError("internal error: expected single char", ch=ch, pair_index=pair_index)

    if pair_index == 1:
        # Accept either case, but only A-R.
        u = ch.upper()
        require(
            u in C.FIELD_CHARS_UPPER,
            InvalidLocatorError,
            f"invalid field letter: {ch!r}",
            ch=ch,
            pair_index=pair_index,
        )
        return ord(u) - ord("A")

    # Other letter pairs: accept either case, but only a-x/A-X.
    l = ch.lower()
    require(
        l in C.SUBSQUARE_CHARS_LOWER,
        InvalidLocatorError,
        f"invalid letter: {ch!r}",
        ch=ch,
        pair_index=pair_index,
    )
    return ord(l) - ord("a")


def _encode_letter(idx: int, *, pair_index: int) -> str:
    """Encode index to canonical letter for the given pair index."""
    if pair_index == 1:
        require(
            0 <= idx < C.FIELD_BASE,
            InvalidLocatorError,
            "field index out of range",
            idx=idx,
            pair_index=pair_index,
        )
        return chr(ord("A") + idx)
    require(
        0 <= idx < C.SUBSQUARE_BASE,
        InvalidLocatorError,
        "letter index out of range",
        idx=idx,
        pair_index=pair_index,
    )
    return chr(ord("a") + idx)


def _decode_digit(ch: str) -> int:
    if len(ch) != 1:
        raise InvalidLocatorError("internal error: expected single char", ch=ch)
    require(ch in C.DIGIT_CHARS, InvalidLocatorError, f"invalid digit: {ch!r}", ch=ch)
    return ord(ch) - ord("0")


def _encode_digit(idx: int) -> str:
    require(0 <= idx < 10, InvalidLocatorError, "digit index out of range", idx=idx)
    return chr(ord("0") + idx)


def normalize(locator: str) -> str:
    """
    Normalize a Maidenhead locator to canonical casing.

    Canonical casing:
      - Pair 1 letters: uppercase (e.g. IO)
      - Pair 2 digits: unchanged
      - Pair 3+ letters: lowercase (e.g. wm)
      - Pair 4 digits: unchanged
      - Pair 5 letters: lowercase
      - ... etc ...

    Normalization also validates the canonical character ranges:
    A-R for pair1, 0-9 for digit pairs, a-x for other letter pairs.
    """
    require(
        isinstance(locator, str),
        InvalidLocatorError,
        f"locator must be str, got {type(locator).__name__}",
        locator=locator,
    )

    s = locator.strip()
    require(s != "", InvalidLocatorError, "locator is empty", locator=locator)

    p = validate_precision(len(s))
    out_chars: list[str] = []

    for i in range(_pair_count(p)):
        pair_index = i + 1
        a = s[2 * i]
        b = s[2 * i + 1]

        kind = C.pair_kind(pair_index)
        if kind == "letters":
            # Decode validates allowed letters; then we re-encode canonically.
            lon_idx = _decode_letter(a, pair_index=pair_index)
            lat_idx = _decode_letter(b, pair_index=pair_index)
            out_chars.append(_encode_letter(lon_idx, pair_index=pair_index))
            out_chars.append(_encode_letter(lat_idx, pair_index=pair_index))
        else:
            # Digits
            lon_idx = _decode_digit(a)
            lat_idx = _decode_digit(b)
            out_chars.append(_encode_digit(lon_idx))
            out_chars.append(_encode_digit(lat_idx))

    return "".join(out_chars)


def is_valid(locator: str) -> bool:
    """Return True if locator parses and validates."""
    try:
        _ = normalize(locator)
        return True
    except MaidenheadError:
        return False


def parse(locator: str) -> GridSquare:
    """Parse and validate a locator string, returning a GridSquare."""
    norm = normalize(locator)
    return GridSquare(norm)


def format_locator(
    locator: LocatorLike,
    *,
    precision: int,
    mode: Literal["truncate", "center", "error"] = "center",
) -> GridSquare:
    """
    Convert a locator to a target precision.

    mode:
      - "truncate": drop pairs to reach target precision
      - "center": use the locator center to re-encode at target precision
      - "error": raise if precision differs
    """
    s = _coerce_locator_text(locator)
    s = normalize(s)
    p = len(s)
    target = validate_precision(int(precision))

    if target == p:
        return GridSquare(s)

    if mode == "error":
        raise PrecisionError(
            "precision does not match locator",
            precision=target,
            locator_precision=p,
        )

    if target < p:
        if mode not in ("truncate", "center"):
            raise ValueError(f"Unknown mode: {mode!r}")
        return parent(s, precision=target)

    # target > p
    if mode == "truncate":
        raise PrecisionError(
            "cannot truncate to a higher precision",
            precision=target,
            locator_precision=p,
        )
    if mode == "center":
        lat, lon = to_center_latlon(s)
        return from_latlon(lat, lon, precision=target)
    raise ValueError(f"Unknown mode: {mode!r}")


def _decode_indices(locator: str) -> tuple[list[int], list[int]]:
    """
    Decode a canonical (or at least validated) locator into index lists.
    Returns (lon_indices, lat_indices) per pair.
    """
    p = validate_precision(len(locator))
    lon_idx: list[int] = []
    lat_idx: list[int] = []

    for i in range(_pair_count(p)):
        pair_index = i + 1
        a = locator[2 * i]
        b = locator[2 * i + 1]
        kind = C.pair_kind(pair_index)

        if kind == "letters":
            lon_idx.append(_decode_letter(a, pair_index=pair_index))
            lat_idx.append(_decode_letter(b, pair_index=pair_index))
        else:
            lon_idx.append(_decode_digit(a))
            lat_idx.append(_decode_digit(b))

    return lon_idx, lat_idx


def to_bbox(locator: LocatorLike) -> tuple[float, float, float, float]:
    """
    Return bounding box (min_lat, min_lon, max_lat, max_lon) for a locator.
    """
    s = _coerce_locator_text(locator)
    s = normalize(s)

    lon_indices, lat_indices = _decode_indices(s)
    lon_min = C.LON_MIN_DEG
    lat_min = C.LAT_MIN_DEG

    lon_cell = C.LON_SPAN_DEG
    lat_cell = C.LAT_SPAN_DEG

    for i in range(len(lon_indices)):
        pair_index = i + 1
        lon_base, lat_base = C.lon_lat_bases_for_pair(pair_index)

        lon_cell /= lon_base
        lat_cell /= lat_base

        lon_min += lon_indices[i] * lon_cell
        lat_min += lat_indices[i] * lat_cell

    return (lat_min, lon_min, lat_min + lat_cell, lon_min + lon_cell)


def to_bbox_split(
    locator: LocatorLike,
) -> tuple[float, float, float, float] | tuple[tuple[float, float, float, float], tuple[float, float, float, float]] | None:
    """
    Return (west_bbox, east_bbox) if the cell crosses the antimeridian.

    Each bbox is (min_lat, min_lon, max_lat, max_lon). Returns None if no split.
    If only one side is non-degenerate, returns that bbox.
    """
    return split_bbox(to_bbox(locator))


def split_bbox(
    bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | tuple[tuple[float, float, float, float], tuple[float, float, float, float]] | None:
    """
    Split a bbox that crosses the antimeridian into (west, east) bboxes.

    Returns None if the bbox does not cross. Longitudes are normalized to [-180, 180).
    """
    min_lat, min_lon, max_lat, max_lon = bbox
    min_lon = _normalize_lon(min_lon)
    max_lon = _normalize_lon(max_lon)

    if min_lon <= max_lon:
        return None

    west = (min_lat, min_lon, max_lat, C.LON_MAX_DEG)
    east = (min_lat, C.LON_MIN_DEG, max_lat, max_lon)
    has_west = west[1] != west[3]
    has_east = east[1] != east[3]
    if has_west and has_east:
        return (west, east)
    if has_west:
        return west
    if has_east:
        return east
    return None


def split_bbox_list(
    bbox: tuple[float, float, float, float],
) -> list[tuple[float, float, float, float]]:
    """
    Return a list of non-degenerate bboxes after splitting at the antimeridian.
    """
    result = split_bbox(bbox)
    if result is None:
        return []
    if len(result) == 4:
        return [result]
    return list(result)


def contains_point(locator: LocatorLike, lat: float, lon: float) -> bool:
    """
    Return True if a point is within the locator bbox.
    """
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    if min_lat <= lat <= max_lat:
        if min_lon <= max_lon:
            return min_lon <= lon <= max_lon
        # dateline wrap
        return lon >= min_lon or lon <= max_lon
    return False


def intersects_bbox(
    locator: LocatorLike,
    bbox: tuple[float, float, float, float],
) -> bool:
    """
    Return True if locator bbox intersects the given bbox.
    """
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    min_lat_b, min_lon_b, max_lat_b, max_lon_b = bbox

    if max_lat < min_lat_b or max_lat_b < min_lat:
        return False

    def _lon_overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> bool:
        if a_min <= a_max and b_min <= b_max:
            return not (a_max < b_min or b_max < a_min)
        # handle wrap by splitting
        if a_min > a_max:
            return _lon_overlap(a_min, C.LON_MAX_DEG, b_min, b_max) or _lon_overlap(
                C.LON_MIN_DEG, a_max, b_min, b_max
            )
        if b_min > b_max:
            return _lon_overlap(a_min, a_max, b_min, C.LON_MAX_DEG) or _lon_overlap(
                a_min, a_max, C.LON_MIN_DEG, b_max
            )
        return False

    return _lon_overlap(min_lon, max_lon, min_lon_b, max_lon_b)


def intersects_polygon(locator: LocatorLike, polygon: Sequence[tuple[float, float]]) -> bool:
    """
    Return True if locator bbox intersects a polygon (lat, lon tuples).
    """
    if len(polygon) < 3:
        raise ValueError("polygon must have at least 3 points")

    def _wrap_lon_near(lon: float, ref: float) -> float:
        lon = _normalize_lon(lon)
        ref = _normalize_lon(ref)
        diff = lon - ref
        if diff > 180.0:
            return lon - 360.0
        if diff < -180.0:
            return lon + 360.0
        return lon

    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    ref_lon = _normalize_lon((min_lon + max_lon) / 2.0)
    min_lon = _wrap_lon_near(min_lon, ref_lon)
    max_lon = _wrap_lon_near(max_lon, ref_lon)

    poly_wrapped = [(lat, _wrap_lon_near(lon, ref_lon)) for (lat, lon) in polygon]
    poly_lats = [p[0] for p in poly_wrapped]
    poly_lons = [p[1] for p in poly_wrapped]
    poly_bbox = (min(poly_lats), min(poly_lons), max(poly_lats), max(poly_lons))
    if max_lat < poly_bbox[0] or poly_bbox[2] < min_lat:
        return False
    if max_lon < poly_bbox[1] or poly_bbox[3] < min_lon:
        return False

    def _point_in_poly(lat: float, lon: float) -> bool:
        inside = False
        j = len(poly_wrapped) - 1
        for i in range(len(poly_wrapped)):
            lat_i, lon_i = poly_wrapped[i]
            lat_j, lon_j = poly_wrapped[j]
            if ((lon_i > lon) != (lon_j > lon)) and (
                lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i + 1e-15) + lat_i
            ):
                inside = not inside
            j = i
        return inside

    def _wrap_point(lat: float, lon: float) -> tuple[float, float]:
        return (lat, _wrap_lon_near(lon, ref_lon))

    corners_pts = [
        _wrap_point(min_lat, min_lon),
        _wrap_point(min_lat, max_lon),
        _wrap_point(max_lat, max_lon),
        _wrap_point(max_lat, min_lon),
    ]
    if any(_point_in_poly(lat, lon) for lat, lon in corners_pts):
        return True
    if any(
        min_lat <= lat <= max_lat and min_lon <= _wrap_lon_near(lon, ref_lon) <= max_lon
        for lat, lon in polygon
    ):
        return True
    def _segments_intersect(a1, a2, b1, b2) -> bool:
        def _orient(p, q, r):
            return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        def _on_segment(p, q, r):
            return (
                min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
                and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
            )
        o1 = _orient(a1, a2, b1)
        o2 = _orient(a1, a2, b2)
        o3 = _orient(b1, b2, a1)
        o4 = _orient(b1, b2, a2)
        if o1 == 0 and _on_segment(a1, b1, a2):
            return True
        if o2 == 0 and _on_segment(a1, b2, a2):
            return True
        if o3 == 0 and _on_segment(b1, a1, b2):
            return True
        if o4 == 0 and _on_segment(b1, a2, b2):
            return True
        return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)

    bbox_edges = [
        ((min_lat, min_lon), (min_lat, max_lon)),
        ((min_lat, max_lon), (max_lat, max_lon)),
        ((max_lat, max_lon), (max_lat, min_lon)),
        ((max_lat, min_lon), (min_lat, min_lon)),
    ]
    for i in range(len(poly_wrapped)):
        p1 = poly_wrapped[i]
        p2 = poly_wrapped[(i + 1) % len(poly_wrapped)]
        for e1, e2 in bbox_edges:
            if _segments_intersect(p1, p2, e1, e2):
                return True
    return False


def _parse_latlon_text(text: str) -> tuple[float, float] | None:
    if "," not in text:
        return None
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        return None


def _resolve_point_latlon(point: LocatorLike | tuple[float, float]) -> tuple[float, float]:
    if isinstance(point, GridSquare):
        return to_center_latlon(point)
    if isinstance(point, str):
        latlon = _parse_latlon_text(point)
        if latlon is not None:
            return latlon
        return to_center_latlon(point)
    if (
        isinstance(point, tuple)
        and len(point) == 2
        and isinstance(point[0], (int, float))
        and isinstance(point[1], (int, float))
    ):
        return (float(point[0]), float(point[1]))
    raise InvalidLocatorError("point must be locator or (lat, lon)", point=point)


def _resolve_geom_input(
    value: LocatorLike | tuple[float, float],
) -> tuple[bool, tuple[float, float, float, float] | None, tuple[float, float] | None]:
    if isinstance(value, tuple) and len(value) == 2:
        lat, lon = value
        return True, None, (float(lat), float(lon))
    if isinstance(value, str):
        latlon = _parse_latlon_text(value)
        if latlon is not None:
            return True, None, latlon
    return False, to_bbox(value), None


def cover_circle(
    center: LocatorLike | tuple[float, float],
    radius_km: float,
    precision: int,
) -> list[GridSquare]:
    """
    Return locators whose bbox intersects a circle.
    """
    lat_c, lon_c = _resolve_point_latlon(center)
    radius_km = float(radius_km)
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0")

    lat_deg = radius_km / 111.32
    cos_lat = math.cos(math.radians(lat_c))
    lon_deg = 180.0 if abs(cos_lat) < 1e-12 else radius_km / (111.32 * cos_lat)

    min_lat = max(C.LAT_MIN_DEG, lat_c - lat_deg)
    max_lat = min(C.LAT_MAX_DEG, lat_c + lat_deg)
    min_lon = lon_c - lon_deg
    max_lon = lon_c + lon_deg

    lon_step, lat_step = cell_size(precision)
    lat = min_lat + lat_step / 2.0

    def _lon_ranges(min_l: float, max_l: float) -> list[tuple[float, float]]:
        if min_l <= max_l:
            return [(min_l, max_l)]
        return [(min_l, C.LON_MAX_DEG), (C.LON_MIN_DEG, max_l)]

    ranges = _lon_ranges(min_lon, max_lon)
    out: list[GridSquare] = []
    seen: set[str] = set()
    center_loc = from_latlon(lat_c, lon_c, precision=precision)
    out.append(center_loc)
    seen.add(center_loc.locator)
    while lat <= max_lat:
        for lo_min, lo_max in ranges:
            lon = lo_min + lon_step / 2.0
            while lon <= lo_max:
                loc = from_latlon(lat, lon, precision=precision)
                if loc.locator not in seen:
                    center_lat, center_lon = to_center_latlon(loc)
                    diag = diagonal_km(loc)
                    if distance_km((lat_c, lon_c), (center_lat, center_lon)) <= radius_km + diag / 2.0:
                        out.append(loc)
                        seen.add(loc.locator)
                lon += lon_step
        lat += lat_step
    return out


def _interpolate_greatcircle(
    a: tuple[float, float],
    b: tuple[float, float],
    fraction: float,
) -> tuple[float, float]:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    d = 2.0 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2.0) ** 2
        )
    )
    if d == 0.0:
        return a
    a_coeff = math.sin((1.0 - fraction) * d) / math.sin(d)
    b_coeff = math.sin(fraction * d) / math.sin(d)
    x = a_coeff * math.cos(lat1) * math.cos(lon1) + b_coeff * math.cos(lat2) * math.cos(lon2)
    y = a_coeff * math.cos(lat1) * math.sin(lon1) + b_coeff * math.cos(lat2) * math.sin(lon2)
    z = a_coeff * math.sin(lat1) + b_coeff * math.sin(lat2)
    lat = math.atan2(z, math.sqrt(x * x + y * y))
    lon = math.atan2(y, x)
    return (math.degrees(lat), _normalize_lon(math.degrees(lon)))


def cover_line(
    a: LocatorLike | tuple[float, float],
    b: LocatorLike | tuple[float, float],
    precision: int,
    *,
    method: Literal["geodesic", "greatcircle"] = "greatcircle",
) -> list[GridSquare]:
    """
    Return locators whose center points follow a line between a and b.
    """
    p1 = _resolve_point_latlon(a)
    p2 = _resolve_point_latlon(b)
    precision = validate_precision(int(precision))

    total = distance_km(p1, p2, method="geodesic" if method == "geodesic" else "haversine")
    mid_lat = (p1[0] + p2[0]) / 2.0
    mid_lon = _normalize_lon((p1[1] + p2[1]) / 2.0)
    step = diagonal_km(from_latlon(mid_lat, mid_lon, precision=precision))
    steps = max(1, int(math.ceil(total / max(step, 1e-6))))

    out: list[GridSquare] = []
    seen: set[str] = set()
    if method == "geodesic":
        try:
            from geographiclib.geodesic import Geodesic  # type: ignore
        except Exception as exc:
            raise MissingDependencyError(
                "geodesic line requires 'geographiclib' (pip install geographiclib)"
            ) from exc
        line = Geodesic.WGS84.InverseLine(p1[0], p1[1], p2[0], p2[1])
        for i in range(steps + 1):
            s = (line.s13 * i) / steps
            pos = line.Position(s)
            lat, lon = float(pos["lat2"]), float(pos["lon2"])
            loc = from_latlon(lat, lon, precision=precision)
            if loc.locator not in seen:
                out.append(loc)
                seen.add(loc.locator)
        return out

    for i in range(steps + 1):
        frac = i / steps
        lat, lon = _interpolate_greatcircle(p1, p2, frac)
        loc = from_latlon(lat, lon, precision=precision)
        if loc.locator not in seen:
            out.append(loc)
            seen.add(loc.locator)
    return out


def to_utm_zone(locator: LocatorLike) -> str:
    """
    Return UTM zone string like "33N" based on the locator center.
    """
    lat, lon = to_center_latlon(locator)
    zone = int((lon + 180.0) // 6.0) + 1
    hemisphere = "N" if lat >= 0 else "S"
    return f"{zone}{hemisphere}"


def to_center_latlon(locator: LocatorLike) -> tuple[float, float]:
    """Return (lat, lon) center of a locator cell."""
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    return ((min_lat + max_lat) / 2.0, _normalize_lon((min_lon + max_lon) / 2.0))


def to_geojson_polygon(locator: LocatorLike | tuple[float, float]) -> dict:
    """
    Return a GeoJSON Polygon for the locator cell.
    If input is a lat/lon point, returns a GeoJSON Point.
    """
    is_point, bbox, latlon = _resolve_geom_input(locator)
    if is_point:
        lat, lon = latlon if latlon is not None else (0.0, 0.0)
        return {"type": "Point", "coordinates": [lon, lat]}
    min_lat, min_lon, max_lat, max_lon = bbox if bbox is not None else to_bbox(locator)
    ring = [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def to_geojson_feature(locator: LocatorLike | tuple[float, float], properties: dict | None = None) -> dict:
    """
    Return a GeoJSON Feature for the locator cell.
    """
    return {
        "type": "Feature",
        "geometry": to_geojson_polygon(locator),
        "properties": properties or {},
    }


def to_geojson_feature_collection(
    locators: Sequence[LocatorLike | tuple[float, float]],
    properties_fn: Callable[[LocatorLike | tuple[float, float]], dict] | None = None,
) -> dict:
    """
    Return a GeoJSON FeatureCollection for locators.
    """
    features = []
    for loc in locators:
        props = properties_fn(loc) if properties_fn else None
        features.append(to_geojson_feature(loc, properties=props))
    return {"type": "FeatureCollection", "features": features}


def to_geojson_bbox(locator: LocatorLike | tuple[float, float]) -> list[float]:
    """
    Return GeoJSON bbox array [min_lon, min_lat, max_lon, max_lat].
    """
    is_point, bbox, latlon = _resolve_geom_input(locator)
    if is_point:
        lat, lon = latlon if latlon is not None else (0.0, 0.0)
        return [lon, lat, lon, lat]
    min_lat, min_lon, max_lat, max_lon = bbox if bbox is not None else to_bbox(locator)
    return [min_lon, min_lat, max_lon, max_lat]


def to_geojson_envelope(locator: LocatorLike | tuple[float, float]) -> dict:
    """
    Return a GeoJSON Polygon using the bbox envelope.
    """
    bbox = to_geojson_bbox(locator)
    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon == max_lon and min_lat == max_lat:
        return {"type": "Point", "coordinates": [min_lon, min_lat], "bbox": bbox}
    ring = [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring], "bbox": bbox}

def to_wkt(locator: LocatorLike | tuple[float, float]) -> str:
    """
    Return a WKT Polygon string for the locator cell.
    If input is a lat/lon point, returns a WKT POINT.
    """
    is_point, bbox, latlon = _resolve_geom_input(locator)
    if is_point:
        lat, lon = latlon if latlon is not None else (0.0, 0.0)
        return f"POINT({lon} {lat})"
    min_lat, min_lon, max_lat, max_lon = bbox if bbox is not None else to_bbox(locator)
    ring = [
        (min_lon, min_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
        (min_lon, max_lat),
        (min_lon, min_lat),
    ]
    coords = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    return f"POLYGON(({coords}))"


def corners(
    locator: LocatorLike,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    """
    Return (nw, ne, sw, se) corners as (lat, lon) pairs.
    """
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    return (
        (max_lat, min_lon),
        (max_lat, max_lon),
        (min_lat, min_lon),
        (min_lat, max_lon),
    )


@overload
def azimuth(
    locator_a: LocatorLike,
    locator_b: LocatorLike,
    *,
    range_mode: Literal[False] = False,
) -> tuple[float, float]: ...


@overload
def azimuth(
    locator_a: LocatorLike,
    locator_b: LocatorLike,
    *,
    range_mode: Literal[True],
) -> tuple[float, float, float]: ...


def azimuth(
    locator_a: LocatorLike,
    locator_b: LocatorLike,
    *,
    range_mode: bool = False,
) -> tuple[float, float] | tuple[float, float, float]:
    """
    Return (bearing_deg, distance_km) from center of locator_a to locator_b.

    If range_mode=True, return (bearing_deg, min_distance_km, max_distance_km)
    using all corner-to-corner distances.
    """
    lat_a, lon_a = to_center_latlon(locator_a)
    lat_b, lon_b = to_center_latlon(locator_b)
    bearing = bearing_deg((lat_a, lon_a), (lat_b, lon_b))
    center_distance = distance_km((lat_a, lon_a), (lat_b, lon_b))

    if not range_mode:
        return (bearing, center_distance)

    corners_a = corners(locator_a)
    corners_b = corners(locator_b)
    distances = [distance_km(a, b) for a in corners_a for b in corners_b]
    return (bearing, min(distances), max(distances))


def initial_bearing(locator_a: LocatorLike, locator_b: LocatorLike) -> float:
    """
    Return initial bearing (deg) from center of locator_a to locator_b.
    """
    lat_a, lon_a = to_center_latlon(locator_a)
    lat_b, lon_b = to_center_latlon(locator_b)
    return bearing_deg((lat_a, lon_a), (lat_b, lon_b))


def cell_size(
    locator_or_precision: LocatorLike | int,
    *,
    unit: Literal["deg", "km", "miles"] = "deg",
    at_lat: float | None = None,
    method: Literal["spherical", "geodesic"] = "spherical",
) -> tuple[float, float]:
    """
    Return (width, height) of a cell for the given locator or precision.

    - unit="deg" returns degree spans (lon, lat).
    - unit="km"/"miles" uses the locator center for distance conversion.
    """
    if isinstance(locator_or_precision, int):
        precision = validate_precision(locator_or_precision)
        if unit != "deg":
            raise ValueError("unit must be 'deg' when using precision only")
        step = C.step_size_for_pair(_pair_count(precision))
        return (step.lon_step_deg, step.lat_step_deg)

    precision = precision_of(locator_or_precision)
    step = C.step_size_for_pair(_pair_count(precision))
    if unit == "deg":
        return (step.lon_step_deg, step.lat_step_deg)

    if method not in ("spherical", "geodesic"):
        raise ValueError(f"Unknown method: {method!r}")
    if at_lat is None:
        at_lat = to_center_latlon(locator_or_precision)[0]
    lat, lon = to_center_latlon(locator_or_precision)
    half_lon = step.lon_step_deg / 2.0
    half_lat = step.lat_step_deg / 2.0
    method_km = "geodesic" if method == "geodesic" else "haversine"
    width_km = distance_km((at_lat, lon - half_lon), (at_lat, lon + half_lon), method=method_km)
    height_km = distance_km((lat - half_lat, lon), (lat + half_lat, lon), method=method_km)

    if unit == "km":
        return (width_km, height_km)
    if unit == "miles":
        miles_per_km = 0.621371
        return (width_km * miles_per_km, height_km * miles_per_km)
    raise ValueError(f"Unknown unit: {unit!r}")


def cell_size_deg(locator: LocatorLike) -> tuple[float, float]:
    """Return (lon_deg, lat_deg) for the locator cell."""
    return cell_size(locator, unit="deg")

def area_km2(
    locator: LocatorLike,
    *,
    method: Literal["spherical", "geodesic"] = "spherical",
) -> float:
    """
    Return approximate area in square kilometers.
    """
    if method == "spherical":
        width_km, height_km = cell_size(locator, unit="km")
        return width_km * height_km
    if method == "geodesic":
        try:
            from geographiclib.geodesic import Geodesic  # type: ignore
        except Exception as exc:
            raise MissingDependencyError(
                "geodesic area requires 'geographiclib' (pip install geographiclib)"
            ) from exc

        min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
        poly = Geodesic.WGS84.Polygon()
        for lat, lon in [
            (min_lat, min_lon),
            (min_lat, max_lon),
            (max_lat, max_lon),
            (max_lat, min_lon),
        ]:
            poly.AddPoint(lat, lon)
        _, _, area = poly.Compute()
        return abs(area) / 1_000_000.0
    raise ValueError(f"Unknown method: {method!r}")


def diagonal_km(
    locator: LocatorLike,
    *,
    method: Literal["spherical", "geodesic"] = "spherical",
) -> float:
    """
    Return diagonal distance (SW to NE) in kilometers.
    """
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    method_km = "geodesic" if method == "geodesic" else "haversine"
    return distance_km((min_lat, min_lon), (max_lat, max_lon), method=method_km)


def from_latlon(
    lat: float,
    lon: float,
    *,
    precision: int = 6,
    clamp: bool = True,
    resolution_deg: float | tuple[float, float] | None = None,
) -> GridSquare:
    """
    Convert lat/lon to a Maidenhead locator at given precision.

    - precision is the locator length (2,4,6,8,10)
    - if lat/lon precision is too coarse, precision is reduced to fit
      (set resolution_deg to enable this fallback)
    - clamp=True prevents boundary issues at exactly 90/180 by nudging inward
    """
    if isinstance(precision, bool):
        raise PrecisionError("precision must be an integer", precision=precision)
    if isinstance(precision, float):
        if not precision.is_integer():
            raise PrecisionError("precision must be an integer", precision=precision)
        precision = int(precision)
    elif isinstance(precision, str):
        if not precision.isdigit():
            raise PrecisionError("precision must be an integer", precision=precision)
        precision = int(precision)
    elif not isinstance(precision, int):
        raise PrecisionError("precision must be an integer", precision=precision)

    require(
        precision in (2, 4, 6, 8, 10),
        PrecisionError,
        "precision must be one of 2, 4, 6, 8, 10",
        precision=precision,
    )
    precision = validate_precision(precision)
    require(isinstance(lat, (int, float)), OutOfRangeError, "lat must be a number", lat=lat)
    require(isinstance(lon, (int, float)), OutOfRangeError, "lon must be a number", lon=lon)

    latf = float(lat)
    lonf = float(lon)

    if resolution_deg is not None:
        if isinstance(resolution_deg, tuple):
            require(
                len(resolution_deg) == 2,
                OutOfRangeError,
                "resolution_deg must be a float or (lat_deg, lon_deg) tuple",
                resolution_deg=resolution_deg,
            )
            lat_res, lon_res = resolution_deg
        else:
            lat_res = resolution_deg
            lon_res = resolution_deg
        require(
            isinstance(lat_res, (int, float)) and isinstance(lon_res, (int, float)),
            OutOfRangeError,
            "resolution_deg must be numeric",
            resolution_deg=resolution_deg,
        )
        lat_res = float(lat_res)
        lon_res = float(lon_res)
        require(
            lat_res > 0 and lon_res > 0,
            OutOfRangeError,
            "resolution_deg must be > 0",
            resolution_deg=resolution_deg,
        )

        for candidate in [p for p in (8, 6, 4, 2) if p <= precision]:
            step = C.step_size_for_pair(_pair_count(candidate))
            if lat_res <= step.lat_step_deg and lon_res <= step.lon_step_deg:
                precision = candidate
                break

    if clamp:
        # Normalize lon into [-180,180), clamp lat into [-90,90],
        # then nudge off exact upper boundaries to avoid overflow.
        lonf = _normalize_lon(lonf)
        latf = _clamp_lat(latf)

        if lonf >= C.LON_MAX_DEG:
            lonf = C.LON_MAX_DEG - C.CLAMP_EPS_DEG
        if latf >= C.LAT_MAX_DEG:
            latf = C.LAT_MAX_DEG - C.CLAMP_EPS_DEG
        if lonf <= C.LON_MIN_DEG:
            lonf = C.LON_MIN_DEG + C.CLAMP_EPS_DEG
        if latf <= C.LAT_MIN_DEG:
            latf = C.LAT_MIN_DEG + C.CLAMP_EPS_DEG
    else:
        require(
            C.LAT_MIN_DEG <= latf <= C.LAT_MAX_DEG,
            OutOfRangeError,
            "lat out of range [-90, 90]",
            lat=latf,
        )
        # Accept lon in a wider range, but normalize to compute.
        lonf = _normalize_lon(lonf)

    # Convert to offsets in [0, span)
    x = lonf - C.LON_MIN_DEG  # lon + 180
    y = latf - C.LAT_MIN_DEG  # lat + 90

    lon_cell = C.LON_SPAN_DEG
    lat_cell = C.LAT_SPAN_DEG

    out: list[str] = []
    for i in range(_pair_count(precision)):
        pair_index = i + 1
        lon_base, lat_base = C.lon_lat_bases_for_pair(pair_index)

        lon_cell /= lon_base
        lat_cell /= lat_base

        lon_i = int(math.floor(x / lon_cell))
        lat_i = int(math.floor(y / lat_cell))

        # Safety clamp against tiny numeric overflows
        lon_i = min(max(lon_i, 0), lon_base - 1)
        lat_i = min(max(lat_i, 0), lat_base - 1)

        x -= lon_i * lon_cell
        y -= lat_i * lat_cell

        if C.pair_kind(pair_index) == "letters":
            out.append(_encode_letter(lon_i, pair_index=pair_index))
            out.append(_encode_letter(lat_i, pair_index=pair_index))
        else:
            out.append(_encode_digit(lon_i))
            out.append(_encode_digit(lat_i))

    return GridSquare("".join(out))


def parent(locator: LocatorLike, *, precision: int | None = None) -> GridSquare:
    """
    Return a less-precise parent locator.

    If precision is None, drops one pair (e.g. 6->4, 4->2).
    """
    s = _coerce_locator_text(locator)
    s = normalize(s)
    p = len(s)

    if precision is None:
        require(p > 2, PrecisionError, "cannot parent a 2-character locator", precision=p)
        new_p = p - 2
    else:
        new_p = validate_precision(int(precision))
        require(
            new_p < p,
            PrecisionError,
            "parent precision must be less than locator precision",
            precision=new_p,
            locator_precision=p,
        )

    return GridSquare(s[:new_p])


def children(locator: LocatorLike, *, precision: int) -> Iterable[GridSquare]:
    """
    Yield child locators at a finer precision.

    Note: expanding multiple levels can be huge; this is intentionally an iterator.
    """
    s = _coerce_locator_text(locator)
    s = normalize(s)
    p0 = len(s)
    p1 = validate_precision(int(precision))

    require(
        p1 > p0,
        PrecisionError,
        "child precision must be greater than locator precision",
        precision=p1,
        locator_precision=p0,
    )

    start_pairs = _pair_count(p0)
    end_pairs = _pair_count(p1)

    def _gen(prefix: str, pair_index: int) -> Iterator[str]:
        if pair_index > end_pairs:
            yield prefix
            return

        lon_base, lat_base = C.lon_lat_bases_for_pair(pair_index)
        if C.pair_kind(pair_index) == "letters":
            for lon_i in range(lon_base):
                for lat_i in range(lat_base):
                    yield from _gen(
                        prefix + _encode_letter(lon_i, pair_index=pair_index) + _encode_letter(lat_i, pair_index=pair_index),
                        pair_index + 1,
                    )
        else:
            for lon_i in range(lon_base):
                for lat_i in range(lat_base):
                    yield from _gen(prefix + _encode_digit(lon_i) + _encode_digit(lat_i), pair_index + 1)

    # We start generating at the first missing pair.
    first_missing_pair = start_pairs + 1
    for loc in _gen(s, first_missing_pair):
        yield GridSquare(loc)


def neighbors(locator: LocatorLike, *, ring: int = 1, diagonals: bool = True) -> list[GridSquare]:
    """
    Return neighboring cells at the same precision.

    Implementation is robust (works across carries) by stepping in degrees from
    the cell center and re-encoding at the same precision.

    Note: near the poles, latitude clamping can cause distinct offsets to map
    to the same cell; duplicates are deduplicated in the output.
    """
    require(isinstance(ring, int) and ring >= 1, ValueError, "ring must be an integer >= 1", ring=ring)

    s = _coerce_locator_text(locator)
    s = normalize(s)
    p = len(s)

    min_lat, min_lon, max_lat, max_lon = to_bbox(s)
    dlat = (max_lat - min_lat)
    dlon = (max_lon - min_lon)
    clat, clon = to_center_latlon(s)

    out: list[GridSquare] = []
    for dy in range(-ring, ring + 1):
        for dx in range(-ring, ring + 1):
            if dx == 0 and dy == 0:
                continue
            if not diagonals and (dx != 0 and dy != 0):
                continue

            lat2 = clat + dy * dlat
            lon2 = _normalize_lon(clon + dx * dlon)

            # Clamp latitude; longitudes wrap naturally.
            lat2 = _clamp_lat(lat2)
            out.append(from_latlon(lat2, lon2, precision=p, clamp=True))

    # Deduplicate in case clamping collapses distinct neighbors near poles.
    # Preserve order.
    seen: set[str] = set()
    uniq: list[GridSquare] = []
    for g in out:
        if g.locator not in seen:
            seen.add(g.locator)
            uniq.append(g)
    return uniq


def adjacent(locator: LocatorLike, *, diagonals: bool = False) -> dict[str, GridSquare]:
    """
    Return adjacent cells at the same precision keyed by direction.

    By default returns cardinal neighbors (N, S, E, W). If diagonals=True,
    includes NE, NW, SE, SW.
    """
    s = _coerce_locator_text(locator)
    s = normalize(s)
    p = len(s)

    min_lat, min_lon, max_lat, max_lon = to_bbox(s)
    dlat = (max_lat - min_lat)
    dlon = (max_lon - min_lon)
    clat, clon = to_center_latlon(s)

    directions: list[tuple[str, int, int]] = [
        ("N", 1, 0),
        ("S", -1, 0),
        ("E", 0, 1),
        ("W", 0, -1),
    ]
    if diagonals:
        directions.extend(
            [
                ("NE", 1, 1),
                ("NW", 1, -1),
                ("SE", -1, 1),
                ("SW", -1, -1),
            ]
        )

    out: dict[str, GridSquare] = {}
    for key, dy, dx in directions:
        lat2 = clat + dy * dlat
        lon2 = _normalize_lon(clon + dx * dlon)
        lat2 = _clamp_lat(lat2)
        out[key] = from_latlon(lat2, lon2, precision=p, clamp=True)

    return out


def step(locator: LocatorLike, *, dlat_cells: int = 0, dlon_cells: int = 0) -> GridSquare:
    """
    Move by a number of cells in latitude/longitude directions.

    Positive dlat_cells moves north, positive dlon_cells moves east.
    """
    require(isinstance(dlat_cells, int), ValueError, "dlat_cells must be int", dlat_cells=dlat_cells)
    require(isinstance(dlon_cells, int), ValueError, "dlon_cells must be int", dlon_cells=dlon_cells)

    s = _coerce_locator_text(locator)
    s = normalize(s)
    p = len(s)

    min_lat, min_lon, max_lat, max_lon = to_bbox(s)
    dlat = (max_lat - min_lat)
    dlon = (max_lon - min_lon)
    clat, clon = to_center_latlon(s)

    lat2 = clat + dlat_cells * dlat
    lon2 = _normalize_lon(clon + dlon_cells * dlon)
    lat2 = _clamp_lat(lat2)
    return from_latlon(lat2, lon2, precision=p, clamp=True)


def contains(outer: LocatorLike, inner: LocatorLike) -> bool:
    """
    Return True if inner's cell is fully within outer's cell.
    """
    def _parts(bbox: tuple[float, float, float, float]) -> list[tuple[float, float, float, float]]:
        parts = split_bbox_list(bbox)
        return parts if parts else [bbox]

    def _contains_bbox(
        outer_bbox: tuple[float, float, float, float],
        inner_bbox: tuple[float, float, float, float],
    ) -> bool:
        min_lat_o, min_lon_o, max_lat_o, max_lon_o = outer_bbox
        min_lat_i, min_lon_i, max_lat_i, max_lon_i = inner_bbox
        return (
            min_lat_o <= min_lat_i
            and max_lat_o >= max_lat_i
            and min_lon_o <= min_lon_i
            and max_lon_o >= max_lon_i
        )

    outer_parts = _parts(to_bbox(outer))
    inner_parts = _parts(to_bbox(inner))
    for inner_part in inner_parts:
        if not any(_contains_bbox(outer_part, inner_part) for outer_part in outer_parts):
            return False
    return True
