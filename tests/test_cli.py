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


def test_cli_validate_invalid(invalid_locators):
    for loc in invalid_locators:
        code = main(["validate", loc])
        assert code == 2


def test_cli_validate_valid_lengths(valid_locators):
    for loc in valid_locators:
        code = main(["validate", loc])
        assert code == 0
