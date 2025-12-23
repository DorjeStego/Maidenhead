# maidenhead/constants.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

PairKind = Literal["letters", "digits"]

# ----------------------------
# Core alphabets / ranges
# ----------------------------

A_ORD: int = ord("A")
a_ORD: int = ord("a")

LETTERS_UPPER: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LETTERS_LOWER: str = "abcdefghijklmnopqrstuvwxyz"
DIGITS: str = "0123456789"

# Maidenhead basics:
# Longitude spans 360 degrees (-180 .. +180)
# Latitude spans 180 degrees (-90  .. +90)
LON_SPAN_DEG: float = 360.0
LAT_SPAN_DEG: float = 180.0

LON_MIN_DEG: float = -180.0
LON_MAX_DEG: float = 180.0
LAT_MIN_DEG: float = -90.0
LAT_MAX_DEG: float = 90.0


# ----------------------------
# Per-pair base sizes
# ----------------------------
#
# Pair index is 1-based:
#   1: Field      (letters) base 18 in the original spec (A-R) commonly,
#      but in practice most implementations allow A-X for robustness.
#      We'll explicitly set the canonical bases used by Maidenhead:
#        - Field longitude: 18 (A-R), latitude: 18 (A-R)
#   2: Square     (digits)  base 10
#   3: Subsquare  (letters) base 24 (a-x)
#   4: Extended   (digits)  base 10
#   5: Extended   (letters) base 24 (a-x)
#
# Pattern continues with alternating digits(10)/letters(24) beyond pair 3.
#
# NOTE: Pair 1 is special: base 18 not 24.

FIELD_BASE: int = 18          # A-R
SQUARE_BASE: int = 10         # 0-9
SUBSQUARE_BASE: int = 24      # a-x

EXT_DIGIT_BASE: int = 10      # 0-9
EXT_LETTER_BASE: int = 24     # a-x


def pair_kind(pair_index: int) -> PairKind:
    """Odd pair indexes are letters, even are digits."""
    if pair_index < 1:
        raise ValueError("pair_index must be >= 1")
    return "letters" if (pair_index % 2 == 1) else "digits"


def lon_lat_bases_for_pair(pair_index: int) -> tuple[int, int]:
    """
    Return (lon_base, lat_base) for the given 1-based pair index.

    Bases are the number of bins in that pair for each axis.
    For classic Maidenhead they are the same for lon and lat at each pair.
    """
    if pair_index == 1:
        return (FIELD_BASE, FIELD_BASE)
    if pair_index == 2:
        return (SQUARE_BASE, SQUARE_BASE)
    if pair_index == 3:
        return (SUBSQUARE_BASE, SUBSQUARE_BASE)

    # Beyond subsquare: alternate 10 (digits) / 24 (letters)
    if pair_kind(pair_index) == "digits":
        return (EXT_DIGIT_BASE, EXT_DIGIT_BASE)
    return (EXT_LETTER_BASE, EXT_LETTER_BASE)


# ----------------------------
# Step sizes per pair
# ----------------------------

@dataclass(frozen=True, slots=True)
class StepSize:
    """
    Degree step size of a single increment at a given pair index.
    For pair_index i, step is the cell size contributed by that pair
    after all previous pairs subdivide the world.
    """
    pair_index: int
    lon_step_deg: float
    lat_step_deg: float


def step_size_for_pair(pair_index: int) -> StepSize:
    """
    Compute the degree step size for the given pair index.
    """
    if pair_index < 1:
        raise ValueError("pair_index must be >= 1")

    lon_step = LON_SPAN_DEG
    lat_step = LAT_SPAN_DEG

    # Each pair subdivides the current cell by its base along each axis.
    # Step size at pair i is the cell size AFTER applying pair i.
    for i in range(1, pair_index + 1):
        lon_base, lat_base = lon_lat_bases_for_pair(i)
        lon_step /= lon_base
        lat_step /= lat_base

    return StepSize(pair_index=pair_index, lon_step_deg=lon_step, lat_step_deg=lat_step)


# Precompute common ones (saves a bit of repeated work and serves as documentation).
STEP_FIELD = step_size_for_pair(1)      # 20° lon, 10° lat
STEP_SQUARE = step_size_for_pair(2)     # 2° lon, 1° lat
STEP_SUBSQUARE = step_size_for_pair(3)  # 5' lon, 2.5' lat
STEP_EXT4 = step_size_for_pair(4)
STEP_EXT5 = step_size_for_pair(5)


# ----------------------------
# Canonical character sets per pair
# ----------------------------

FIELD_CHARS_UPPER: str = "ABCDEFGHIJKLMNOPQR"  # A-R (18)
SUBSQUARE_CHARS_LOWER: str = "abcdefghijklmnopqrstuvwx"  # a-x (24)

DIGIT_CHARS: str = DIGITS

# For tolerant parsing you may accept A-X/a-x for pair 1, but canonical output should be A-R.
# Keep these distinct so core can choose strict vs tolerant behavior.
FIELD_CHARS_TOLERANT_UPPER: str = "ABCDEFGHIJKLMNOPQRSTUVWX"  # A-X (24)


def canonical_letter_range_for_pair(pair_index: int) -> tuple[str, str]:
    """
    Return (allowed_upper, allowed_lower) for a letter pair.
    Used for strict validation/canonicalization.
    """
    if pair_kind(pair_index) != "letters":
        raise ValueError("pair_index must refer to a letters pair")
    if pair_index == 1:
        return (FIELD_CHARS_UPPER, FIELD_CHARS_UPPER.lower())
    # pair 3,5,7,... use a-x (24) in standard extensions
    return (SUBSQUARE_CHARS_LOWER.upper(), SUBSQUARE_CHARS_LOWER)


# ----------------------------
# Numeric stability helpers
# ----------------------------

# Used when clamping lat/lon at boundaries (90 and 180) so flooring doesn't overflow.
# (A tiny epsilon in degrees; ~1e-10 deg is ~1e-5 meters at equator, plenty small.)
CLAMP_EPS_DEG: float = 1e-10
