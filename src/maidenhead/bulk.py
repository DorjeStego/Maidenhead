# maidenhead/bulk.py
from __future__ import annotations

from typing import Iterable, Sequence

from .core import cell_size, from_latlon, normalize, to_bbox, to_center_latlon
from .errors import OutOfRangeError, require
from .mh_types import LocatorLike


def _require_same_length(a: Sequence[float], b: Sequence[float]) -> None:
    require(
        len(a) == len(b),
        OutOfRangeError,
        "lat and lon sequences must be the same length",
        lat_len=len(a),
        lon_len=len(b),
    )


def normalize_many(locators: Iterable[LocatorLike]) -> list[str]:
    return [normalize(loc) for loc in locators]


def from_latlon_many(
    lats: Sequence[float],
    lons: Sequence[float],
    *,
    precision: int = 6,
    clamp: bool = True,
) -> list[str]:
    _require_same_length(lats, lons)
    return [
        from_latlon(lat, lon, precision=precision, clamp=clamp).locator
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


def cell_size_many(
    locators: Iterable[LocatorLike],
    *,
    unit: str = "deg",
) -> tuple[list[float], list[float]]:
    widths: list[float] = []
    heights: list[float] = []
    for loc in locators:
        width, height = cell_size(loc, unit=unit)
        widths.append(width)
        heights.append(height)
    return (widths, heights)
