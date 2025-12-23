import pytest

from maidenhead.geo import bearing_deg, distance_km, midpoint


def test_distance_symmetric():
    d1 = distance_km((0.0, 0.0), (10.0, 10.0))
    d2 = distance_km((10.0, 10.0), (0.0, 0.0))
    assert d1 == pytest.approx(d2)


def test_bearing_due_north():
    br = bearing_deg((0.0, 0.0), (1.0, 0.0))
    assert br == pytest.approx(0.0, abs=1e-6)


def test_midpoint_on_equator():
    lat, lon = midpoint((0.0, 0.0), (0.0, 10.0))
    assert lat == pytest.approx(0.0, abs=1e-6)
    assert lon == pytest.approx(5.0, abs=1e-6)
