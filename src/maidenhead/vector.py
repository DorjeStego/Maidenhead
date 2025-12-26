# maidenhead/vector.py
from __future__ import annotations

from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple, Union, overload

from . import constants as C
from .mh_types import GridSquare, LocatorLike, validate_precision
from .core import (
    azimuth,
    cell_size,
    cell_size_deg,
    cell_size_km,
    from_latlon,
    normalize,
    parse,
    to_bbox,
    to_center_latlon,
    to_geojson_bbox,
    to_geojson_envelope,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_polygon,
    neighbors,
    adjacent,
    corners,
    parent,
    children,
    to_utm_zone,
    intersects_bbox,
    intersects_polygon,
    area_km2,
    diagonal_km,
    to_wkt,
    contains_point,
    contains,
    split_bbox_list,
    precision_of,
    initial_bearing,
)
from .errors import InvalidLocatorError, PrecisionError


# ----------------------------
# Optional dependency helpers
# ----------------------------

def _is_numpy_array(x: Any) -> bool:
    # Avoid importing numpy unless it's actually installed and needed.
    try:
        import numpy as np  # type: ignore
    except Exception:
        return False
    return isinstance(x, np.ndarray)


def _is_pandas_series(x: Any) -> bool:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return False
    return isinstance(x, pd.Series)


def _as_numpy_array(x: Any) -> Any:
    import numpy as np  # type: ignore
    return np.asarray(x)


def _make_numpy_object_array(length: int) -> Any:
    import numpy as np  # type: ignore
    return np.empty(length, dtype=object)


def _make_numpy_float_array(length: int) -> Any:
    import numpy as np  # type: ignore
    return np.empty(length, dtype=float)


def _listify(value: Any) -> list[Any]:
    if _is_pandas_series(value):
        return list(value)
    if isinstance(value, list):
        return value
    return list(value)


def _require_same_length(a: Any, b: Any, *, name_a: str, name_b: str) -> tuple[list[Any], list[Any]]:
    a_list = _listify(a)
    b_list = _listify(b)
    if len(a_list) != len(b_list):
        raise ValueError(f"{name_a} and {name_b} must have the same length")
    return a_list, b_list

def _from_latlon_numpy(lats: Any, lons: Any, *, precision: int) -> Any:
    import numpy as np  # type: ignore
    lats_arr = np.asarray(lats, dtype=float)
    lons_arr = np.asarray(lons, dtype=float)
    if lats_arr.shape != lons_arr.shape:
        raise ValueError("lats and lons must have the same shape")

    # Clamp/normalize like core.from_latlon with clamp=True.
    lons_arr = (lons_arr + 180.0) % 360.0 - 180.0
    lats_arr = np.clip(lats_arr, C.LAT_MIN_DEG, C.LAT_MAX_DEG)
    eps = C.CLAMP_EPS_DEG
    lons_arr = np.where(lons_arr >= C.LON_MAX_DEG, C.LON_MAX_DEG - eps, lons_arr)
    lons_arr = np.where(lons_arr <= C.LON_MIN_DEG, C.LON_MIN_DEG + eps, lons_arr)
    lats_arr = np.where(lats_arr >= C.LAT_MAX_DEG, C.LAT_MAX_DEG - eps, lats_arr)
    lats_arr = np.where(lats_arr <= C.LAT_MIN_DEG, C.LAT_MIN_DEG + eps, lats_arr)

    x = lons_arr - C.LON_MIN_DEG
    y = lats_arr - C.LAT_MIN_DEG

    lon_cell = C.LON_SPAN_DEG
    lat_cell = C.LAT_SPAN_DEG
    out = None
    pair_count = precision // 2

    for i in range(pair_count):
        pair_index = i + 1
        lon_base, lat_base = C.lon_lat_bases_for_pair(pair_index)
        lon_cell /= lon_base
        lat_cell /= lat_base

        lon_i = np.floor(x / lon_cell).astype(int)
        lat_i = np.floor(y / lat_cell).astype(int)
        lon_i = np.clip(lon_i, 0, lon_base - 1)
        lat_i = np.clip(lat_i, 0, lat_base - 1)

        x = x - lon_i * lon_cell
        y = y - lat_i * lat_cell

        if C.pair_kind(pair_index) == "letters":
            if pair_index == 1:
                alphabet = np.array(list(C.FIELD_CHARS_UPPER))
            else:
                alphabet = np.array(list(C.SUBSQUARE_CHARS_LOWER))
            a = alphabet[lon_i]
            b = alphabet[lat_i]
        else:
            digits = np.array(list(C.DIGIT_CHARS))
            a = digits[lon_i]
            b = digits[lat_i]

        if out is None:
            out = np.char.add(a, b)
        else:
            out = np.char.add(out, np.char.add(a, b))

    return out


# ----------------------------
# Core utilities
# ----------------------------

def _iter_pairs(lats: Iterable[float], lons: Iterable[float]) -> Iterator[Tuple[float, float]]:
    it_lat = iter(lats)
    it_lon = iter(lons)
    while True:
        try:
            lat = next(it_lat)
        except StopIteration:
            # Ensure lon is also exhausted (avoid silent truncation).
            try:
                next(it_lon)
                raise ValueError("lats and lons have different lengths")
            except StopIteration:
                return
        try:
            lon = next(it_lon)
        except StopIteration:
            raise ValueError("lats and lons have different lengths")
        yield (float(lat), float(lon))


def _coerce_locator_out(obj: GridSquare) -> str:
    # Vector API returns string locators by default.
    return obj.locator


def _maybe_wrap_series(values: List[Any], like: Any) -> Any:
    if _is_pandas_series(like):
        import pandas as pd  # type: ignore
        return pd.Series(values, index=like.index, name=like.name)
    return values


# ----------------------------
# Public vector API
# ----------------------------

def from_latlon_many(
    lats: Any,
    lons: Any,
    *,
    precision: int = 6,
    return_type: str = "auto",
    resolution_deg: float | tuple[float, float] | None = None,
) -> Any:
    """
    Vectorized Maidenhead conversion: lat/lon -> locator strings.

    Inputs:
      - lats/lons: iterables, numpy arrays, or pandas Series

    return_type:
      - "auto": preserve Series/ndarray where possible, else list[str]
      - "list": always list[str]
      - "numpy": numpy ndarray(dtype=object) (requires numpy)
      - "pandas": pandas Series (requires pandas; index from lats if Series else RangeIndex)
    """
    validate_precision(precision)

    # Pandas Series preservation (if both are Series, we preserve index)
    if return_type == "auto" and _is_pandas_series(lats) and _is_pandas_series(lons):
        if len(lats) != len(lons):
            raise ValueError("lats and lons must have the same length")
        out = [
            _coerce_locator_out(
                from_latlon(lat, lon, precision=precision, resolution_deg=resolution_deg)
            )
            for (lat, lon) in zip(lats.tolist(), lons.tolist())
        ]
        import pandas as pd  # type: ignore
        return pd.Series(out, index=lats.index, name=getattr(lats, "name", None))

    # Numpy arrays preservation
    if return_type == "auto" and _is_numpy_array(lats) and _is_numpy_array(lons):
        if resolution_deg is not None:
            # Fallback precision uses core, so defer to scalar path.
            n = int(len(lats))
            if len(lons) != n:
                raise ValueError("lats and lons must have the same length")
            out = _make_numpy_object_array(n)
            for i in range(n):
                out[i] = _coerce_locator_out(
                    from_latlon(
                        float(lats[i]),
                        float(lons[i]),
                        precision=precision,
                        resolution_deg=resolution_deg,
                    )
                )
            return out
        return _from_latlon_numpy(lats, lons, precision=precision)

    # Explicit return type requests
    if return_type == "numpy":
        if not _is_numpy_array([0.0]):  # quick check for numpy availability
            # Above is a bit hacky; better:
            try:
                import numpy as np  # type: ignore
            except Exception as e:
                raise ImportError("return_type='numpy' requires numpy") from e
        lats_arr = _as_numpy_array(lats)
        lons_arr = _as_numpy_array(lons)
        if resolution_deg is not None:
            if len(lats_arr) != len(lons_arr):
                raise ValueError("lats and lons must have the same length")
            out = _make_numpy_object_array(int(len(lats_arr)))
            for i in range(int(len(lats_arr))):
                out[i] = _coerce_locator_out(
                    from_latlon(
                        float(lats_arr[i]),
                        float(lons_arr[i]),
                        precision=precision,
                        resolution_deg=resolution_deg,
                    )
                )
            return out
        return _from_latlon_numpy(lats_arr, lons_arr, precision=precision)

    if return_type == "pandas":
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise ImportError("return_type='pandas' requires pandas") from e

        if _is_pandas_series(lats) and _is_pandas_series(lons):
            if len(lats) != len(lons):
                raise ValueError("lats and lons must have the same length")
            index = lats.index
            name = getattr(lats, "name", None)
            lat_list = lats.tolist()
            lon_list = lons.tolist()
        else:
            lat_list = list(lats)
            lon_list = list(lons)
            if len(lat_list) != len(lon_list):
                raise ValueError("lats and lons must have the same length")
            index = None
            name = None

        out = [
            _coerce_locator_out(
                from_latlon(
                    float(lat_list[i]),
                    float(lon_list[i]),
                    precision=precision,
                    resolution_deg=resolution_deg,
                )
            )
            for i in range(len(lat_list))
        ]
        return pd.Series(out, index=index, name=name)

    # Default list behavior
    lat_list = list(lats)
    lon_list = list(lons)
    if len(lat_list) != len(lon_list):
        raise ValueError("lats and lons must have the same length")

    return [
        _coerce_locator_out(
            from_latlon(
                float(lat_list[i]),
                float(lon_list[i]),
                precision=precision,
                resolution_deg=resolution_deg,
            )
        )
        for i in range(len(lat_list))
    ]


def normalize_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    """
    Vectorized locator normalization.

    return_type:
      - "auto": pandas Series in -> Series out, else list[str]
      - "list": always list[str]
      - "pandas": pandas Series (requires pandas)
    """
    def _normalize_series(series):
        import pandas as pd  # type: ignore

        s = series.astype(str).str.strip()
        if (s == "").any():
            raise InvalidLocatorError("locator is empty")

        length = s.str.len()
        invalid_len = (length < 2) | (length > 10) | (length % 2 != 0)
        if invalid_len.any():
            raise PrecisionError("precision must be even and between 2 and 10 characters")

        out = pd.Series([""] * len(s), index=s.index, name=series.name)

        def _apply_pair(pair_index: int, kind: str, pattern: str, case: str | None) -> None:
            start = (pair_index - 1) * 2
            end = pair_index * 2
            mask = length >= end
            if not mask.any():
                return
            part = s.str.slice(start, end)
            if case == "upper":
                part = part.str.upper()
            elif case == "lower":
                part = part.str.lower()
            valid = part.str.fullmatch(pattern)
            bad = mask & ~valid
            if bad.any():
                raise InvalidLocatorError(f"invalid {kind} in locator")
            out[:] = out + part.where(mask, "")

        _apply_pair(1, "field letters", r"[A-R]{2}", "upper")
        _apply_pair(2, "digits", r"[0-9]{2}", None)
        _apply_pair(3, "letters", r"[a-x]{2}", "lower")
        _apply_pair(4, "digits", r"[0-9]{2}", None)
        _apply_pair(5, "letters", r"[a-x]{2}", "lower")

        return out

    if return_type == "auto" and _is_pandas_series(locators):
        return _normalize_series(locators)

    if return_type == "pandas":
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise ImportError("return_type='pandas' requires pandas") from e
        series = locators if _is_pandas_series(locators) else pd.Series(list(locators))
        return _normalize_series(series)

    return [normalize(str(x)) for x in locators]


def to_center_latlon_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    """
    Vectorized locator -> center lat/lon.

    Returns:
      - "auto": Series -> DataFrame (lat, lon) OR two Series? (see below),
                ndarray -> (lat_array, lon_array),
                else -> (list_lat, list_lon)
      - "tuple": always (list_lat, list_lon)
      - "numpy": (lat_ndarray, lon_ndarray)
      - "pandas": pandas.DataFrame with columns ["lat", "lon"]
    """
    # pandas series in => DataFrame out (nice ergonomics)
    if return_type == "auto" and _is_pandas_series(locators):
        import pandas as pd  # type: ignore
        vals = locators.astype(str).tolist()
        lat = []
        lon = []
        for v in vals:
            a, b = to_center_latlon(v)
            lat.append(a)
            lon.append(b)
        return pd.DataFrame({"lat": lat, "lon": lon}, index=locators.index)

    # numpy in => numpy out
    if return_type == "auto" and _is_numpy_array(locators):
        n = int(len(locators))
        lat_out = _make_numpy_float_array(n)
        lon_out = _make_numpy_float_array(n)
        for i in range(n):
            a, b = to_center_latlon(str(locators[i]))
            lat_out[i] = a
            lon_out[i] = b
        return (lat_out, lon_out)

    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        arr = _as_numpy_array(locators)
        n = int(len(arr))
        lat_out = _make_numpy_float_array(n)
        lon_out = _make_numpy_float_array(n)
        for i in range(n):
            a, b = to_center_latlon(str(arr[i]))
            lat_out[i] = a
            lon_out[i] = b
        return (lat_out, lon_out)
    if return_type == "tuple":
        lat = []
        lon = []
        for loc in locators:
            a, b = to_center_latlon(loc)
            lat.append(a)
            lon.append(b)
        return (lat, lon)

    if return_type == "pandas":
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise ImportError("return_type='pandas' requires pandas") from e
        if _is_pandas_series(locators):
            idx = locators.index
            vals = locators.astype(str).tolist()
        else:
            vals = [str(x) for x in locators]
            idx = None
        lat = []
        lon = []
        for v in vals:
            a, b = to_center_latlon(v)
            lat.append(a)
            lon.append(b)
        return pd.DataFrame({"lat": lat, "lon": lon}, index=idx)

    # Plain tuple of lists
    vals = [str(x) for x in locators]
    lat = []
    lon = []
    for v in vals:
        a, b = to_center_latlon(v)
        lat.append(a)
        lon.append(b)
    return (lat, lon)


def to_bbox_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    """
    Vectorized locator -> bbox.

    Returns:
      - list[tuple[min_lat, min_lon, max_lat, max_lon]] by default
      - numpy ndarray shape (n, 4) if return_type="numpy"
      - pandas DataFrame columns ["min_lat","min_lon","max_lat","max_lon"] if return_type="pandas"
    """
    vals: list[str]
    idx = None

    if _is_pandas_series(locators):
        vals = locators.astype(str).tolist()
        idx = locators.index
    elif _is_numpy_array(locators):
        vals = [str(x) for x in locators.tolist()]
    else:
        vals = [str(x) for x in locators]

    bbs = [to_bbox(v) for v in vals]

    if return_type == "auto":
        if idx is not None:
            # Pandas in -> DataFrame out
            import pandas as pd  # type: ignore
            return pd.DataFrame(
                bbs,
                columns=["min_lat", "min_lon", "max_lat", "max_lon"],
                index=idx,
            )
        if _is_numpy_array(locators):
            # Numpy in -> numpy out
            import numpy as np  # type: ignore
            return np.asarray(bbs, dtype=float)
        return bbs

    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(bbs, dtype=float)

    if return_type == "pandas":
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise ImportError("return_type='pandas' requires pandas") from e
        return pd.DataFrame(
            bbs,
            columns=["min_lat", "min_lon", "max_lat", "max_lon"],
            index=idx,
        )

    if return_type == "tuple":
        min_lat = []
        min_lon = []
        max_lat = []
        max_lon = []
        for a, b, c, d in bbs:
            min_lat.append(a)
            min_lon.append(b)
            max_lat.append(c)
            max_lon.append(d)
        return (min_lat, min_lon, max_lat, max_lon)

    if return_type == "list":
        return bbs

    raise ValueError(f"Unknown return_type: {return_type!r}")


def _geojson_series_out(locators: Any, out: list[Any], *, name: str | None) -> Any:
    import pandas as pd  # type: ignore
    if _is_pandas_series(locators):
        return pd.Series(out, index=locators.index, name=name)
    return pd.Series(out, name=name)


def to_geojson_polygon_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_geojson_polygon(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="geojson_polygon")
    return out


def to_geojson_feature_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_geojson_feature(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="geojson_feature")
    return out


def to_geojson_feature_collection_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    if return_type not in ("auto", "list"):
        raise ValueError("return_type must be 'auto' or 'list'")
    return to_geojson_feature_collection(locators)


def to_geojson_bbox_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_geojson_bbox(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="geojson_bbox")
    return out


def to_geojson_envelope_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_geojson_envelope(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="geojson_envelope")
    return out


def cell_size_deg_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [cell_size_deg(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="cell_size_deg")
    return out


def cell_size_km_many(
    locators: Any,
    *,
    at_lat: float | None = None,
    method: str = "spherical",
    return_type: str = "auto",
) -> Any:
    out = [cell_size_km(loc, at_lat=at_lat, method=method) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="cell_size_km")
    return out


def cell_size_many(
    locators: Any,
    *,
    unit: str = "deg",
    at_lat: float | None = None,
    method: str = "spherical",
    return_type: str = "auto",
) -> Any:
    if unit not in ("deg", "km", "miles"):
        raise ValueError(f"Unknown unit: {unit!r}")
    if unit == "deg":
        out = [cell_size(loc, unit="deg") for loc in locators]
    else:
        out = [cell_size_km(loc, at_lat=at_lat, method=method) for loc in locators]
    if unit == "miles":
        miles_per_km = 0.621371
        out = [(w * miles_per_km, h * miles_per_km) for w, h in out]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="cell_size")
    return out


def corners_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [corners(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="corners")
    return out


def azimuth_many(
    points_a: Any,
    points_b: Any,
    *,
    range_mode: bool = False,
    return_type: str = "auto",
) -> Any:
    a_list, b_list = _require_same_length(points_a, points_b, name_a="points_a", name_b="points_b")
    out = [azimuth(a, b, range_mode=range_mode) for a, b in zip(a_list, b_list)]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(points_a)):
        return _geojson_series_out(points_a, out, name="azimuth")
    return out


def parent_many(
    locators: Any,
    *,
    precision: int | None = None,
    return_type: str = "auto",
) -> Any:
    if precision is None:
        out = [parent(loc).locator for loc in locators]
    else:
        out = [parent(loc, precision=precision).locator for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="parent")
    return out


def children_many(
    locators: Any,
    *,
    precision: int | None = None,
    limit: int | None = None,
    return_type: str = "auto",
) -> Any:
    out = []
    for loc in locators:
        if precision is None:
            precision_value = parse(loc).precision + 2
        else:
            precision_value = precision
        items = list(children(loc, precision=precision_value))
        if limit is not None:
            items = items[:limit]
        out.append([g.locator for g in items])
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="children")
    return out


def to_utm_zone_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_utm_zone(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="utm_zone")
    return out


def intersects_bbox_many(
    locators: Any,
    bboxes: Any,
    *,
    return_type: str = "auto",
) -> Any:
    loc_list, bbox_list = _require_same_length(locators, bboxes, name_a="locators", name_b="bboxes")
    out = [intersects_bbox(loc, bbox) for loc, bbox in zip(loc_list, bbox_list)]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="intersects_bbox")
    return out


def intersects_polygon_many(
    locators: Any,
    polygons: Any,
    *,
    return_type: str = "auto",
) -> Any:
    loc_list, poly_list = _require_same_length(locators, polygons, name_a="locators", name_b="polygons")
    out = [intersects_polygon(loc, poly) for loc, poly in zip(loc_list, poly_list)]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="intersects_polygon")
    return out


def area_km2_many(
    locators: Any,
    *,
    method: str = "spherical",
    return_type: str = "auto",
) -> Any:
    out = [area_km2(loc, method=method) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="area_km2")
    return out


def diagonal_km_many(
    locators: Any,
    *,
    method: str = "spherical",
    return_type: str = "auto",
) -> Any:
    out = [diagonal_km(loc, method=method) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="diagonal_km")
    return out


def to_wkt_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [to_wkt(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="wkt")
    return out


def contains_point_many(
    locators: Any,
    lats: Any,
    lons: Any,
    *,
    return_type: str = "auto",
) -> Any:
    loc_list, lat_list = _require_same_length(locators, lats, name_a="locators", name_b="lats")
    lon_list = _listify(lons)
    if len(lon_list) != len(loc_list):
        raise ValueError("lons and locators must have the same length")
    out = [contains_point(loc, lat, lon) for loc, lat, lon in zip(loc_list, lat_list, lon_list)]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=bool)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="contains_point")
    return out


def contains_many(
    outers: Any,
    inners: Any,
    *,
    return_type: str = "auto",
) -> Any:
    outer_list, inner_list = _require_same_length(outers, inners, name_a="outers", name_b="inners")
    out = [contains(outer, inner) for outer, inner in zip(outer_list, inner_list)]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=bool)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(outers)):
        return _geojson_series_out(outers, out, name="contains")
    return out


def split_bbox_many(
    bboxes: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [split_bbox_list(bbox) for bbox in bboxes]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(bboxes)):
        return _geojson_series_out(bboxes, out, name="split_bbox")
    return out


def precision_many(
    locators: Any,
    *,
    return_type: str = "auto",
) -> Any:
    out = [precision_of(loc) for loc in locators]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=int)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="precision")
    return out


def initial_bearing_many(
    locators_a: Any,
    locators_b: Any,
    *,
    return_type: str = "auto",
) -> Any:
    loc_a, loc_b = _require_same_length(locators_a, locators_b, name_a="locators_a", name_b="locators_b")
    out = [initial_bearing(a, b) for a, b in zip(loc_a, loc_b)]
    if return_type == "list":
        return out
    if return_type == "numpy":
        try:
            import numpy as np  # type: ignore
        except Exception as e:
            raise ImportError("return_type='numpy' requires numpy") from e
        return np.asarray(out, dtype=float)
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators_a)):
        return _geojson_series_out(locators_a, out, name="initial_bearing")
    return out


def neighbors_many(
    locators: Any,
    *,
    ring: int = 1,
    diagonals: bool = True,
    return_type: str = "auto",
) -> Any:
    out = [[g.locator for g in neighbors(loc, ring=ring, diagonals=diagonals)] for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="neighbors")
    return out


def adjacent_many(
    locators: Any,
    *,
    diagonals: bool = True,
    return_type: str = "auto",
) -> Any:
    out = [{k: v.locator for k, v in adjacent(loc, diagonals=diagonals).items()} for loc in locators]
    if return_type == "list":
        return out
    if return_type == "pandas" or (return_type == "auto" and _is_pandas_series(locators)):
        return _geojson_series_out(locators, out, name="adjacent")
    return out
