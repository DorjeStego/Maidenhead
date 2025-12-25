import pytest


numpy = pytest.importorskip("numpy")

from maidenhead.core import from_latlon
from maidenhead.vector import from_latlon_many, to_center_latlon_many


def test_from_latlon_many_numpy_matches_core():
    lats = numpy.array([51.5, 40.7, -33.86])
    lons = numpy.array([-0.1, -74.0, 151.2])
    out = from_latlon_many(lats, lons, precision=6, return_type="numpy")
    expected = [
        from_latlon(float(lat), float(lon), precision=6).locator
        for lat, lon in zip(lats, lons)
    ]
    assert out.tolist() == expected


def test_from_latlon_many_numpy_mismatched_shapes():
    lats = numpy.array([0.0, 1.0])
    lons = numpy.array([0.0])
    with pytest.raises(ValueError):
        from_latlon_many(lats, lons, precision=6, return_type="numpy")


def test_from_latlon_many_numpy_with_resolution_fallback():
    lats = numpy.array([0.0, 10.0])
    lons = numpy.array([0.0, 10.0])
    out = from_latlon_many(lats, lons, precision=8, return_type="numpy", resolution_deg=1.0)
    assert all(len(loc) == 4 for loc in out.tolist())


def test_to_center_latlon_many_numpy_return_type():
    locs = numpy.array(["IO83ri", "JO22db"])
    lat_out, lon_out = to_center_latlon_many(locs, return_type="numpy")
    assert lat_out.shape == (2,)
    assert lon_out.shape == (2,)
