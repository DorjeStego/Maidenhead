import random

import pytest

import maidenhead.core as core
from maidenhead import (
    adjacent,
    azimuth,
    cover_circle,
    cover_line,
    contains_point,
    intersects_bbox,
    intersects_polygon,
    cell_size,
    cell_size_deg,
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
    split_bbox,
    split_bbox_list,
    to_center_latlon,
    to_geojson_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_bbox,
    to_geojson_envelope,
    to_wkt,
    to_utm_zone,
)
from maidenhead import constants as C
from maidenhead.errors import PrecisionError
from maidenhead.geo import bearing_deg, distance_km


def test_center_roundtrip_locators(valid_locators):
    for loc in valid_locators:
        lat, lon = to_center_latlon(loc)
        back = from_latlon(lat, lon, precision=len(loc))
        assert back.locator == normalize(loc)


def test_from_latlon_precision_10_roundtrip():
    loc = from_latlon(53.365418, -2.574069, precision=10)
    assert len(loc.locator) == 10
    lat, lon = to_center_latlon(loc)
    back = from_latlon(lat, lon, precision=10)
    assert back.locator == loc.locator


def test_bbox_contains_center(valid_locators):
    for loc in valid_locators:
        min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
        lat, lon = to_center_latlon(loc)
        assert min_lat <= lat <= max_lat
        assert min_lon <= lon <= max_lon


def test_from_latlon_north_pole_bbox():
    loc = from_latlon(90.0, 0.0, precision=6)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    assert max_lat == pytest.approx(90.0)
    lat, lon = to_center_latlon(loc)
    assert min_lat <= lat <= max_lat
    assert min_lon <= lon <= max_lon
    assert contains_point(loc, 90.0, 0.0)


def test_from_latlon_south_pole_bbox():
    loc = from_latlon(-90.0, 0.0, precision=6)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    assert min_lat == pytest.approx(-90.0)
    lat, lon = to_center_latlon(loc)
    assert min_lat <= lat <= max_lat
    assert min_lon <= lon <= max_lon
    assert contains_point(loc, -90.0, 0.0)


def test_bbox_split_none_for_standard_cells(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=409)[0]
    assert to_bbox_split(loc) is None


def test_bbox_split_none_at_dateline_edge():
    loc = from_latlon(0.0, 179.999, precision=6)
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    assert max_lon == pytest.approx(180.0)
    result = to_bbox_split(loc)
    assert result is not None
    assert result[0] == pytest.approx(min_lat)
    assert result[1] == pytest.approx(min_lon)
    assert result[2] == pytest.approx(max_lat)
    assert result[3] == pytest.approx(180.0)


def test_split_bbox_crosses_antimeridian():
    bbox = (0.0, 170.0, 10.0, -170.0)
    west, east = split_bbox(bbox)
    assert west == (0.0, 170.0, 10.0, 180.0)
    assert east == (0.0, -180.0, 10.0, -170.0)


def test_split_bbox_none_for_normalized_bbox():
    bbox = (0.0, 190.0, 10.0, 200.0)
    assert split_bbox(bbox) is None


def test_split_bbox_list_outputs():
    bbox = (0.0, 170.0, 10.0, -170.0)
    out = split_bbox_list(bbox)
    assert out == [(0.0, 170.0, 10.0, 180.0), (0.0, -180.0, 10.0, -170.0)]
    assert split_bbox_list((0.0, 179.0, 10.0, 180.0)) == [(0.0, 179.0, 10.0, 180.0)]


def test_bbox_split_crosses_antimeridian_east(monkeypatch):
    def fake_to_bbox(_locator):
        return (0.0, 150.0, 10.0, 190.0)

    monkeypatch.setattr(core, "to_bbox", fake_to_bbox)
    west, east = to_bbox_split("AA00aa")
    assert west == (0.0, 150.0, 10.0, 180.0)
    assert east == (0.0, -180.0, 10.0, -170.0)


def test_bbox_split_crosses_antimeridian_west(monkeypatch):
    def fake_to_bbox(_locator):
        return (0.0, -200.0, 10.0, -160.0)

    monkeypatch.setattr(core, "to_bbox", fake_to_bbox)
    west, east = to_bbox_split("AA00aa")
    assert west == (0.0, 160.0, 10.0, 180.0)
    assert east == (0.0, -180.0, 10.0, -160.0)


def test_geojson_polygon_matches_bbox(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=410)[0]
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    geojson = to_geojson_polygon(loc)
    assert geojson["type"] == "Polygon"
    ring = geojson["coordinates"][0]
    assert ring[0] == [min_lon, min_lat]
    assert ring[1] == [max_lon, min_lat]
    assert ring[2] == [max_lon, max_lat]
    assert ring[3] == [min_lon, max_lat]
    assert ring[4] == [min_lon, min_lat]


def test_geojson_feature(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=411)[0]
    feature = to_geojson_feature(loc, properties={"name": "cell"})
    assert feature["type"] == "Feature"
    assert feature["properties"]["name"] == "cell"
    assert feature["geometry"]["type"] == "Polygon"


def test_geojson_feature_collection(sample_valid_locators):
    locs = sample_valid_locators(lengths=[4, 6], seed=412, count=1)
    fc = to_geojson_feature_collection(locs, properties_fn=lambda l: {"loc": l})
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 2
    assert fc["features"][0]["properties"]["loc"] == locs[0]


def test_geojson_bbox_and_envelope(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=413)[0]
    bbox = to_geojson_bbox(loc)
    env = to_geojson_envelope(loc)
    assert env["bbox"] == bbox
    assert env["type"] == "Polygon"


def test_geojson_point_inputs():
    point = (10.5, 20.25)
    polygon = to_geojson_polygon(point)
    assert polygon["type"] == "Point"
    assert polygon["coordinates"] == [point[1], point[0]]
    bbox = to_geojson_bbox(point)
    assert bbox == [point[1], point[0], point[1], point[0]]
    env = to_geojson_envelope(point)
    assert env["type"] == "Point"
    assert env["bbox"] == bbox
    feature = to_geojson_feature(point)
    assert feature["geometry"]["type"] == "Point"


def test_wkt_matches_bbox(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=414)[0]
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    wkt = to_wkt(loc)
    expected = (
        f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )
    assert wkt == expected


def test_wkt_point_input():
    point = (10.5, 20.25)
    assert to_wkt(point) == "POINT(20.25 10.5)"


def test_contains_point_and_intersects_bbox(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=415)[0]
    lat, lon = to_center_latlon(loc)
    assert contains_point(loc, lat, lon)
    assert not contains_point(loc, 89.9, 0.0)
    bbox = to_bbox(loc)
    assert intersects_bbox(loc, bbox)
    assert not intersects_bbox(loc, (80.0, 0.0, 85.0, 10.0))


def test_intersects_bbox_dateline_wrap():
    loc = from_latlon(0.0, 179.0, precision=4)
    assert intersects_bbox(loc, (-1.0, 170.0, 1.0, -170.0))
    assert not intersects_bbox(loc, (-1.0, -20.0, 1.0, -10.0))


def test_intersects_polygon(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=416)[0]
    lat, lon = to_center_latlon(loc)
    poly = [
        (lat - 0.1, lon - 0.1),
        (lat - 0.1, lon + 0.1),
        (lat + 0.1, lon + 0.1),
        (lat + 0.1, lon - 0.1),
    ]
    assert intersects_polygon(loc, poly)
    far_poly = [(80.0, 0.0), (80.0, 1.0), (81.0, 1.0), (81.0, 0.0)]
    assert not intersects_polygon(loc, far_poly)


def test_intersects_polygon_edge_crossing(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=417)[0]
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    mid_lat = (min_lat + max_lat) / 2.0
    poly = [
        (mid_lat - 0.01, min_lon - 0.1),
        (mid_lat - 0.01, max_lon + 0.1),
        (mid_lat + 0.01, max_lon + 0.1),
        (mid_lat + 0.01, min_lon - 0.1),
    ]
    assert intersects_polygon(loc, poly)


def test_intersects_polygon_dateline_wrap():
    loc = from_latlon(0.0, 179.0, precision=4)
    lat, lon = to_center_latlon(loc)
    poly = [
        (lat - 0.5, 179.5),
        (lat - 0.5, -179.5),
        (lat + 0.5, -179.5),
        (lat + 0.5, 179.5),
    ]
    assert intersects_polygon(loc, poly)


def test_cover_circle_includes_center():
    center = (0.0, 0.0)
    loc = from_latlon(*center, precision=6)
    out = cover_circle(center, radius_km=5.0, precision=6)
    assert loc.locator in [g.locator for g in out]


def test_cover_circle_dateline_wrap():
    center = (0.0, 179.5)
    out = cover_circle(center, radius_km=1200.0, precision=4)
    lons = [to_center_latlon(loc)[1] for loc in out]
    assert any(lon > 170.0 for lon in lons)
    assert any(lon < -170.0 for lon in lons)


def test_cover_line_includes_endpoints():
    a = (0.0, 0.0)
    b = (1.0, 1.0)
    loc_a = from_latlon(*a, precision=4)
    loc_b = from_latlon(*b, precision=4)
    out = cover_line(a, b, precision=4)
    locs = {g.locator for g in out}
    assert loc_a.locator in locs
    assert loc_b.locator in locs


def test_cover_line_dateline_wrap():
    a = (0.0, 179.0)
    b = (0.0, -179.0)
    out = cover_line(a, b, precision=4)
    lons = [to_center_latlon(loc)[1] for loc in out]
    assert any(lon > 170.0 for lon in lons)
    assert any(lon < -170.0 for lon in lons)


def test_to_utm_zone():
    loc = from_latlon(0.0, 0.0, precision=4)
    assert to_utm_zone(loc) == "31N"
    loc_s = from_latlon(-10.0, 33.0, precision=4)
    assert to_utm_zone(loc_s) == "36S"


def test_corners_match_bbox(sample_valid_locators):
    locs = sample_valid_locators(lengths=[4, 6, 8, 10], seed=418)
    for loc in locs:
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


def test_cell_size_deg_matches_cell_size(sample_valid_locators):
    locs = sample_valid_locators(lengths=[2, 4, 6, 8, 10], seed=401)
    for loc in locs:
        assert cell_size_deg(loc) == cell_size(loc, unit="deg")


def test_cell_size_km_at_lat(sample_valid_locators):
    locs = sample_valid_locators(lengths=[2, 4, 6, 8, 10], seed=402)
    for loc in locs:
        width_center, height_center = cell_size(loc, unit="km")
        width_at = cell_size(loc, unit="km", at_lat=10.0)[0]
        assert height_center > 0
        assert width_center > 0
        assert width_at > 0


def test_area_km2_and_diagonal(sample_valid_locators):
    locs = sample_valid_locators(lengths=[2, 4, 6, 8, 10], seed=403)
    for loc in locs:
        area = area_km2(loc)
        diag = diagonal_km(loc)
        assert area > 0
        assert diag > 0


def test_cell_size_degrees_from_locator(sample_valid_locators):
    locs = sample_valid_locators(lengths=[2, 4, 6, 8, 10], seed=404)
    for loc in locs:
        width, height = cell_size(loc)
        step = C.step_size_for_pair(len(loc) // 2)
        assert width == pytest.approx(step.lon_step_deg)
        assert height == pytest.approx(step.lat_step_deg)


def test_cell_size_distance_units(sample_valid_locators):
    locs = sample_valid_locators(lengths=[2, 4, 6, 8, 10], seed=405)
    miles_per_km = 0.621371
    for loc in locs:
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
        assert width_mi == pytest.approx(expected_width_km * miles_per_km)
        assert height_mi == pytest.approx(expected_height_km * miles_per_km)


def test_from_latlon_precision_rejects_invalid():
    with pytest.raises(PrecisionError):
        from_latlon(0.0, 0.0, precision=12)


def test_from_latlon_fallback_precision():
    loc = from_latlon(51.5, -0.1, precision=6, resolution_deg=0.1)
    assert len(loc.locator) == 4
    loc2 = from_latlon(0, 0, precision=8, resolution_deg=1.0)
    assert len(loc2.locator) == 4


def test_format_locator_truncate(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=406)[0]
    out = format_locator(loc, precision=4, mode="truncate")
    assert out.locator == normalize(loc)[:4]


def test_format_locator_center(sample_valid_locators):
    loc = sample_valid_locators(lengths=[4], seed=407)[0]
    out = format_locator(loc, precision=6, mode="center")
    assert len(out.locator) == 6


def test_format_locator_error(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=408)[0]
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


def test_step_zero_returns_same(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=419)[0]
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


def test_contains_dateline_wrap(locator_cases, monkeypatch):
    outer = next(loc for loc in locator_cases["valid_locators"]["2"]["global"] if loc == "RJ")
    inner = next(loc for loc in locator_cases["valid_locators"]["4"]["global"] if loc == "RJ80")
    original_to_bbox = core.to_bbox

    def _fake_to_bbox(locator):
        if locator == outer:
            return (0.0, 170.0, 1.0, -170.0)
        return original_to_bbox(locator)

    monkeypatch.setattr(core, "to_bbox", _fake_to_bbox)
    assert contains(outer, inner)


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
