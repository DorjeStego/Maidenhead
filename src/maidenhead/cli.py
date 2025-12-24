# maidenhead/cli.py
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .core import (
    from_latlon,
    normalize,
    parse,
    to_bbox,
    to_center_latlon,
)
from .geo import bearing_deg, distance_km, midpoint
from .errors import MaidenheadError


def _fmt_float(x: float, digits: int) -> str:
    # Avoid scientific notation for typical coords unless needed.
    return f"{x:.{digits}f}"


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--digits",
        type=int,
        default=6,
        help="Decimal places for numeric output (default: 6).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mh",
        description="Maidenhead grid square utilities",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # normalize
    p_norm = sub.add_parser("normalize", help="Normalize locator casing and validate.")
    p_norm.add_argument("locator", help="Maidenhead locator (e.g. IO91wm)")

    # validate
    p_val = sub.add_parser("validate", help="Validate a locator. Exit code 0 if valid, 2 if invalid.")
    p_val.add_argument("locator", help="Maidenhead locator (e.g. IO91wm)")

    # center
    p_center = sub.add_parser("center", help="Print the center lat/lon for a locator.")
    p_center.add_argument("locator", help="Maidenhead locator")
    _add_common_args(p_center)

    # bbox
    p_bbox = sub.add_parser("bbox", help="Print bbox for a locator: min_lat min_lon max_lat max_lon.")
    p_bbox.add_argument("locator", help="Maidenhead locator")
    _add_common_args(p_bbox)

    # from-latlon
    p_fll = sub.add_parser("from-latlon", help="Convert lat/lon to a locator.")
    p_fll.add_argument("lat", type=float, help="Latitude in degrees (-90..90)")
    p_fll.add_argument("lon", type=float, help="Longitude in degrees (-180..180 or any, normalized)")
    p_fll.add_argument(
        "-p",
        "--precision",
        type=int,
        default=6,
        help="Locator precision (character length): 2, 4, 6, 8 (default: 6)",
    )
    p_fll.add_argument(
        "--no-clamp",
        action="store_true",
        help="Disable boundary clamping (lat=90/lon=180 will error).",
    )

    # distance
    p_dist = sub.add_parser("distance", help="Distance (km) between two locators or points.")
    p_dist.add_argument("a", help="Locator or 'lat,lon' (e.g. IO91wm or 51.5,-0.12)")
    p_dist.add_argument("b", help="Locator or 'lat,lon' (e.g. FN31pr or 40.7,-74.0)")
    p_dist.add_argument(
        "--method",
        choices=["haversine", "geodesic"],
        default="haversine",
        help="Distance method (default: haversine).",
    )
    _add_common_args(p_dist)

    # bearing
    p_bear = sub.add_parser("bearing", help="Initial bearing (deg) from A to B.")
    p_bear.add_argument("a", help="Locator or 'lat,lon'")
    p_bear.add_argument("b", help="Locator or 'lat,lon'")
    _add_common_args(p_bear)

    # midpoint
    p_mid = sub.add_parser("midpoint", help="Great-circle midpoint between A and B (lat lon).")
    p_mid.add_argument("a", help="Locator or 'lat,lon'")
    p_mid.add_argument("b", help="Locator or 'lat,lon'")
    _add_common_args(p_mid)

    return parser


def _parse_point(s: str):
    """
    Accept either a Maidenhead locator or a 'lat,lon' string.
    Returns either a locator (str) or (lat, lon) tuple for geo functions.
    """
    txt = s.strip()
    if "," in txt:
        parts = [p.strip() for p in txt.split(",")]
        if len(parts) != 2:
            raise ValueError("Point must be 'lat,lon' or a locator")
        return (float(parts[0]), float(parts[1]))

    # Treat as locator; normalize/validate early for clearer CLI errors.
    return normalize(txt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.cmd == "normalize":
            loc = normalize(args.locator)
            print(loc)
            return 0

        if args.cmd == "validate":
            try:
                _ = normalize(args.locator)
            except MaidenheadError:
                # 2 is a common “bad usage / invalid input” exit code.
                return 2
            return 0

        if args.cmd == "center":
            lat, lon = to_center_latlon(args.locator)
            print(f"{_fmt_float(lat, args.digits)} {_fmt_float(lon, args.digits)}")
            return 0

        if args.cmd == "bbox":
            min_lat, min_lon, max_lat, max_lon = to_bbox(args.locator)
            print(
                f"{_fmt_float(min_lat, args.digits)} {_fmt_float(min_lon, args.digits)} "
                f"{_fmt_float(max_lat, args.digits)} {_fmt_float(max_lon, args.digits)}"
            )
            return 0

        if args.cmd == "from-latlon":
            g = from_latlon(
                args.lat,
                args.lon,
                precision=args.precision,
                clamp=(not args.no_clamp),
            )
            print(g.locator)
            return 0

        if args.cmd == "distance":
            a = _parse_point(args.a)
            b = _parse_point(args.b)
            d = distance_km(a, b, method=args.method)
            print(_fmt_float(d, args.digits))
            return 0

        if args.cmd == "bearing":
            a = _parse_point(args.a)
            b = _parse_point(args.b)
            br = bearing_deg(a, b)
            print(_fmt_float(br, args.digits))
            return 0

        if args.cmd == "midpoint":
            a = _parse_point(args.a)
            b = _parse_point(args.b)
            lat, lon = midpoint(a, b)
            print(f"{_fmt_float(lat, args.digits)} {_fmt_float(lon, args.digits)}")
            return 0

        parser.error("unknown command")
        return 2

    except MaidenheadError as e:
        # Library-defined errors: print a clean message to stderr.
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        # CLI parsing / lat,lon parsing issues.
        print(f"error: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
