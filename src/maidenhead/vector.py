# maidenhead/vector.py
from __future__ import annotations

from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple, Union, overload

from . import constants as C
from .mh_types import GridSquare, LocatorLike, validate_precision
from .core import from_latlon, to_bbox, to_center_latlon


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

    if return_type == "list":
        return bbs

    raise ValueError(f"Unknown return_type: {return_type!r}")
