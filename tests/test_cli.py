import json
import random
import sys
from io import StringIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover - optional in local env
    orjson = None

from maidenhead import normalize, step
from maidenhead.core import to_bbox, to_center_latlon, to_geojson_bbox
from maidenhead.geo import bearing_deg, distance_km
from maidenhead.cli import main


FIXTURES_PATH = Path(__file__).with_name("fixtures_cli.json")


def _load_fixtures():
    with FIXTURES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _run_cli(args, capsys):
    code = main(args)
    captured = capsys.readouterr()
    assert code == 0
    return captured.out.strip()


def test_cli_normalize(capsys, valid_locators):
    rng = random.Random(5)
    loc = rng.choice(valid_locators)
    code = main(["normalize", loc.swapcase()])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == normalize(loc)


def test_cli_center_literal_expected(capsys):
    out = _run_cli(["center", "IO83ri", "--digits", "6"], capsys)
    assert out == "53.354167 -2.541667"


def test_cli_bbox_literal_expected(capsys):
    out = _run_cli(["bbox", "IO83ri", "--digits", "6"], capsys)
    assert out == "53.333333 -2.583333 53.375000 -2.500000"


def test_cli_roundtrip_center_within_bbox(capsys):
    loc = _run_cli(["from-latlon", "53.365418,-2.574069"], capsys)
    center = _run_cli(["center", loc, "--digits", "6"], capsys)
    bbox = _run_cli(["bbox", loc, "--digits", "6"], capsys)
    lat, lon = [float(v) for v in center.split()]
    min_lat, min_lon, max_lat, max_lon = [float(v) for v in bbox.split()]
    assert min_lat <= lat <= max_lat
    assert min_lon <= lon <= max_lon


def test_cli_golden_fixtures(capsys):
    fixtures = _load_fixtures()
    for item in fixtures["center"]:
        out = _run_cli(
            ["center", item["locator"], "--digits", str(item["digits"])],
            capsys,
        )
        assert out == item["output"]
    for item in fixtures["bbox"]:
        out = _run_cli(
            ["bbox", item["locator"], "--digits", str(item["digits"])],
            capsys,
        )
        assert out == item["output"]
    for item in fixtures["from_latlon"]:
        out = _run_cli(
            ["from-latlon", item["latlon"], "--precision", str(item["precision"])],
            capsys,
        )
        assert out == item["output"]
    for item in fixtures["distance"]:
        out = _run_cli(
            ["distance", *item["points"], "--digits", str(item["digits"])],
            capsys,
        )
        assert out == item["output"]
    for item in fixtures["bearing"]:
        out = _run_cli(
            ["bearing", *item["points"], "--digits", str(item["digits"])],
            capsys,
        )
        assert out == item["output"]


def test_cli_center_csv(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["center", loc, "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    lat, lon = to_center_latlon(loc)
    out_lat, out_lon = [float(v) for v in captured.out.strip().split(",")]
    assert out_lat == pytest.approx(round(lat, 4))
    assert out_lon == pytest.approx(round(lon, 4))


def test_cli_bbox_csv(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["bbox", loc, "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    min_lat, min_lon, max_lat, max_lon = to_bbox(loc)
    out_vals = [float(v) for v in captured.out.strip().split(",")]
    expected = [min_lat, min_lon, max_lat, max_lon]
    for out_val, exp in zip(out_vals, expected):
        assert out_val == pytest.approx(round(exp, 4))


def test_cli_bbox_split_single(capsys):
    code = main(["bbox", "IO83ri", "--split", "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    out_vals = [float(v) for v in lines[0].split(",")]
    expected = list(to_bbox("IO83ri"))
    for out_val, exp in zip(out_vals, expected):
        assert out_val == pytest.approx(round(exp, 4))


def test_cli_from_latlon_single_arg(capsys):
    code = main(["from-latlon", "53.365418,-2.574069"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83ri"


def test_cli_from_latlon_space_separated(capsys):
    code = main(["from-latlon", "53.073219", "-3.934023"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83ab"


def test_cli_from_latlon_comma_space(capsys):
    code = main(["from-latlon", "53.073219,", "-3.934023"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83ab"


def test_cli_from_latlon_precision_10(capsys):
    code = main(["from-latlon", "53.365418,-2.574069", "--precision", "10"])
    captured = capsys.readouterr()
    assert code == 0
    assert len(captured.out.strip()) == 10


def test_cli_parts_output(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["parts", loc])
    captured = capsys.readouterr()
    assert code == 0
    assert "field=" in captured.out


def test_cli_size_output(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["size", loc, "--unit", "km", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    out = [float(v) for v in captured.out.strip().split(",")]
    assert len(out) == 2
    assert out[0] > 0.0
    assert out[1] > 0.0


def test_cli_step_output(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["step", loc, "--dlat-cells", "1"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == step(loc, dlat_cells=1).locator


def test_cli_normalize_batch_json_stdin(monkeypatch, capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "io83ri\nfn31pr\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["normalize", "--stdin", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    assert orjson.loads(captured.out.strip()) == ["IO83ri", "FN31pr"]


def test_cli_batch_conflicting_inputs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", StringIO("IO83rj\n"))
    code = main(["normalize", "--stdin", "--file", "locators.txt"])
    captured = capsys.readouterr()
    assert code == 2
    assert "error:" in captured.err


def test_cli_normalize_requires_locator(capsys):
    code = main(["normalize"])
    captured = capsys.readouterr()
    assert code == 2
    assert "error:" in captured.err


def test_cli_from_latlon_batch_invalid_line(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", StringIO("53.36,-2.57,1\n"))
    code = main(["from-latlon", "--stdin", "--format", "plain"])
    captured = capsys.readouterr()
    assert code == 2
    assert "error:" in captured.err


def test_cli_geojson_batch_requires_featurecollection(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", StringIO("IO83rj\n"))
    code = main(["geojson", "--stdin"])
    captured = capsys.readouterr()
    assert code == 2
    assert "error:" in captured.err


def test_cli_center_batch_csv_file(tmp_path, capsys, valid_locators):
    locs = valid_locators[:2]
    file_path = tmp_path / "locs.txt"
    file_path.write_text("\n".join(locs))
    code = main(["center", "--file", str(file_path), "--format", "csv", "--digits", "4"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2
    assert all("," in line for line in lines)


def test_cli_from_latlon_batch_json_stdin(monkeypatch, capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "53.365418,-2.574069\n52.069654,4.271870\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["from-latlon", "--stdin", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    assert orjson.loads(captured.out.strip()) == ["IO83ri", "JO22db"]


def test_cli_format_truncate(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["format", loc, "--precision", "2", "--mode", "truncate"])
    captured = capsys.readouterr()
    assert code == 0
    assert len(captured.out.strip()) == 2


def test_cli_size_at_lat(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["size", loc, "--unit", "km", "--at-lat", "10"])
    captured = capsys.readouterr()
    assert code == 0
    out = [float(v) for v in captured.out.strip().split()]
    assert len(out) == 2
    assert out[0] > 0.0
    assert out[1] > 0.0


def test_cli_area_diagonal(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["area", loc])
    captured = capsys.readouterr()
    assert code == 0
    assert float(captured.out.strip()) > 0.0


def test_cli_distance_comma_space(capsys):
    code = main(["distance", "53.073219,", "-3.934023", "51.5074,-0.1278"])
    captured = capsys.readouterr()
    assert code == 0
    out = float(captured.out.strip())
    expected = distance_km((53.073219, -3.934023), (51.5074, -0.1278))
    assert out == pytest.approx(expected)


def test_cli_distance_space_separated(capsys):
    code = main(["distance", "53.073219", "-3.934023", "51.5074", "-0.1278"])
    captured = capsys.readouterr()
    assert code == 0
    out = float(captured.out.strip())
    expected = distance_km((53.073219, -3.934023), (51.5074, -0.1278))
    assert out == pytest.approx(expected)


def test_cli_utm(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["utm", loc])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "29N"


def test_cli_corners(capsys):
    code = main(["corners", "IO83ri", "--digits", "4"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 4


def test_cli_precision(capsys):
    code = main(["precision", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "6"


def test_cli_neighbors(capsys):
    code = main(["neighbors", "IO83ri", "--no-diagonals"])
    captured = capsys.readouterr()
    assert code == 0
    out = captured.out.strip().split()
    assert len(out) == 4


def test_cli_adjacent(capsys):
    code = main(["adjacent", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 4


def test_cli_wkt_locator(capsys):
    code = main(["wkt", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip().startswith("POLYGON((")


def test_cli_wkt_latlon(capsys):
    code = main(["wkt", "53.365418,-2.574069", "--precision", "6"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip().startswith("POLYGON((")


def test_cli_cover_circle(capsys):
    code = main(["cover-circle", "0.0,0.0", "5", "--precision", "4"])
    captured = capsys.readouterr()
    assert code == 0
    locs = captured.out.strip().split()
    assert "JJ00" in locs


def test_cli_cover_line(capsys):
    code = main(["cover-line", "0.0,0.0", "1.0,1.0", "--precision", "4"])
    captured = capsys.readouterr()
    assert code == 0
    locs = captured.out.strip().split()
    assert "JJ00" in locs


def test_cli_great_circle(capsys):
    code = main(["great-circle", "0.0,0.0", "1.0,1.0", "--points-count", "3"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 3


def test_cli_bearing_bin(capsys):
    code = main(["bearing-bin", "0.0,0.0", "0.0,10.0", "--bin-size", "10"])
    captured = capsys.readouterr()
    assert code == 0
    assert float(captured.out.strip()) == pytest.approx(90.0)


def test_cli_azimuthal_sector(capsys):
    code = main(["azimuthal-sector", "0.0,0.0", "0.0,10.0", "--width", "20"])
    captured = capsys.readouterr()
    assert code == 0
    start, end = [float(v) for v in captured.out.strip().split()]
    assert start == pytest.approx(80.0)
    assert end == pytest.approx(100.0)


def test_cli_midpoint(capsys):
    code = main(["midpoint", "0.0,0.0", "0.0,10.0"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip()


def test_cli_midpoint_geodesic_missing_dependency(capsys):
    code = main(["midpoint", "0.0,0.0", "0.0,10.0", "--method", "geodesic"])
    captured = capsys.readouterr()
    if code == 0:
        assert captured.out.strip()
    else:
        assert code == 2
        assert "geodesic midpoint requires" in captured.err


def test_cli_azimuth_basic(capsys):
    code = main(["azimuth", "IO83ri", "IO84aa", "--digits", "4"])
    captured = capsys.readouterr()
    assert code == 0
    parts = captured.out.strip().split()
    assert len(parts) == 2


def test_cli_azimuth_range(capsys):
    code = main(["azimuth", "IO83ri", "IO84aa", "--range", "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    parts = captured.out.strip().split(",")
    assert len(parts) == 3


def test_cli_initial_bearing(capsys):
    code = main(["initial-bearing", "IO83ri", "IO84aa", "--digits", "4"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip()


def test_cli_parent_default(capsys):
    code = main(["parent", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83"


def test_cli_parent_precision(capsys):
    code = main(["parent", "IO83ri", "--precision", "2"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO"


def test_cli_children_default(capsys):
    code = main(["children", "IO83", "--limit", "5"])
    captured = capsys.readouterr()
    assert code == 0
    out = captured.out.strip().split()
    assert len(out) == 5


def test_cli_children_precision(capsys):
    code = main(["children", "IO", "--precision", "6", "--limit", "3"])
    captured = capsys.readouterr()
    assert code == 0
    out = captured.out.strip().split()
    assert len(out) == 3


def test_cli_contains(capsys):
    code = main(["contains", "IO83", "IO83ri"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "true"


def test_cli_contains_point(capsys):
    code = main(["contains-point", "IO83ri", "53.354167,-2.541667"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "true"


def test_cli_intersects_bbox(capsys):
    code = main(["intersects-bbox", "IO83ri", "53.0", "-3.0", "54.0", "-2.0"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "true"


def test_cli_intersects_polygon(capsys):
    code = main(
        [
            "intersects-polygon",
            "IO83ri",
            "53.0,-3.0",
            "53.0,-2.0",
            "54.0,-2.0",
            "54.0,-3.0",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "true"


def test_cli_geojson_feature(capsys, valid_locators):
    if orjson is None:
        pytest.skip("orjson not installed")
    loc = valid_locators[0]
    code = main(["geojson", loc])
    captured = capsys.readouterr()
    assert code == 0
    data = orjson.loads(captured.out.strip())
    assert data["type"] == "Feature"


def test_cli_geojson_bbox_format(capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    code = main(["geojson", "IO83ri", "--geojson-format", "bbox"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert out == to_geojson_bbox("IO83ri")


def test_cli_geojson_featurecollection_stdin(monkeypatch, capsys, valid_locators):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "\n".join(valid_locators[:2]) + "\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["geojson", "--stdin", "--geojson-format", "featurecollection"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert out["type"] == "FeatureCollection"


def test_cli_cover_circle_batch_csv_stdin(monkeypatch, capsys):
    data = "JJ00 5 4\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["cover-circle", "0.0,0.0", "5", "--precision", "4", "--stdin", "--format", "csv"])
    captured = capsys.readouterr()
    assert code == 0
    line = captured.out.strip()
    assert line
    assert " " not in line


def test_cli_cover_line_batch_csv_stdin(monkeypatch, capsys):
    data = "JJ00 JJ11 4\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["cover-line", "0.0,0.0", "1.0,1.0", "--precision", "4", "--stdin", "--format", "csv"])
    captured = capsys.readouterr()
    assert code == 0
    line = captured.out.strip()
    assert line
    assert "," in line


def test_cli_cover_circle_batch_json_stdin(monkeypatch, capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "JJ00 5 4\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["cover-circle", "0.0,0.0", "5", "--precision", "4", "--stdin", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert isinstance(out, list)
    assert out and isinstance(out[0], list)


def test_cli_cover_line_batch_json_stdin(monkeypatch, capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "JJ00 JJ11 4\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["cover-line", "0.0,0.0", "1.0,1.0", "--precision", "4", "--stdin", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert isinstance(out, list)
    assert out and isinstance(out[0], list)


def test_cli_bulk_center_json(monkeypatch, capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    data = "IO83ri\nJO22db\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "center", "--stdin", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert len(out) == 2
    assert len(out[0]) == 2


def test_cli_bulk_wkt_plain(monkeypatch, capsys):
    data = "IO83ri\n53.365418,-2.574069\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "wkt", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2
    assert all(line.startswith("POLYGON((") for line in lines)


def test_cli_bulk_contains_point(monkeypatch, capsys):
    data = "IO83ri 53.354167 -2.541667\nIO83ri 80 0\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "contains-point", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert lines == ["true", "false"]


def test_cli_bulk_contains(monkeypatch, capsys):
    data = "IO83 IO83ri\nIO83 JO22db\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "contains", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert lines == ["true", "false"]


def test_cli_bulk_intersects_bbox(monkeypatch, capsys):
    data = "IO83ri 53.0 -3.0 54.0 -2.0\nIO83ri 80 0 81 1\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "intersects-bbox", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert lines == ["true", "false"]


def test_cli_bulk_azimuth(monkeypatch, capsys):
    data = "IO83ri IO84aa\nIO83ri IO83ri\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "azimuth", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2
    assert len(lines[0].split()) == 2


def test_cli_bulk_initial_bearing(monkeypatch, capsys):
    data = "IO83ri IO84aa\nIO83ri IO83ri\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "initial-bearing", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2


def test_cli_bulk_intersects_polygon(monkeypatch, capsys):
    data = "IO83ri 53.0,-3.0 53.0,-2.0 54.0,-2.0 54.0,-3.0\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "intersects-polygon", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert lines == ["true"]


def test_cli_bulk_neighbors(monkeypatch, capsys):
    data = "IO83ri\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "neighbors", "--stdin", "--no-diagonals"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    assert len(lines[0].split()) == 4


def test_cli_bulk_adjacent(monkeypatch, capsys):
    data = "IO83ri\n"
    monkeypatch.setattr(sys, "stdin", StringIO(data))
    code = main(["bulk", "adjacent", "--stdin"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    assert ":" in lines[0]


def test_cli_bbox_split_command(capsys):
    code = main(["bbox-split", "0", "170", "10", "-170", "--csv", "--digits", "4"])
    captured = capsys.readouterr()
    assert code == 0
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2


def test_cli_bbox_split_list_json(capsys):
    if orjson is None:
        pytest.skip("orjson not installed")
    code = main(["bbox-split-list", "0", "170", "10", "-170", "--format", "json"])
    captured = capsys.readouterr()
    assert code == 0
    out = orjson.loads(captured.out.strip())
    assert len(out) == 2


def test_cli_validate_invalid(invalid_locators):
    for loc in invalid_locators:
        code = main(["validate", loc])
        assert code == 2


def test_cli_validate_valid_lengths(valid_locators):
    for loc in valid_locators:
        code = main(["validate", loc])
        assert code == 0


def test_cli_validate_print_valid(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["validate", loc, "--print"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "valid"


def test_cli_validate_print_invalid(capsys, invalid_locators):
    loc = invalid_locators[0]
    code = main(["validate", loc, "--print"])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out.strip() == "invalid"
