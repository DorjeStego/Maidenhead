import random

import pytest

from maidenhead import GridSquare, is_valid, normalize, parse, precision_of
from maidenhead.errors import InvalidLocatorError, PrecisionError


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


def test_parse_returns_gridsquare(sample_valid_locators):
    loc = sample_valid_locators(lengths=[6], seed=301)[0]
    gs = parse(loc)
    assert isinstance(gs, GridSquare)
    assert gs.locator == normalize(loc)
    loc2 = sample_valid_locators(lengths=[2], seed=302)[0]
    gs2 = parse(loc2)
    assert gs2.locator == normalize(loc2)
    loc3 = sample_valid_locators(lengths=[8], seed=303)[0]
    gs3 = parse(loc3)
    assert gs3.locator == normalize(loc3)
    loc4 = sample_valid_locators(lengths=[10], seed=304)[0]
    gs4 = parse(loc4)
    assert gs4.locator == normalize(loc4)


def test_precision_of(sample_valid_locators):
    loc2 = sample_valid_locators(lengths=[2], seed=305)[0]
    loc4 = sample_valid_locators(lengths=[4], seed=306)[0]
    loc6 = sample_valid_locators(lengths=[6], seed=307)[0]
    loc8 = sample_valid_locators(lengths=[8], seed=308)[0]
    loc10 = sample_valid_locators(lengths=[10], seed=309)[0]
    assert precision_of(loc4) == 4
    assert precision_of(parse(loc6)) == 6
    assert precision_of(loc2) == 2
    assert precision_of(loc8) == 8
    assert precision_of(loc10) == 10


def test_precision_of_rejects_too_long():
    with pytest.raises(PrecisionError):
        precision_of("IO91wm34aa55")


def test_normalize_rejects_invalid(invalid_locator_groups):
    length_invalid = invalid_locator_groups["length"][0]
    with pytest.raises(PrecisionError):
        normalize(length_invalid)
    invalid_char = invalid_locator_groups["invalid_character"][0]
    with pytest.raises(InvalidLocatorError):
        normalize(invalid_char)
