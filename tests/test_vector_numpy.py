import pytest


numpy = pytest.importorskip("numpy")

from maidenhead.core import from_latlon
from maidenhead.vector import from_latlon_many


def test_from_latlon_many_numpy_matches_core():
    lats = numpy.array([51.5, 40.7, -33.86])
    lons = numpy.array([-0.1, -74.0, 151.2])
    out = from_latlon_many(lats, lons, precision=6, return_type="numpy")
    expected = [
        from_latlon(float(lat), float(lon), precision=6).locator
        for lat, lon in zip(lats, lons)
    ]
    assert out.tolist() == expected
