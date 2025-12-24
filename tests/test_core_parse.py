import random

import pytest

from maidenhead import GridSquare, is_valid, normalize, parse, precision_of
from maidenhead.errors import InvalidLocatorError, PrecisionError


def _pick_by_length(valid_locators, length):
    for loc in valid_locators:
        if len(loc) == length:
            return loc
    raise AssertionError(f"no locator with length {length}")


def test_normalize_casing(valid_locators):
    rng = random.Random(6)
    loc = rng.choice(valid_locators)
    expected = normalize(loc)
    assert normalize(loc.lower()) == expected
    assert normalize(loc.upper()) == expected


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


def test_parse_returns_gridsquare(valid_locators):
    loc = _pick_by_length(valid_locators, 6)
    gs = parse(loc)
    assert isinstance(gs, GridSquare)
    assert gs.locator == normalize(loc)
    loc2 = _pick_by_length(valid_locators, 2)
    gs2 = parse(loc2)
    assert gs2.locator == normalize(loc2)
    loc3 = _pick_by_length(valid_locators, 8)
    gs3 = parse(loc3)
    assert gs3.locator == normalize(loc3)


def test_precision_of(valid_locators):
    loc2 = _pick_by_length(valid_locators, 2)
    loc4 = _pick_by_length(valid_locators, 4)
    loc6 = _pick_by_length(valid_locators, 6)
    loc8 = _pick_by_length(valid_locators, 8)
    assert precision_of(loc4) == 4
    assert precision_of(parse(loc6)) == 6
    assert precision_of(loc2) == 2
    assert precision_of(loc8) == 8


def test_normalize_rejects_invalid(invalid_locator_groups):
    length_invalid = invalid_locator_groups["length"][0]
    with pytest.raises(PrecisionError):
        normalize(length_invalid)
    invalid_char = invalid_locator_groups["invalid_character"][0]
    with pytest.raises(InvalidLocatorError):
        normalize(invalid_char)
