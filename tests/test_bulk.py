import random

import pytest

from maidenhead import (
    cell_size,
    cell_size_many,
    from_latlon_many,
    GridSquare,
    normalize,
    normalize_many,
    to_bbox,
    to_bbox_many,
    to_center_latlon,
    to_center_many,
)


def _by_length(valid_locators):
    by_len = {}
    for loc in valid_locators:
        by_len.setdefault(len(loc), []).append(loc)
    return by_len


def test_normalize_many(valid_locators):
    rng = random.Random(11)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    mixed = [loc.swapcase() for loc in locs]
    assert normalize_many(mixed) == [normalize(loc) for loc in locs]


def test_normalize_many_with_gridsquare(valid_locators):
    rng = random.Random(15)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    squares = [GridSquare(normalize(loc)) for loc in locs]
    assert normalize_many(squares) == [normalize(loc) for loc in locs]


def test_to_center_many(valid_locators):
    rng = random.Random(12)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    lats, lons = to_center_many(locs)
    assert len(lats) == len(locs)
    assert len(lons) == len(locs)
    for loc, lat, lon in zip(locs, lats, lons):
        exp_lat, exp_lon = to_center_latlon(loc)
        assert lat == pytest.approx(exp_lat)
        assert lon == pytest.approx(exp_lon)


def test_to_bbox_many(valid_locators):
    rng = random.Random(13)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    min_lats, min_lons, max_lats, max_lons = to_bbox_many(locs)
    for loc, min_lat, min_lon, max_lat, max_lon in zip(locs, min_lats, min_lons, max_lats, max_lons):
        exp = to_bbox(loc)
        assert (min_lat, min_lon, max_lat, max_lon) == pytest.approx(exp)


def test_from_latlon_many_roundtrip(valid_locators):
    by_len = _by_length(valid_locators)
    for length in (2, 4, 6, 8):
        locs = by_len.get(length, [])
        if not locs:
            continue
        sample = locs[:3]
        lats, lons = to_center_many(sample)
        out = from_latlon_many(lats, lons, precision=length)
        assert out == [normalize(loc) for loc in sample]


def test_cell_size_many(valid_locators):
    rng = random.Random(14)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    widths, heights = cell_size_many(locs, unit="deg")
    for loc, width, height in zip(locs, widths, heights):
        exp_w, exp_h = cell_size(loc)
        assert width == pytest.approx(exp_w)
        assert height == pytest.approx(exp_h)
