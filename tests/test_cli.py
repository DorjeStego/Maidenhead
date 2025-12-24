import random

from maidenhead import normalize
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
