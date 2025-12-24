# maidenhead/errors.py
from __future__ import annotations

from typing import Type, Union

__all__ = [
    "MaidenheadError",
    "PrecisionError",
    "InvalidLocatorError",
    "OutOfRangeError",
    "UnsupportedError",
    "MissingDependencyError",
    "require",
]


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

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.context = context

    def __str__(self) -> str:
        return _format_with_context(super().__str__(), self.context)


class InvalidLocatorError(MaidenheadError, ValueError):
    """
    Raised when a locator string is malformed or contains invalid characters.
    Inherits ValueError for ergonomics.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.context = context

    def __str__(self) -> str:
        return _format_with_context(super().__str__(), self.context)


class OutOfRangeError(MaidenheadError, ValueError):
    """
    Raised when latitude/longitude inputs are out of valid bounds.
    Inherits ValueError for ergonomics.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.context = context

    def __str__(self) -> str:
        return _format_with_context(super().__str__(), self.context)


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


ExceptionType = Type[Exception]
ExceptionLike = Union[ExceptionType, Exception]


def _format_with_context(message: str, context: dict[str, object]) -> str:
    if not context:
        return message
    parts = ", ".join(f"{key}={context[key]!r}" for key in sorted(context))
    return f"{message} ({parts})"


def require(condition: bool, exc: ExceptionLike, message: str, **context: object) -> None:
    """
    Tiny internal helper to keep core code readable.

    Example:
        require(len(locator) % 2 == 0, PrecisionError, "precision must be even")
    """
    if not condition:
        if isinstance(exc, Exception):
            raise exc
        if context:
            try:
                raise exc(message, **context)
            except TypeError:
                raise exc(message)
        raise exc(message)
