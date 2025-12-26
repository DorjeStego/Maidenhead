import pytest


pd = pytest.importorskip("pandas")

from maidenhead.core import from_latlon
from maidenhead.errors import InvalidLocatorError, PrecisionError
from maidenhead.vector import (
    from_latlon_many,
    normalize_many,
    to_center_latlon_many,
    to_geojson_bbox_many,
    to_geojson_envelope_many,
    to_geojson_feature_collection_many,
    to_geojson_feature,
    to_geojson_feature_many,
    to_geojson_polygon_many,
    neighbors_many,
    adjacent_many,
    cell_size_deg_many,
    cell_size_km_many,
    cell_size_many,
    corners_many,
    azimuth_many,
    parent_many,
    children_many,
    to_utm_zone_many,
    intersects_bbox_many,
    intersects_polygon_many,
    area_km2_many,
    diagonal_km_many,
    to_wkt_many,
    contains_point_many,
    contains_many,
    split_bbox_many,
    precision_many,
    initial_bearing_many,
)
from maidenhead.core import to_bbox


def test_from_latlon_many_pandas_return_type():
    lats = pd.Series([51.5, 40.7], index=["a", "b"], name="lat")
    lons = pd.Series([-0.1, -74.0], index=["a", "b"], name="lon")
    out = from_latlon_many(lats, lons, precision=6, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.name == "lat"
    expected = [
        from_latlon(float(lat), float(lon), precision=6).locator
        for lat, lon in zip(lats.tolist(), lons.tolist())
    ]
    assert out.tolist() == expected


def test_from_latlon_many_pandas_auto_return_type():
    lats = pd.Series([51.5, 40.7], index=["a", "b"], name="lat")
    lons = pd.Series([-0.1, -74.0], index=["a", "b"], name="lon")
    out = from_latlon_many(lats, lons, precision=6, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.name == "lat"


def test_from_latlon_many_pandas_mismatched_lengths():
    lats = pd.Series([51.5, 40.7], index=["a", "b"], name="lat")
    lons = pd.Series([-0.1], index=["a"], name="lon")
    with pytest.raises(ValueError):
        from_latlon_many(lats, lons, precision=6, return_type="pandas")


def test_to_center_latlon_many_pandas_return_type():
    locs = pd.Series(["IO83ri", "JO22db"], index=["x", "y"], name="loc")
    out = to_center_latlon_many(locs, return_type="pandas")
    assert list(out.columns) == ["lat", "lon"]
    assert out.index.tolist() == ["x", "y"]


def test_from_latlon_many_pandas_list_input_index():
    lats = [51.5, 40.7]
    lons = [-0.1, -74.0]
    out = from_latlon_many(lats, lons, precision=6, return_type="pandas")
    assert out.index.tolist() == [0, 1]
    assert out.name is None


def test_normalize_many_pandas_auto_return_type():
    locs = pd.Series([" io83RI ", "jo22db"], index=["a", "b"], name="locs")
    out = normalize_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.name == "locs"
    assert out.tolist() == ["IO83ri", "JO22db"]


def test_normalize_many_pandas_invalid_length():
    locs = pd.Series(["IO8", "IO83"], index=["a", "b"])
    with pytest.raises(PrecisionError):
        normalize_many(locs, return_type="pandas")


def test_normalize_many_pandas_invalid_chars():
    locs = pd.Series(["SS00"], index=["a"])
    with pytest.raises(InvalidLocatorError):
        normalize_many(locs, return_type="pandas")


def test_to_geojson_polygon_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_geojson_polygon_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_to_geojson_feature_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_geojson_feature_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_to_geojson_feature_collection_many():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_geojson_feature_collection_many(locs)
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.name == "geojson_feature_collection"
    assert out.tolist() == [to_geojson_feature(loc) for loc in locs.tolist()]


def test_to_geojson_bbox_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_geojson_bbox_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_to_geojson_envelope_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_geojson_envelope_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_neighbors_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = neighbors_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_adjacent_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = adjacent_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_cell_size_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = cell_size_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert all(isinstance(item, tuple) and len(item) == 2 for item in out.tolist())


def test_cell_size_deg_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = cell_size_deg_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_cell_size_km_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = cell_size_km_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_corners_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = corners_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert all(isinstance(item, tuple) and len(item) == 4 for item in out.tolist())


def test_azimuth_many_pandas():
    points_a = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    points_b = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = azimuth_many(points_a, points_b, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert all(isinstance(item, tuple) and len(item) == 2 for item in out.tolist())


def test_parent_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = parent_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_children_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = children_many(locs, limit=3, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert all(isinstance(item, list) for item in out.tolist())


def test_to_utm_zone_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_utm_zone_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_intersects_bbox_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    bboxes = pd.Series([(-90.0, -180.0, 90.0, 180.0)] * 2, index=["a", "b"])
    out = intersects_bbox_many(locs, bboxes, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.tolist() == [True, True]


def test_intersects_polygon_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    polys = []
    for loc in locs.tolist():
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        polys.append(
            [
                (min_lat, min_lon),
                (min_lat, max_lon),
                (max_lat, max_lon),
                (max_lat, min_lon),
            ]
        )
    polys = pd.Series(polys, index=["a", "b"])
    out = intersects_polygon_many(locs, polys, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
    assert out.tolist() == [True, True]


def test_area_km2_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = area_km2_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_diagonal_km_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = diagonal_km_many(locs, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_to_wkt_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = to_wkt_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_contains_point_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    lats = pd.Series([0.0, 0.0], index=["a", "b"])
    lons = pd.Series([0.0, 0.0], index=["a", "b"])
    out = contains_point_many(locs, lats, lons, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_contains_many_pandas():
    outers = pd.Series(["IO83", "JO22"], index=["a", "b"])
    inners = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = contains_many(outers, inners, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_split_bbox_many_pandas():
    bboxes = pd.Series(
        [
            (10.0, 170.0, 20.0, -170.0),
            (10.0, 10.0, 20.0, 20.0),
        ],
        index=["a", "b"],
    )
    out = split_bbox_many(bboxes, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_precision_many_pandas():
    locs = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = precision_many(locs, return_type="pandas")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]


def test_initial_bearing_many_pandas():
    a = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    b = pd.Series(["IO83ri", "JO22db"], index=["a", "b"])
    out = initial_bearing_many(a, b, return_type="auto")
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == ["a", "b"]
