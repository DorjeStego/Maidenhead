import random

import pytest

from maidenhead import (
    adjacent,
    azimuth,
    cell_size,
    cell_size_deg,
    cell_size_km,
    area_km2,
    diagonal_km,
    children,
    contains,
    corners,
    from_latlon,
    format_locator,
    initial_bearing,
    neighbors,
    normalize,
    parent,
    step,
    to_bbox,
    to_bbox_split,
    to_center_latlon,
    to_geojson_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_bbox,
    to_geojson_envelope,
    to_wkt,
)
from maidenhead import constants as C
from maidenhead.errors import PrecisionError
from maidenhead.geo import bearing_deg, distance_km


def _pick_by_length(valid_locators, length):
    for loc in valid_locators:
        if len(loc) == length:
            return loc
    raise AssertionError(f"no locator with length {length}")


def test_center_roundtrip_locators(valid_locators):
    for loc in valid_locators:
        lat, lon = to_center_latlon(loc)
        back = from_latlon(lat, lon, precision=len(loc))
        assert back.locator == normalize(loc)


def test_bbox_contains_center(valid_locators):
    for loc in valid_locators:
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        lat, lon = to_center_latlon(loc)
        assert min_lat <= lat <= max_lat
        assert min_lon <= lon <= max_lon


def test_bbox_split_none_for_standard_cells(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    assert to_bbox_split(loc) is None


def test_bbox_split_none_at_dateline_edge():
    loc = from_latlon(0.0, 179.999, precision=6)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    assert max_lon == pytest.approx(180.0)
    assert to_bbox_split(loc) is None


def test_geojson_polygon_matches_bbox(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    geojson = to_geojson_polygon(loc)
    assert geojson["type"] == "Polygon"
    ring = geojson["coordinates"][0]
    assert ring[0] == [min_lon, min_lat]
    assert ring[1] == [max_lon, min_lat]
    assert ring[2] == [max_lon, max_lat]
    assert ring[3] == [min_lon, max_lat]
    assert ring[4] == [min_lon, min_lat]


def test_geojson_feature(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    feature = to_geojson_feature(loc, properties={"name": "cell"})
    assert feature["type"] == "Feature"
    assert feature["properties"]["name"] == "cell"
    assert feature["geometry"]["type"] == "Polygon"


def test_geojson_feature_collection(valid_locators):
    locs = valid_locators[:2]
    fc = to_geojson_feature_collection(locs, properties_fn=lambda l: {"loc": l})
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 2
    assert fc["features"][0]["properties"]["loc"] == locs[0]


def test_geojson_bbox_and_envelope(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    bbox = to_geojson_bbox(loc)
    env = to_geojson_envelope(loc)
    assert env["bbox"] == bbox
    assert env["type"] == "Polygon"


def test_wkt_matches_bbox(valid_locators):
    loc = _pick_by_length(valid_locators, 6)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    wkt = to_wkt(loc)
    expected = (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )
    assert wkt == expected


def test_corners_match_bbox(valid_locators):
    for loc in [
        _pick_by_length(valid_locators, 4),
        _pick_by_length(valid_locators, 6),
        _pick_by_length(valid_locators, 8),
    ]:
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        nw, ne, sw, se = corners(loc)
        assert nw == (max_lat, min_lon)
        assert ne == (max_lat, max_lon)
        assert sw == (min_lat, min_lon)
        assert se == (min_lat, max_lon)


def test_azimuth_center_matches_geo(valid_locators):
    rng = random.Random(7)
    a, b = rng.sample(valid_locators, 2)
    bearing, distance = azimuth(a, b)
    lat_a, lon_a = to_center_latlon(a)
    lat_b, lon_b = to_center_latlon(b)
    assert bearing == pytest.approx(bearing_deg((lat_a, lon_a), (lat_b, lon_b)))
    assert distance == pytest.approx(distance_km((lat_a, lon_a), (lat_b, lon_b)))


def test_azimuth_range_bounds(valid_locators):
    rng = random.Random(8)
    a, b = rng.sample(valid_locators, 2)
    bearing, min_distance, max_distance = azimuth(a, b, range_mode=True)
    lat_a, lon_a = to_center_latlon(a)
    lat_b, lon_b = to_center_latlon(b)
    center_distance = distance_km((lat_a, lon_a), (lat_b, lon_b))
    distances = [distance_km(p, q) for p in corners(a) for q in corners(b)]
    assert bearing == pytest.approx(bearing_deg((lat_a, lon_a), (lat_b, lon_b)))
    assert min_distance == pytest.approx(min(distances))
    assert max_distance == pytest.approx(max(distances))
    assert min_distance <= center_distance <= max_distance


def test_initial_bearing_center(valid_locators):
    rng = random.Random(0)
    by_length = {}
    for loc in valid_locators:
        by_length.setdefault(len(loc), []).append(loc)
    lengths = sorted(by_length)
    assert len(lengths) >= 2
    len_a, len_b = rng.sample(lengths, 2)
    a = rng.choice(by_length[len_a])
    b = rng.choice(by_length[len_b])
    lat_a, lon_a = to_center_latlon(a)
    lat_b, lon_b = to_center_latlon(b)
    assert initial_bearing(a, b) == pytest.approx(bearing_deg((lat_a, lon_a), (lat_b, lon_b)))


def test_cell_size_degrees_from_precision():
    width, height = cell_size(4)
    step = C.step_size_for_pair(2)
    assert width == pytest.approx(step.lon_step_deg)
    assert height == pytest.approx(step.lat_step_deg)


def test_cell_size_deg_matches_cell_size(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    assert cell_size_deg(loc) == cell_size(loc, unit="deg")


def test_cell_size_km_at_lat(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    width_center, height_center = cell_size_km(loc)
    width_at = cell_size_km(loc, at_lat=10.0)[0]
    assert height_center > 0
    assert width_center > 0
    assert width_at > 0


def test_area_km2_and_diagonal(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    area = area_km2(loc)
    diag = diagonal_km(loc)
    assert area > 0
    assert diag > 0


def test_cell_size_degrees_from_locator(valid_locators):
    loc = _pick_by_length(valid_locators, 6)
    width, height = cell_size(loc)
    step = C.step_size_for_pair(3)
    assert width == pytest.approx(step.lon_step_deg)
    assert height == pytest.approx(step.lat_step_deg)


def test_cell_size_distance_units(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    step = C.step_size_for_pair(len(loc) // 2)
    lat, lon = to_center_latlon(loc)
    half_lon = step.lon_step_deg / 2.0
    half_lat = step.lat_step_deg / 2.0
    expected_width_km = distance_km((lat, lon - half_lon), (lat, lon + half_lon))
    expected_height_km = distance_km((lat - half_lat, lon), (lat + half_lat, lon))
    width_km, height_km = cell_size(loc, unit="km")
    assert width_km == pytest.approx(expected_width_km)
    assert height_km == pytest.approx(expected_height_km)
    width_mi, height_mi = cell_size(loc, unit="miles")
    miles_per_km = 0.621371
    assert width_mi == pytest.approx(expected_width_km * miles_per_km)
    assert height_mi == pytest.approx(expected_height_km * miles_per_km)


def test_from_latlon_precision_rejects_invalid():
    with pytest.raises(PrecisionError):
        from_latlon(0.0, 0.0, precision=10)


def test_from_latlon_fallback_precision():
    loc = from_latlon(51.5, -0.1, precision=6, resolution_deg=0.1)
    assert len(loc.locator) == 4
    loc2 = from_latlon(0, 0, precision=8, resolution_deg=1.0)
    assert len(loc2.locator) == 4


def test_format_locator_truncate(valid_locators):
    loc = _pick_by_length(valid_locators, 6)
    out = format_locator(loc, precision=4, mode="truncate")
    assert out.locator == normalize(loc)[:4]


def test_format_locator_center(valid_locators):
    loc = _pick_by_length(valid_locators, 4)
    out = format_locator(loc, precision=6, mode="center")
    assert len(out.locator) == 6


def test_format_locator_error(valid_locators):
    loc = _pick_by_length(valid_locators, 6)
    with pytest.raises(PrecisionError):
        format_locator(loc, precision=4, mode="error")


def test_adjacent_cardinal_matches_neighbors(valid_locators):
    rng = random.Random(1)
    loc = rng.choice(valid_locators)
    adj = adjacent(loc)
    assert set(adj.keys()) == {"N", "S", "E", "W"}
    cardinal = {g.locator for g in neighbors(loc, diagonals=False)}
    assert {g.locator for g in adj.values()} <= cardinal
    assert all(len(g.locator) == len(loc) for g in adj.values())


def test_adjacent_diagonals_matches_neighbors(valid_locators):
    rng = random.Random(2)
    loc = rng.choice(valid_locators)
    adj = adjacent(loc, diagonals=True)
    assert set(adj.keys()) == {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
    all_dirs = {g.locator for g in neighbors(loc, diagonals=True)}
    assert {g.locator for g in adj.values()} <= all_dirs


def test_step_matches_adjacent(valid_locators):
    rng = random.Random(16)
    loc = rng.choice(valid_locators)
    adj = adjacent(loc, diagonals=False)
    assert step(loc, dlat_cells=1).locator == adj["N"].locator
    assert step(loc, dlat_cells=-1).locator == adj["S"].locator
    assert step(loc, dlon_cells=1).locator == adj["E"].locator
    assert step(loc, dlon_cells=-1).locator == adj["W"].locator


def test_step_zero_returns_same(valid_locators):
    loc = valid_locators[0]
    assert step(loc).locator == normalize(loc)


def test_contains_parent_child(valid_locators):
    rng = random.Random(3)
    longer = [loc for loc in valid_locators if len(loc) >= 4]
    inner = rng.choice(longer)
    outer = parent(inner).locator
    assert contains(outer, inner)
    assert contains(inner, inner)


def test_contains_sibling_false(valid_locators):
    rng = random.Random(4)
    by_length = {}
    for loc in valid_locators:
        by_length.setdefault(len(loc), []).append(loc)
    lengths = [length for length in by_length if length >= 4]
    length = rng.choice(lengths)
    loc = rng.choice(by_length[length])
    outer = parent(loc).locator
    candidates = [c for c in by_length[len(outer)] if c != outer]
    if not candidates:
        pytest.skip("not enough distinct locators")
    other = rng.choice(candidates)
    assert not contains(outer, other)


def test_neighbors_same_precision(valid_locators):
    rng = random.Random(9)
    loc = rng.choice([l for l in valid_locators if len(l) >= 4])
    neigh = neighbors(loc)
    assert len(neigh) > 0
    assert all(len(n.locator) == len(loc) for n in neigh)


def test_parent_children_roundtrip(valid_locators):
    rng = random.Random(10)
    loc = rng.choice([l for l in valid_locators if len(l) >= 4])
    p = parent(loc)
    kids = list(children(p, precision=len(loc)))
    assert loc in [k.locator for k in kids]
