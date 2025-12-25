import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if "maidenhead" in sys.modules:
    mod = sys.modules["maidenhead"]
    mod_path = getattr(mod, "__file__", "")
    if mod_path and not Path(mod_path).resolve().is_relative_to(SRC):
        for name in list(sys.modules):
            if name == "maidenhead" or name.startswith("maidenhead."):
                sys.modules.pop(name, None)


@pytest.fixture(scope="session")
def locator_cases():
    path = Path(__file__).with_name("locators.json")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _flatten_invalid_locators(invalid_locators):
    if isinstance(invalid_locators, list):
        return invalid_locators
    if isinstance(invalid_locators, dict):
        flattened = []
        for values in invalid_locators.values():
            flattened.extend(values)
        return flattened
    raise TypeError("invalid_locators must be a list or dict")


def _flatten_valid_locators(valid_locators):
    if isinstance(valid_locators, list):
        return valid_locators
    if isinstance(valid_locators, dict):
        flattened = []
        for length_map in valid_locators.values():
            for values in length_map.values():
                flattened.extend(values)
        return flattened
    raise TypeError("valid_locators must be a list or dict")


@pytest.fixture(scope="session")
def valid_locators(locator_cases):
    return _flatten_valid_locators(locator_cases["valid_locators"])


@pytest.fixture(scope="session")
def invalid_locators(locator_cases):
    return _flatten_invalid_locators(locator_cases["invalid_locators"])


@pytest.fixture(scope="session")
def valid_locator_groups(locator_cases):
    valid_locators = locator_cases["valid_locators"]
    if not isinstance(valid_locators, dict):
        raise TypeError("valid_locators must be a dict for grouped access")
    return valid_locators


@pytest.fixture(scope="session")
def invalid_locator_groups(locator_cases):
    invalid_locators = locator_cases["invalid_locators"]
    if not isinstance(invalid_locators, dict):
        raise TypeError("invalid_locators must be a dict for grouped access")
    return invalid_locators
