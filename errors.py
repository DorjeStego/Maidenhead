# maidenhead/errors.py
from __future__ import annotations


class MaidenheadError(Exception):
    """
    Base exception for the maidenhead package.

    Catch this to handle any library-specific error without also catching
    unrelated ValueError/TypeError from user code.
    """


class PrecisionError(MaidenheadError, ValueError):
    """
    Raised when a requested precision is invalid (e.g. odd length, <2, mismatch).
    Inherits ValueError for ergonomics with existing code patterns.
    """


class InvalidLocatorError(MaidenheadError, ValueError):
    """
    Raised when a locator string is malformed or contains invalid characters.
    Inherits ValueError for ergonomics.
    """


class OutOfRangeError(MaidenheadError, ValueError):
    """
    Raised when latitude/longitude inputs are out of valid bounds.
    Inherits ValueError for ergonomics.
    """


class UnsupportedError(MaidenheadError):
    """
    Raised when a feature is intentionally not supported (e.g. a requested method
    or precision mode not implemented).
    """


class MissingDependencyError(MaidenheadError, ImportError):
    """
    Raised when an optional feature requires a dependency that is not installed.
    Inherits ImportError to match typical expectations.
    """


def require(condition: bool, exc: type[Exception], message: str) -> None:
    """
    Tiny internal helper to keep core code readable.

    Example:
        require(len(locator) % 2 == 0, PrecisionError, "precision must be even")
    """
    if not condition:
        raise exc(message)
