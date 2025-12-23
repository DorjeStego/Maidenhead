import pytest

from maidenhead import GridSquare, is_valid, normalize, parse, precision_of
from maidenhead.errors import InvalidLocatorError, PrecisionError


def test_normalize_casing():
    assert normalize("io83ri") == "IO83ri"
    assert normalize("Io83RI") == "IO83ri"
    assert normalize("IO83") == "IO83"


def test_is_valid_basic(valid_locators, invalid_locators):
    for loc in valid_locators:
        assert is_valid(loc)
    for loc in invalid_locators:
        assert not is_valid(loc)


def test_valid_locators_are_in_field_range(valid_locators):
    allowed = set("ABCDEFGHIJKLMNOPQR")
    for loc in valid_locators:
        assert loc[0] in allowed
        assert loc[1] in allowed


def test_parse_returns_gridsquare():
    gs = parse("IO83ri")
    assert isinstance(gs, GridSquare)
    assert gs.locator == "IO83ri"
    gs2 = parse("IO")
    assert gs2.locator == "IO"
    gs3 = parse("IO83ri12")
    assert gs3.locator == "IO83ri12"


def test_precision_of():
    assert precision_of("IO83") == 4
    assert precision_of(parse("IO83ri")) == 6
    assert precision_of("IO") == 2
    assert precision_of("IO83ri12") == 8


def test_normalize_rejects_invalid():
    with pytest.raises(PrecisionError):
        normalize("IO8")
    with pytest.raises(PrecisionError):
        normalize("IO83ri1")
    with pytest.raises(InvalidLocatorError):
        normalize("IO83r!")
    with pytest.raises(InvalidLocatorError):
        normalize("IO83r@")
