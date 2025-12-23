# maidenhead/mh_types.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Iterator, Optional, Sequence, Union, overload

from .errors import InvalidLocatorError, PrecisionError

LocatorLike = Union[str, "GridSquare"]

class PairKind(str, Enum):
    """The expected character class of each 2-character pair in a Maidenhead locator."""
    LETTERS = "letters"
    DIGITS = "digits"

@dataclass(frozen=True, slots=True)
class LocatorToken:
    """
    A 2-character token of a Maidenhead locator (pair), used to make parsing/normalization easier.

    pair_index is 1-based:
      1 => field (letters), 2 => square (digits), 3 => subsquare (letters), 4 => ext (digits), ...
    """
    pair_index: int
    kind: PairKind
    text: str

    def __post_init__(self) -> None:
        if self.pair_index < 1:
            raise ValueError("pair_index must be >= 1")
        if len(self.text) != 2:
            raise ValueError("LocatorToken.text must be exactly 2 characters")

def expected_pair_kind(pair_index: int) -> PairKind:
    """
    Returns the expected PairKind for the given 1-based pair index.

    Maidenhead alternates:
      1: letters, 2: digits, 3: letters, 4: digits, ...
    """
    if pair_index < 1:
        raise ValueError("pair_index must be >= 1")
    return PairKind.LETTERS if (pair_index % 2 == 1) else PairKind.DIGITS


def validate_precision(precision: int) -> int:
    """
    Validate a Maidenhead precision value (string length in characters).
    Must be even and >= 2.
    """
    if not isinstance(precision, int):
        raise PrecisionError(f"precision must be int, got {type(precision).__name__}")
    if precision < 2:
        raise PrecisionError("precision must be >= 2 characters")
    if precision % 2 != 0:
        raise PrecisionError("precision must be an even number of characters (2, 4, 6, ...)")
    return precision


def precision_of(locator: str) -> int:
    """Return precision (character length) of locator, after basic sanity checks."""
    if not isinstance(locator, str):
        raise InvalidLocatorError(f"locator must be str, got {type(locator).__name__}")
    return validate_precision(len(locator))


def iter_tokens(locator: str) -> Iterator[LocatorToken]:
    """
    Yield 2-character tokens from a locator string.

    This does NOT normalize or validate the content beyond length/precision.
    Intended for use by core.parse()/core.normalize() after they do their own
    preprocessing (trim, case handling, strict checks, etc.).
    """
    p = precision_of(locator)
    for i in range(0, p, 2):
        pair_index = (i // 2) + 1
        yield LocatorToken(
            pair_index=pair_index,
            kind=expected_pair_kind(pair_index),
            text=locator[i : i + 2],
        )


@dataclass(frozen=True, slots=True)
class GridSquare:
    """
    Immutable value object representing a Maidenhead grid square at a given precision.

    locator is expected to be in canonical form (e.g. "IO91wm", "FN31pr", ...).
    The library's parse()/normalize() functions should produce canonical locators.

    precision is stored for convenience and must match len(locator).
    """
    locator: str
    precision: int = field(default=0)

    def __post_init__(self) -> None:
        if not isinstance(self.locator, str):
            raise InvalidLocatorError(f"locator must be str, got {type(self.locator).__name__}")

        loc_len = len(self.locator)
        validate_precision(loc_len)

        if self.precision in (0, None):  # allow default construction
            object.__setattr__(self, "precision", loc_len)
        else:
            validate_precision(self.precision)
            if self.precision != loc_len:
                raise PrecisionError(
                    f"precision ({self.precision}) does not match locator length ({loc_len})"
                )

    def __str__(self) -> str:
        return self.locator

    def __repr__(self) -> str:
        return f"GridSquare(locator={self.locator!r}, precision={self.precision})"

    def __len__(self) -> int:
        return self.precision

    # ---- Convenience constructors ----

    @classmethod
    def parse(cls, locator: str, *, allow_extended: bool = True) -> "GridSquare":
        """
        Parse and validate a locator string using core.parse(), returning GridSquare.
        """
        from .core import parse as _parse  # lazy to avoid circular import
        return _parse(locator, allow_extended=allow_extended)

    # ---- Geometry properties (delegated to core) ----

    @property
    def center(self) -> tuple[float, float]:
        """(lat, lon) of the center point of this grid cell."""
        from .core import to_center_latlon  # lazy import
        return to_center_latlon(self)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(min_lat, min_lon, max_lat, max_lon) bounding box of this grid cell."""
        from .core import to_bbox  # lazy import
        return to_bbox(self)

    # ---- Topology helpers (delegated to core) ----

    def parent(self, target_precision: Optional[int] = None) -> "GridSquare":
        """
        Return a parent (less precise) locator.

        If target_precision is None, drops one pair (e.g. 6->4, 4->2).
        """
        from .core import parent as _parent  # lazy import
        return _parent(self, precision=target_precision)

    def children(self, child_precision: int) -> Iterable["GridSquare"]:
        """
        Yield child cells at a finer precision.
        Potentially large if you expand multiple levels.
        """
        from .core import children as _children  # lazy import
        return _children(self, precision=child_precision)

    def neighbors(self, *, ring: int = 1, diagonals: bool = True) -> list["GridSquare"]:
        """Return neighboring cells at the same precision."""
        from .core import neighbors as _neighbors  # lazy import
        return _neighbors(self, ring=ring, diagonals=diagonals)

    def as_precision(self, precision: int) -> "GridSquare":
        """
        Convert to a different precision:
          - if precision < self.precision => truncate to parent
          - if precision == self.precision => return self
          - if precision > self.precision => returns the cell containing this cell's center
            at the requested precision (deterministic, but not a full 'children' expansion).
        """
        validate_precision(precision)
        if precision == self.precision:
            return self
        if precision < self.precision:
            return self.parent(target_precision=precision)

        # Deterministic "zoom in" choice: use the center point
        from .core import from_latlon  # lazy import
        lat, lon = self.center
        return from_latlon(lat, lon, precision=precision)
