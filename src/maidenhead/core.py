# maidenhead/core.py
from __future__ import annotations

import math
from typing import Iterable, Iterator, List, Sequence, Tuple, Union, overload

from . import constants as C
from .errors import InvalidLocatorError, OutOfRangeError, PrecisionError, require
from .mh_types import GridSquare, LocatorLike, validate_precision


def precision_of(locator: str | GridSquare) -> int:
    """Return locator precision (character length)."""
    if isinstance(locator, GridSquare):
        return locator.precision
    if not isinstance(locator, str):
        raise InvalidLocatorError(f"locator must be str or GridSquare, got {type(locator).__name__}")
    return validate_precision(len(locator))


def _normalize_lon(lon: float) -> float:
    """Normalize longitude to [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _clamp_lat(lat: float) -> float:
    """Clamp latitude to [-90, 90]."""
    return max(C.LAT_MIN_DEG, min(C.LAT_MAX_DEG, lat))


def _coerce_locator_text(locator: str | GridSquare) -> str:
    return locator.locator if isinstance(locator, GridSquare) else locator


def _check_allow_extended(p: int, allow_extended: bool) -> None:
    if not allow_extended:
        require(p <= 6, PrecisionError, "extended Maidenhead locators are disabled (max precision=6)")


def _pair_count(precision: int) -> int:
    return precision // 2


def _decode_letter(ch: str, *, pair_index: int) -> int:
    """
    Decode a letter char to an index for the given pair index.
    Pair 1 is base18 (A-R). Other letter pairs are base24 (a-x).
    """
    if len(ch) != 1:
        raise InvalidLocatorError("internal error: expected single char")

    if pair_index == 1:
        # Accept either case, but only A-R.
        u = ch.upper()
        require(u in C.FIELD_CHARS_UPPER, InvalidLocatorError, f"invalid field letter: {ch!r}")
        return ord(u) - ord("A")

    # Other letter pairs: accept either case, but only a-x/A-X.
    l = ch.lower()
    require(l in C.SUBSQUARE_CHARS_LOWER, InvalidLocatorError, f"invalid letter: {ch!r}")
    return ord(l) - ord("a")


def _encode_letter(idx: int, *, pair_index: int) -> str:
    """Encode index to canonical letter for the given pair index."""
    if pair_index == 1:
        require(0 <= idx < C.FIELD_BASE, InvalidLocatorError, "field index out of range")
        return chr(ord("A") + idx)
    require(0 <= idx < C.SUBSQUARE_BASE, InvalidLocatorError, "letter index out of range")
    return chr(ord("a") + idx)


def _decode_digit(ch: str) -> int:
    if len(ch) != 1:
        raise InvalidLocatorError("internal error: expected single char")
    require(ch in C.DIGIT_CHARS, InvalidLocatorError, f"invalid digit: {ch!r}")
    return ord(ch) - ord("0")


def _encode_digit(idx: int) -> str:
    require(0 <= idx < 10, InvalidLocatorError, "digit index out of range")
    return chr(ord("0") + idx)


def normalize(locator: str, *, allow_extended: bool = True, strict: bool = False) -> str:
    """
    Normalize a Maidenhead locator to canonical casing.

    Canonical casing:
      - Pair 1 letters: uppercase (e.g. IO)
      - Pair 2 digits: unchanged
      - Pair 3+ letters: lowercase (e.g. wm)
      - Pair 4 digits: unchanged
      - Pair 5 letters: lowercase
      - ... etc ...

    strict currently controls whether we reject any characters outside the canonical
    ranges (A-R for pair1, 0-9 for digit pairs, a-x for other letter pairs). Case
    is normalized regardless.
    """
    require(isinstance(locator, str), InvalidLocatorError, f"locator must be str, got {type(locator).__name__}")

    s = locator.strip()
    require(s != "", InvalidLocatorError, "locator is empty")

    p = validate_precision(len(s))
    _check_allow_extended(p, allow_extended)

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


def is_valid(locator: str, *, allow_extended: bool = True) -> bool:
    """Return True if locator parses and validates."""
    try:
        _ = normalize(locator, allow_extended=allow_extended, strict=True)
        return True
    except Exception:
        return False


def parse(locator: str, *, allow_extended: bool = True) -> GridSquare:
    """Parse and validate a locator string, returning a GridSquare."""
    norm = normalize(locator, allow_extended=allow_extended, strict=True)
    return GridSquare(norm)


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
    s = normalize(s, allow_extended=True, strict=True)

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


def to_center_latlon(locator: LocatorLike) -> tuple[float, float]:
    """Return (lat, lon) center of a locator cell."""
    min_lat, min_lon, max_lat, max_lon = to_bbox(locator)
    return ((min_lat + max_lat) / 2.0, _normalize_lon((min_lon + max_lon) / 2.0))


def from_latlon(
    lat: float,
    lon: float,
    *,
    precision: int = 6,
    clamp: bool = True,
    allow_extended: bool = True,
) -> GridSquare:
    """
    Convert lat/lon to a Maidenhead locator at given precision.

    - precision is the locator length (2,4,6,8,...)
    - clamp=True prevents boundary issues at exactly 90/180 by nudging inward
    """
    precision = validate_precision(precision)
    _check_allow_extended(precision, allow_extended)

    require(isinstance(lat, (int, float)), OutOfRangeError, "lat must be a number")
    require(isinstance(lon, (int, float)), OutOfRangeError, "lon must be a number")

    latf = float(lat)
    lonf = float(lon)

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
        require(C.LAT_MIN_DEG <= latf <= C.LAT_MAX_DEG, OutOfRangeError, "lat out of range [-90, 90]")
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
    s = normalize(s, allow_extended=True, strict=True)
    p = len(s)

    if precision is None:
        require(p > 2, PrecisionError, "cannot parent a 2-character locator")
        new_p = p - 2
    else:
        new_p = validate_precision(int(precision))
        require(new_p < p, PrecisionError, "parent precision must be less than locator precision")

    return GridSquare(s[:new_p])


def children(locator: LocatorLike, *, precision: int) -> Iterable[GridSquare]:
    """
    Yield child locators at a finer precision.

    Note: expanding multiple levels can be huge; this is intentionally an iterator.
    """
    s = _coerce_locator_text(locator)
    s = normalize(s, allow_extended=True, strict=True)
    p0 = len(s)
    p1 = validate_precision(int(precision))

    require(p1 > p0, PrecisionError, "child precision must be greater than locator precision")

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
    """
    require(isinstance(ring, int) and ring >= 1, ValueError, "ring must be an integer >= 1")

    s = _coerce_locator_text(locator)
    s = normalize(s, allow_extended=True, strict=True)
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
            out.append(from_latlon(lat2, lon2, precision=p, clamp=True, allow_extended=True))

    # Deduplicate in case clamping collapses distinct neighbors near poles.
    # Preserve order.
    seen: set[str] = set()
    uniq: list[GridSquare] = []
    for g in out:
        if g.locator not in seen:
            seen.add(g.locator)
            uniq.append(g)
    return uniq
