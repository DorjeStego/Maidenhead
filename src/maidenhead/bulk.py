# maidenhead/bulk.py
from __future__ import annotations

from typing import Iterable, Sequence

from .core import (
    area_km2,
    azimuth,
    cell_size,
    cell_size_deg,
    children,
    contains,
    contains_point,
    corners,
    diagonal_km,
    from_latlon,
    neighbors,
    normalize,
    parent,
    parse,
    precision_of,
    split_bbox_list,
    to_bbox,
    to_center_latlon,
    to_wkt,
    adjacent,
    intersects_bbox,
    intersects_polygon,
    initial_bearing,
    to_geojson_bbox,
    to_geojson_envelope,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_polygon,
    to_utm_zone,
)
from .errors import OutOfRangeError, require
from .mh_types import GridSquare, LocatorLike


def _require_same_length(a: Sequence[float], b: Sequence[float]) -> None:
    require(
        len(a) == len(b),
        OutOfRangeError,
        "lat and lon sequences must be the same length",
        lat_len=len(a),
        lon_len=len(b),
    )


def _coerce_locator_text(locator: LocatorLike) -> str:
    return locator.locator if isinstance(locator, GridSquare) else locator


def normalize_many(locators: Iterable[LocatorLike]) -> list[str]:
    return [normalize(_coerce_locator_text(loc)) for loc in locators]


def from_latlon_many(
    lats: Sequence[float],
    lons: Sequence[float],
    *,
    precision: int = 6,
    clamp: bool = True,
    resolution_deg: float | tuple[float, float] | None = None,
) -> list[str]:
    _require_same_length(lats, lons)
    return [
        from_latlon(lat, lon, precision=precision, clamp=clamp, resolution_deg=resolution_deg).locator
        for lat, lon in zip(lats, lons)
    ]


def to_center_many(locators: Iterable[LocatorLike]) -> tuple[list[float], list[float]]:
    lats: list[float] = []
    lons: list[float] = []
    for loc in locators:
        lat, lon = to_center_latlon(loc)
        lats.append(lat)
        lons.append(lon)
    return (lats, lons)


def to_bbox_many(
    locators: Iterable[LocatorLike],
) -> tuple[list[float], list[float], list[float], list[float]]:
    min_lats: list[float] = []
    min_lons: list[float] = []
    max_lats: list[float] = []
    max_lons: list[float] = []
    for loc in locators:
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        min_lats.append(min_lat)
        min_lons.append(min_lon)
        max_lats.append(max_lat)
        max_lons.append(max_lon)
    return (min_lats, min_lons, max_lats, max_lons)


def cell_size_deg_many(
    locators: Iterable[LocatorLike],
) -> tuple[list[float], list[float]]:
    widths: list[float] = []
    heights: list[float] = []
    for loc in locators:
        width, height = cell_size_deg(loc)
        widths.append(width)
        heights.append(height)
    return (widths, heights)


def cell_size_km_many(
    locators: Iterable[LocatorLike],
    *,
    at_lat: float | None = None,
    method: str = "spherical",
) -> tuple[list[float], list[float]]:
    widths: list[float] = []
    heights: list[float] = []
    for loc in locators:
        width, height = cell_size(loc, unit="km", at_lat=at_lat, method=method)
        widths.append(width)
        heights.append(height)
    return (widths, heights)


def cell_size_many(
    locators: Iterable[LocatorLike],
    *,
    unit: str = "deg",
    at_lat: float | None = None,
    method: str = "spherical",
) -> tuple[list[float], list[float]]:
    if unit == "deg":
        return cell_size_deg_many(locators)
    if unit == "km":
        return cell_size_km_many(locators, at_lat=at_lat, method=method)
    if unit == "miles":
        widths, heights = cell_size_km_many(locators, at_lat=at_lat, method=method)
        miles_per_km = 0.621371
        return ([w * miles_per_km for w in widths], [h * miles_per_km for h in heights])
    raise ValueError(f"Unknown unit: {unit!r}")


def area_km2_many(
    locators: Iterable[LocatorLike],
    *,
    method: str = "spherical",
) -> list[float]:
    return [area_km2(loc, method=method) for loc in locators]


def diagonal_km_many(
    locators: Iterable[LocatorLike],
    *,
    method: str = "spherical",
) -> list[float]:
    return [diagonal_km(loc, method=method) for loc in locators]


def parent_many(
    locators: Iterable[LocatorLike],
    *,
    precision: int | None = None,
) -> list[str]:
    out: list[str] = []
    for loc in locators:
        if precision is None:
            out.append(parent(loc).locator)
        else:
            out.append(parent(loc, precision=precision).locator)
    return out


def children_many(
    locators: Iterable[LocatorLike],
    *,
    precision: int | None = None,
    limit: int | None = None,
) -> list[list[str]]:
    out: list[list[str]] = []
    for loc in locators:
        if precision is None:
            precision_value = parse(loc).precision + 2
        else:
            precision_value = precision
        items = list(children(loc, precision=precision_value))
        if limit is not None:
            items = items[:limit]
        out.append([g.locator for g in items])
    return out


def to_wkt_many(locators: Iterable[LocatorLike]) -> list[str]:
    return [to_wkt(loc) for loc in locators]


def azimuth_many(
    points_a: Sequence[LocatorLike | tuple[float, float]],
    points_b: Sequence[LocatorLike | tuple[float, float]],
    *,
    range_mode: bool = False,
) -> list[tuple[float, float] | tuple[float, float, float]]:
    _require_same_length(points_a, points_b)
    return [
        azimuth(a, b, range_mode=range_mode)
        for a, b in zip(points_a, points_b)
    ]


def contains_point_many(
    locators: Sequence[LocatorLike],
    lats: Sequence[float],
    lons: Sequence[float],
) -> list[bool]:
    _require_same_length(locators, lats)
    _require_same_length(locators, lons)
    return [contains_point(loc, lat, lon) for loc, lat, lon in zip(locators, lats, lons)]


def contains_many(
    outers: Sequence[LocatorLike],
    inners: Sequence[LocatorLike],
) -> list[bool]:
    _require_same_length(outers, inners)
    return [contains(outer, inner) for outer, inner in zip(outers, inners)]


def corners_many(
    locators: Iterable[LocatorLike],
    *,
    return_type: str = "list",
) -> list[list[tuple[float, float]]] | tuple[
    list[tuple[float, float]],
    list[tuple[float, float]],
    list[tuple[float, float]],
    list[tuple[float, float]],
]:
    if return_type not in ("list", "tuple"):
        raise ValueError("return_type must be 'list' or 'tuple'")
    if return_type == "tuple":
        nws: list[tuple[float, float]] = []
        nes: list[tuple[float, float]] = []
        sws: list[tuple[float, float]] = []
        ses: list[tuple[float, float]] = []
        for loc in locators:
            nw, ne, sw, se = corners(loc)
            nws.append(nw)
            nes.append(ne)
            sws.append(sw)
            ses.append(se)
        return (nws, nes, sws, ses)
    return [list(corners(loc)) for loc in locators]


def split_bbox_many(
    bboxes: Iterable[tuple[float, float, float, float]],
) -> list[list[tuple[float, float, float, float]]]:
    out: list[list[tuple[float, float, float, float]]] = []
    for bbox in bboxes:
        out.append(split_bbox_list(bbox))
    return out


def neighbors_many(
    locators: Iterable[LocatorLike],
    *,
    ring: int = 1,
    diagonals: bool = True,
) -> list[list[str]]:
    out: list[list[str]] = []
    for loc in locators:
        neigh = neighbors(loc, ring=ring, diagonals=diagonals)
        out.append([g.locator for g in neigh])
    return out


def adjacent_many(
    locators: Iterable[LocatorLike],
    *,
    diagonals: bool = True,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for loc in locators:
        adj = adjacent(loc, diagonals=diagonals)
        out.append({k: v.locator for k, v in adj.items()})
    return out


def precision_many(
    locators: Iterable[LocatorLike],
) -> list[int]:
    return [precision_of(loc) for loc in locators]


def intersects_bbox_many(
    locators: Sequence[LocatorLike],
    bboxes: Sequence[tuple[float, float, float, float]],
) -> list[bool]:
    _require_same_length(locators, bboxes)
    return [intersects_bbox(loc, bbox) for loc, bbox in zip(locators, bboxes)]


def intersects_polygon_many(
    locators: Sequence[LocatorLike],
    polygons: Sequence[Sequence[tuple[float, float]]],
) -> list[bool]:
    _require_same_length(locators, polygons)
    return [intersects_polygon(loc, poly) for loc, poly in zip(locators, polygons)]


def initial_bearing_many(
    locators_a: Sequence[LocatorLike],
    locators_b: Sequence[LocatorLike],
) -> list[float]:
    _require_same_length(locators_a, locators_b)
    return [initial_bearing(a, b) for a, b in zip(locators_a, locators_b)]


def to_utm_zone_many(locators: Iterable[LocatorLike]) -> list[str]:
    return [to_utm_zone(loc) for loc in locators]


def to_geojson_polygon_many(locators: Iterable[LocatorLike]) -> list[dict]:
    return [to_geojson_polygon(loc) for loc in locators]


def to_geojson_feature_many(locators: Iterable[LocatorLike]) -> list[dict]:
    return [to_geojson_feature(loc) for loc in locators]


def to_geojson_feature_collection_many(locators: Iterable[LocatorLike]) -> list[dict]:
    return [to_geojson_feature(loc) for loc in locators]


def to_geojson_bbox_many(locators: Iterable[LocatorLike]) -> list[list[float]]:
    return [to_geojson_bbox(loc) for loc in locators]


def to_geojson_envelope_many(locators: Iterable[LocatorLike]) -> list[dict]:
    return [to_geojson_envelope(loc) for loc in locators]
