import pytest


pd = pytest.importorskip("pandas")

from maidenhead.core import from_latlon
from maidenhead.vector import from_latlon_many, to_center_latlon_many


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
