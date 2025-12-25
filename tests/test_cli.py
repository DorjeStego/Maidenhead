import random
import sys
from io import StringIO

import pytest

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover - optional in local env
    orjson = None

from maidenhead import normalize, step
from maidenhead.cli import main


def test_cli_normalize(capsys, valid_locators):
    rng = random.Random(5)
    loc = rng.choice(valid_locators)
    code = main(["normalize", loc.swapcase()])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == normalize(loc)


def test_cli_center_csv(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["center", loc, "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    assert "," in captured.out.strip()


def test_cli_bbox_csv(capsys, valid_locators):
    loc = valid_locators[0]
    code = main(["bbox", loc, "--digits", "4", "--csv"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip().count(",") == 3


def test_cli_from_latlon_single_arg(capsys):
    code = main(["from-latlon", "53.365418,-2.574069"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "IO83ri"


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
    assert captured.out.strip().count(",") == 1


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


def test_cli_geojson_feature(capsys, valid_locators):
    if orjson is None:
        pytest.skip("orjson not installed")
    loc = valid_locators[0]
    code = main(["geojson", loc])
    captured = capsys.readouterr()
    assert code == 0
    data = orjson.loads(captured.out.strip())
    assert data["type"] == "Feature"


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
