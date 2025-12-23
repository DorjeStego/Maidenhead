from maidenhead import children, from_latlon, neighbors, normalize, parent, to_bbox, to_center_latlon


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


def test_neighbors_same_precision():
    loc = "IO83ri"
    neigh = neighbors(loc)
    assert len(neigh) > 0
    assert all(len(n.locator) == len(loc) for n in neigh)


def test_parent_children_roundtrip():
    loc = "IO83ri"
    p = parent(loc)
    assert p.locator == "IO83"
    kids = list(children(p, precision=6))
    assert "IO83ri" in [k.locator for k in kids]
