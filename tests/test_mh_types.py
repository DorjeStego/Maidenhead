import math

import pytest

from maidenhead import GridSquare, cell_size, normalize
from maidenhead.geo import EARTH_RADIUS_KM


def test_gridsquare_components():
    loc = "IO83ri17aa"
    g = GridSquare(normalize(loc))
    assert g.field == "IO"
    assert g.square == "83"
    assert g.subsquare == "ri"
    assert g.ext4 == "17"
    assert g.ext5 == "aa"
    assert g.pairs == ["IO", "83", "ri", "17", "aa"]


def test_gridsquare_ordering():
    a = GridSquare("IO")
    b = GridSquare("IO83")
    c = GridSquare("JO")
    assert a < b
    assert sorted([c, b, a]) == [a, b, c]


def test_gridsquare_size_km_lat(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=201)[0]
    g = GridSquare(normalize(loc))
    assert g.size_km_lat == pytest.approx(cell_size(g, unit="km")[1])


def test_gridsquare_size_km_lon_at(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=202)[0]
    g = GridSquare(normalize(loc))
    lon_deg = cell_size(g, unit="deg")[0]
    lat = 45.0
    expected = (math.cos(math.radians(lat)) * lon_deg * 2.0 * math.pi * EARTH_RADIUS_KM) / 360.0
    assert g.size_km_lon_at(lat) == pytest.approx(expected)
