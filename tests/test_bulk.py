import random

import pytest

from maidenhead import (
    cell_size,
    cell_size_deg,
    cell_size_deg_many,
    cell_size_many,
    cell_size_km_many,
    area_km2,
    area_km2_many,
    azimuth,
    azimuth_many,
    adjacent,
    adjacent_many,
    children_many,
    contains,
    contains_many,
    contains_point,
    contains_point_many,
    corners,
    corners_many,
    diagonal_km,
    diagonal_km_many,
    intersects_bbox,
    intersects_bbox_many,
    intersects_polygon,
    intersects_polygon_many,
    initial_bearing,
    initial_bearing_many,
    from_latlon_many,
    GridSquare,
    to_geojson_bbox,
    to_geojson_bbox_many,
    to_geojson_envelope,
    to_geojson_envelope_many,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_feature_collection_many,
    to_geojson_feature_many,
    to_geojson_polygon,
    to_geojson_polygon_many,
    neighbors,
    neighbors_many,
    normalize,
    parent_many,
    normalize_many,
    parent,
    children,
    parse,
    precision_many,
    precision_of,
    split_bbox_list,
    split_bbox_many,
    to_utm_zone,
    to_utm_zone_many,
    to_wkt,
    to_wkt_many,
    to_bbox,
    to_bbox_many,
    to_center_latlon,
    to_center_many,
)
from maidenhead.errors import OutOfRangeError


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


def test_from_latlon_many_resolution_fallback():
    lats = [0.0, 10.0]
    lons = [0.0, 10.0]
    out = from_latlon_many(lats, lons, precision=8, resolution_deg=1.0)
    assert all(len(loc) == 4 for loc in out)


def test_from_latlon_many_mismatched_lengths():
    with pytest.raises(OutOfRangeError):
        from_latlon_many([0.0], [0.0, 1.0])


def test_to_center_many_with_gridsquare(valid_locators):
    locs = [GridSquare(normalize(loc)) for loc in valid_locators[:3]]
    lats, lons = to_center_many(locs)
    assert len(lats) == len(locs)
    assert len(lons) == len(locs)


def test_to_center_many_empty():
    lats, lons = to_center_many([])
    assert lats == []
    assert lons == []


def test_to_bbox_many_empty():
    min_lats, min_lons, max_lats, max_lons = to_bbox_many([])
    assert min_lats == []
    assert min_lons == []
    assert max_lats == []
    assert max_lons == []


def test_cell_size_many(valid_locators):
    rng = random.Random(14)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    widths, heights = cell_size_many(locs, unit="deg")
    for loc, width, height in zip(locs, widths, heights):
        exp_w, exp_h = cell_size(loc)
        assert width == pytest.approx(exp_w)
        assert height == pytest.approx(exp_h)


def test_cell_size_deg_many(valid_locators):
    rng = random.Random(16)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    widths, heights = cell_size_deg_many(locs)
    for loc, width, height in zip(locs, widths, heights):
        exp_w, exp_h = cell_size_deg(loc)
        assert width == pytest.approx(exp_w)
        assert height == pytest.approx(exp_h)


def test_cell_size_km_many(valid_locators):
    rng = random.Random(17)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    widths, heights = cell_size_km_many(locs)
    for loc, width, height in zip(locs, widths, heights):
        exp_w, exp_h = cell_size(loc, unit="km")
        assert width == pytest.approx(exp_w)
        assert height == pytest.approx(exp_h)


def test_cell_size_many_miles(valid_locators):
    rng = random.Random(18)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    widths, heights = cell_size_many(locs, unit="miles")
    miles_per_km = 0.621371
    for loc, width, height in zip(locs, widths, heights):
        exp_w, exp_h = cell_size(loc, unit="km")
        assert width == pytest.approx(exp_w * miles_per_km)
        assert height == pytest.approx(exp_h * miles_per_km)


def test_area_km2_many(valid_locators):
    rng = random.Random(19)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    out = area_km2_many(locs)
    for loc, area in zip(locs, out):
        assert area == pytest.approx(area_km2(loc))


def test_diagonal_km_many(valid_locators):
    rng = random.Random(20)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    out = diagonal_km_many(locs)
    for loc, diag in zip(locs, out):
        assert diag == pytest.approx(diagonal_km(loc))


def test_parent_many(valid_locators):
    rng = random.Random(21)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    out = parent_many(locs)
    for loc, parent_loc in zip(locs, out):
        assert parent_loc == parent(loc).locator


def test_children_many(valid_locators):
    rng = random.Random(22)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = children_many(locs, limit=5)
    for loc, children_loc in zip(locs, out):
        expected = [g.locator for g in list(children(loc, precision=parse(loc).precision + 2))[:5]]
        assert children_loc == expected


def test_to_wkt_many(valid_locators):
    rng = random.Random(23)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    out = to_wkt_many(locs)
    for loc, wkt in zip(locs, out):
        assert wkt == to_wkt(loc)


def test_azimuth_many(valid_locators):
    rng = random.Random(24)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    a = locs[:2]
    b = locs[2:4]
    out = azimuth_many(a, b)
    for loc_a, loc_b, result in zip(a, b, out):
        assert result == pytest.approx(azimuth(loc_a, loc_b))


def test_azimuth_many_range_mode(valid_locators):
    rng = random.Random(25)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    a = locs[:2]
    b = locs[2:4]
    out = azimuth_many(a, b, range_mode=True)
    for loc_a, loc_b, result in zip(a, b, out):
        assert result == pytest.approx(azimuth(loc_a, loc_b, range_mode=True))


def test_contains_point_many(valid_locators):
    rng = random.Random(26)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    lats, lons = to_center_many(locs)
    out = contains_point_many(locs, lats, lons)
    assert all(out)
    for loc, lat, lon, result in zip(locs, lats, lons, out):
        assert result == contains_point(loc, lat, lon)


def test_contains_many(valid_locators):
    rng = random.Random(27)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    outers = [parent(loc).locator for loc in locs]
    out = contains_many(outers, locs)
    assert all(out)
    for outer, inner, result in zip(outers, locs, out):
        assert result == contains(outer, inner)


def test_corners_many_list(valid_locators):
    rng = random.Random(28)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    out = corners_many(locs)
    for loc, corners_out in zip(locs, out):
        assert tuple(corners_out) == corners(loc)


def test_corners_many_tuple(valid_locators):
    rng = random.Random(29)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    nws, nes, sws, ses = corners_many(locs, return_type="tuple")
    for i, loc in enumerate(locs):
        exp = corners(loc)
        assert (nws[i], nes[i], sws[i], ses[i]) == exp


def test_split_bbox_many():
    bboxes = [
        (10.0, 170.0, 20.0, -170.0),
        (10.0, 10.0, 20.0, 20.0),
    ]
    out = split_bbox_many(bboxes)
    assert out[0] == split_bbox_list(bboxes[0])
    assert out[1] == split_bbox_list(bboxes[1])


def test_neighbors_many(valid_locators):
    rng = random.Random(30)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = neighbors_many(locs, ring=1, diagonals=True)
    for loc, row in zip(locs, out):
        expected = [g.locator for g in neighbors(loc, ring=1, diagonals=True)]
        assert row == expected


def test_adjacent_many(valid_locators):
    rng = random.Random(31)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = adjacent_many(locs, diagonals=True)
    for loc, row in zip(locs, out):
        expected = {k: v.locator for k, v in adjacent(loc, diagonals=True).items()}
        assert row == expected


def test_precision_many(valid_locators):
    rng = random.Random(32)
    locs = rng.sample(valid_locators, min(5, len(valid_locators)))
    out = precision_many(locs)
    for loc, value in zip(locs, out):
        assert value == precision_of(loc)


def test_intersects_bbox_many(valid_locators):
    rng = random.Random(33)
    locs = rng.sample(valid_locators, min(2, len(valid_locators)))
    bboxes = [to_bbox(loc) for loc in locs]
    out = intersects_bbox_many(locs, bboxes)
    assert all(out)
    for loc, bbox, result in zip(locs, bboxes, out):
        assert result == intersects_bbox(loc, bbox)


def test_intersects_polygon_many(valid_locators):
    rng = random.Random(34)
    locs = rng.sample(valid_locators, min(2, len(valid_locators)))
    polys = []
    for loc in locs:
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        polys.append(
            [
                (min_lat, min_lon),
                (min_lat, max_lon),
                (max_lat, max_lon),
                (max_lat, min_lon),
            ]
        )
    out = intersects_polygon_many(locs, polys)
    assert all(out)
    for loc, poly, result in zip(locs, polys, out):
        assert result == intersects_polygon(loc, poly)


def test_initial_bearing_many(valid_locators):
    rng = random.Random(35)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    a = locs[:2]
    b = locs[2:4]
    out = initial_bearing_many(a, b)
    for loc_a, loc_b, result in zip(a, b, out):
        assert result == pytest.approx(initial_bearing(loc_a, loc_b))


def test_to_utm_zone_many(valid_locators):
    rng = random.Random(36)
    locs = rng.sample(valid_locators, min(4, len(valid_locators)))
    out = to_utm_zone_many(locs)
    for loc, zone in zip(locs, out):
        assert zone == to_utm_zone(loc)


def test_to_geojson_polygon_many(valid_locators):
    rng = random.Random(37)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = to_geojson_polygon_many(locs)
    for loc, poly in zip(locs, out):
        assert poly == to_geojson_polygon(loc)


def test_to_geojson_feature_many(valid_locators):
    rng = random.Random(38)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = to_geojson_feature_many(locs)
    for loc, feature in zip(locs, out):
        assert feature == to_geojson_feature(loc)


def test_to_geojson_feature_collection_many(valid_locators):
    rng = random.Random(39)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = to_geojson_feature_collection_many(locs)
    assert out == to_geojson_feature_collection(locs)


def test_to_geojson_bbox_many(valid_locators):
    rng = random.Random(40)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = to_geojson_bbox_many(locs)
    for loc, bbox in zip(locs, out):
        assert bbox == to_geojson_bbox(loc)


def test_to_geojson_envelope_many(valid_locators):
    rng = random.Random(41)
    locs = rng.sample(valid_locators, min(3, len(valid_locators)))
    out = to_geojson_envelope_many(locs)
    for loc, env in zip(locs, out):
        assert env == to_geojson_envelope(loc)
