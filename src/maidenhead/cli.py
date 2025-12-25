# maidenhead/cli.py
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .core import (
    area_km2,
    cell_size,
    cell_size_km,
    cover_circle,
    cover_line,
    diagonal_km,
    from_latlon,
    format_locator,
    normalize,
    parse,
    step,
    to_bbox,
    to_center_latlon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_utm_zone,
)
from .geo import azimuthal_sector, bearing_bin, bearing_deg, distance_km, great_circle_path, midpoint
from .errors import MaidenheadError, MissingDependencyError


def _fmt_float(x: float, digits: int) -> str:
    # Avoid scientific notation for typical coords unless needed.
    return f"{x:.{digits}f}"


def _json_dumps(obj: object) -> str:
    try:
        import orjson  # type: ignore
    except Exception as exc:
        raise MissingDependencyError("JSON output requires orjson") from exc
    return orjson.dumps(obj).decode("utf-8")


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--digits",
        type=int,
        default=6,
        help="Decimal places for numeric output (default: 6).",
    )
    p.add_argument(
        "--csv",
        action="store_true",
        help="Use comma-separated output instead of spaces.",
    )


def _add_batch_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", help="Read input lines from a file.")
    p.add_argument("--stdin", action="store_true", help="Read input lines from stdin.")
    p.add_argument(
        "--format",
        choices=["plain", "csv", "json"],
        default="plain",
        help="Output format for batch mode (default: plain).",
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
    p_norm.add_argument("locator", nargs="?", help="Maidenhead locator (e.g. IO91wm)")
    _add_batch_args(p_norm)

    # validate
    p_val = sub.add_parser("validate", help="Validate a locator. Exit code 0 if valid, 2 if invalid.")
    p_val.add_argument("locator", help="Maidenhead locator (e.g. IO91wm)")
    p_val.add_argument(
        "--print",
        dest="print_output",
        action="store_true",
        help="Print 'valid' or 'invalid' in addition to the exit code.",
    )

    # center
    p_center = sub.add_parser("center", help="Print the center lat/lon for a locator.")
    p_center.add_argument("locator", nargs="?", help="Maidenhead locator")
    _add_common_args(p_center)
    _add_batch_args(p_center)

    # bbox
    p_bbox = sub.add_parser("bbox", help="Print bbox for a locator: min_lat min_lon max_lat max_lon.")
    p_bbox.add_argument("locator", nargs="?", help="Maidenhead locator")
    _add_common_args(p_bbox)
    _add_batch_args(p_bbox)

    # parts
    p_parts = sub.add_parser("parts", help="Print locator components (field/square/subsquare/etc).")
    p_parts.add_argument("locator", help="Maidenhead locator")

    # geojson
    p_geo = sub.add_parser("geojson", help="Emit GeoJSON for a locator or batch.")
    p_geo.add_argument("locator", nargs="?", help="Maidenhead locator")
    p_geo.add_argument(
        "--geojson-format",
        choices=["feature", "featurecollection"],
        default="feature",
        help="GeoJSON output type (default: feature).",
    )
    _add_batch_args(p_geo)

    # size
    p_size = sub.add_parser("size", help="Print cell size (width height).")
    p_size.add_argument("locator", help="Maidenhead locator")
    p_size.add_argument(
        "--unit",
        choices=["deg", "km", "miles"],
        default="deg",
        help="Unit for output (default: deg).",
    )
    p_size.add_argument(
        "--lon-at",
        type=float,
        default=None,
        help="Latitude for computing east-west size along the parallel (km/miles only).",
    )
    p_size.add_argument(
        "--at-lat",
        type=float,
        default=None,
        help="Alias for --lon-at.",
    )
    p_size.add_argument(
        "--method",
        choices=["spherical", "geodesic"],
        default="spherical",
        help="Distance method for km/miles (default: spherical).",
    )
    _add_common_args(p_size)

    # step
    p_step = sub.add_parser("step", help="Move a locator by a number of cells.")
    p_step.add_argument("locator", help="Maidenhead locator")
    p_step.add_argument("--dlat-cells", type=int, default=0, help="Cells to move north/south.")
    p_step.add_argument("--dlon-cells", type=int, default=0, help="Cells to move east/west.")

    # from-latlon
    p_fll = sub.add_parser("from-latlon", help="Convert lat/lon to a locator.")
    p_fll.add_argument(
        "latlon",
        nargs="*",
        help="Latitude/longitude as 'lat lon' or 'lat,lon'",
    )
    _add_batch_args(p_fll)
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

    # format
    p_fmt = sub.add_parser("format", help="Coerce locator precision.")
    p_fmt.add_argument("locator", help="Maidenhead locator")
    p_fmt.add_argument(
        "-p",
        "--precision",
        type=int,
        required=True,
        help="Target locator precision (character length).",
    )
    p_fmt.add_argument(
        "--mode",
        choices=["truncate", "center", "error"],
        default="center",
        help="Precision change mode (default: center).",
    )

    # area
    p_area = sub.add_parser("area", help="Print cell area (km^2).")
    p_area.add_argument("locator", help="Maidenhead locator")
    p_area.add_argument(
        "--method",
        choices=["spherical", "geodesic"],
        default="spherical",
        help="Area method (default: spherical).",
    )
    _add_common_args(p_area)

    # diagonal
    p_diag = sub.add_parser("diagonal", help="Print cell diagonal length (km).")
    p_diag.add_argument("locator", help="Maidenhead locator")
    p_diag.add_argument(
        "--method",
        choices=["spherical", "geodesic"],
        default="spherical",
        help="Distance method (default: spherical).",
    )
    _add_common_args(p_diag)

    # utm
    p_utm = sub.add_parser("utm", help="Print UTM zone for locator.")
    p_utm.add_argument("locator", help="Maidenhead locator")

    # cover-circle
    p_cc = sub.add_parser("cover-circle", help="Cover circle with grid squares.")
    p_cc.add_argument("center", nargs="+", help="Center as locator or 'lat,lon'")
    p_cc.add_argument("radius_km", type=float, help="Radius in kilometers")
    p_cc.add_argument(
        "-p",
        "--precision",
        type=int,
        required=True,
        help="Target locator precision (character length).",
    )
    _add_common_args(p_cc)
    _add_batch_args(p_cc)

    # cover-line
    p_cl = sub.add_parser("cover-line", help="Cover line with grid squares.")
    p_cl.add_argument("points", nargs="+", help="Start and end as locators or 'lat,lon'")
    p_cl.add_argument(
        "-p",
        "--precision",
        type=int,
        required=True,
        help="Target locator precision (character length).",
    )
    p_cl.add_argument(
        "--method",
        choices=["geodesic", "greatcircle"],
        default="greatcircle",
        help="Line method (default: greatcircle).",
    )
    _add_common_args(p_cl)
    _add_batch_args(p_cl)

    # distance
    p_dist = sub.add_parser("distance", help="Distance (km) between two locators or points.")
    p_dist.add_argument(
        "points",
        nargs="+",
        help="Two points as locators or 'lat,lon' (e.g. IO91wm 51.5,-0.12)",
    )
    p_dist.add_argument(
        "--method",
        choices=["haversine", "geodesic"],
        default="haversine",
        help="Distance method (default: haversine).",
    )
    _add_common_args(p_dist)

    # bearing
    p_bear = sub.add_parser("bearing", help="Initial bearing (deg) from A to B.")
    p_bear.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    _add_common_args(p_bear)

    # midpoint
    p_mid = sub.add_parser("midpoint", help="Great-circle midpoint between A and B (lat lon).")
    p_mid.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    _add_common_args(p_mid)

    # great-circle
    p_gc = sub.add_parser("great-circle", help="Great-circle path points from A to B.")
    p_gc.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    p_gc.add_argument(
        "-n",
        "--points-count",
        type=int,
        default=100,
        help="Number of points along the path (default: 100).",
    )
    _add_common_args(p_gc)

    # bearing-bin
    p_bin = sub.add_parser("bearing-bin", help="Bearing bin start angle from A to B.")
    p_bin.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    p_bin.add_argument(
        "--bin-size",
        type=float,
        default=5.0,
        help="Bearing bin size in degrees (default: 5).",
    )
    _add_common_args(p_bin)

    # azimuthal-sector
    p_sector = sub.add_parser("azimuthal-sector", help="Bearing sector from A to B.")
    p_sector.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    p_sector.add_argument(
        "--width",
        type=float,
        required=True,
        help="Sector width in degrees.",
    )
    _add_common_args(p_sector)

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


def _split_latlon_parts(parts: Sequence[str]) -> tuple[float, float] | None:
    stripped = [p.strip() for p in parts]
    joined = " ".join(stripped).strip()
    if "," in joined:
        pieces = [p.strip() for p in joined.split(",")]
        if len(pieces) == 2 and pieces[0] and pieces[1]:
            return (float(pieces[0]), float(pieces[1]))
    if len(stripped) == 2:
        try:
            return (float(stripped[0]), float(stripped[1]))
        except ValueError:
            return None
    return None


def _format_locator_list(locators: Sequence[str], *, sep: str) -> str:
    return sep.join(locators)


def _parse_latlon(args: Sequence[str]) -> tuple[float, float]:
    if len(args) == 1:
        parts = [p.strip() for p in args[0].split(",")]
        if len(parts) == 2:
            return (float(parts[0]), float(parts[1]))
        raise ValueError("Latitude/longitude must be 'lat lon' or 'lat,lon'")
    if len(args) == 2:
        latlon = _split_latlon_parts(args)
        if latlon is not None:
            return latlon
        return (float(args[0]), float(args[1]))
    raise ValueError("Latitude/longitude must be 'lat lon' or 'lat,lon'")


def _parse_point_parts(parts: Sequence[str]) -> tuple[float, float] | str:
    latlon = _split_latlon_parts(parts)
    if latlon is not None:
        return latlon
    if len(parts) == 1:
        return _parse_point(parts[0])
    raise ValueError("Point must be 'lat,lon' or a locator")


def _split_two_points(args: Sequence[str]) -> tuple[list[str], list[str]]:
    if len(args) == 2:
        return [args[0]], [args[1]]
    if len(args) == 3:
        if _split_latlon_parts(args[:2]) is not None:
            return list(args[:2]), [args[2]]
        if _split_latlon_parts(args[1:3]) is not None:
            return [args[0]], list(args[1:3])
        raise ValueError("expected two points")
    if len(args) == 4:
        return list(args[:2]), list(args[2:4])
    raise ValueError("expected two points")


def _read_batch_lines(file_path: str | None, use_stdin: bool) -> list[str]:
    if file_path and use_stdin:
        raise ValueError("Use only one of --file or --stdin")
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    if use_stdin:
        return [line.strip() for line in sys.stdin if line.strip()]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.cmd == "normalize":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = [normalize(line) for line in batch]
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            loc = normalize(args.locator)
            print(loc)
            return 0

        if args.cmd == "validate":
            try:
                _ = normalize(args.locator)
            except MaidenheadError:
                # 2 is a common “bad usage / invalid input” exit code.
                if args.print_output:
                    print("invalid")
                return 2
            if args.print_output:
                print("valid")
            return 0

        if args.cmd == "center":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                rows = [to_center_latlon(loc) for loc in batch]
                if args.format == "json":
                    print(_json_dumps([[lat, lon] for (lat, lon) in rows]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            f"{_fmt_float(lat, args.digits)}{sep}{_fmt_float(lon, args.digits)}"
                            for lat, lon in rows
                        )
                    )
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            lat, lon = to_center_latlon(args.locator)
            sep = "," if args.csv else " "
            print(f"{_fmt_float(lat, args.digits)}{sep}{_fmt_float(lon, args.digits)}")
            return 0

        if args.cmd == "bbox":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                rows = [to_bbox(loc) for loc in batch]
                if args.format == "json":
                    print(_json_dumps([list(row) for row in rows]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            f"{_fmt_float(min_lat, args.digits)}{sep}{_fmt_float(min_lon, args.digits)}"
                            f"{sep}{_fmt_float(max_lat, args.digits)}{sep}{_fmt_float(max_lon, args.digits)}"
                            for min_lat, min_lon, max_lat, max_lon in rows
                        )
                    )
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            min_lat, min_lon, max_lat, max_lon = to_bbox(args.locator)
            sep = "," if args.csv else " "
            print(
                f"{_fmt_float(min_lat, args.digits)}{sep}{_fmt_float(min_lon, args.digits)}"
                f"{sep}{_fmt_float(max_lat, args.digits)}{sep}{_fmt_float(max_lon, args.digits)}"
            )
            return 0

        if args.cmd == "parts":
            g = parse(args.locator)
            parts = [f"field={g.field}"]
            if g.square:
                parts.append(f"square={g.square}")
            if g.subsquare:
                parts.append(f"subsquare={g.subsquare}")
            if g.ext4:
                parts.append(f"ext4={g.ext4}")
            if g.ext5:
                parts.append(f"ext5={g.ext5}")
            print(" ".join(parts))
            return 0

        if args.cmd == "geojson":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                if args.geojson_format != "featurecollection":
                    raise ValueError("Batch geojson requires --geojson-format featurecollection")
                out = to_geojson_feature_collection(batch)
                print(_json_dumps(out))
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            if args.geojson_format == "featurecollection":
                out = to_geojson_feature_collection([args.locator])
            else:
                out = to_geojson_feature(args.locator)
            print(_json_dumps(out))
            return 0

        if args.cmd == "size":
            at_lat = args.lon_at if args.lon_at is not None else args.at_lat
            if args.unit == "deg":
                if at_lat is not None:
                    raise ValueError("--at-lat requires --unit km or miles")
                width, height = cell_size(args.locator, unit=args.unit)
            else:
                width, height = cell_size_km(
                    args.locator,
                    at_lat=at_lat,
                    method=args.method,
                )
                if args.unit == "miles":
                    miles_per_km = 0.621371
                    width *= miles_per_km
                    height *= miles_per_km
            sep = "," if args.csv else " "
            print(f"{_fmt_float(width, args.digits)}{sep}{_fmt_float(height, args.digits)}")
            return 0

        if args.cmd == "step":
            g = step(args.locator, dlat_cells=args.dlat_cells, dlon_cells=args.dlon_cells)
            print(g.locator)
            return 0

        if args.cmd == "area":
            area = area_km2(args.locator, method=args.method)
            print(_fmt_float(area, args.digits))
            return 0

        if args.cmd == "diagonal":
            dist = diagonal_km(args.locator, method=args.method)
            print(_fmt_float(dist, args.digits))
            return 0

        if args.cmd == "utm":
            print(to_utm_zone(args.locator))
            return 0

        if args.cmd == "cover-circle":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) != 3:
                        raise ValueError("Expected lines: center radius_km precision")
                    center_raw, radius_km, precision = parts[0], float(parts[1]), int(parts[2])
                    center = _parse_point(center_raw)
                    out.append([g.locator for g in cover_circle(center, radius_km, precision)])
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(sep.join(row) for row in out))
                return 0
            center = _parse_point_parts(args.center)
            out = cover_circle(center, args.radius_km, args.precision)
            sep = "," if args.csv else " "
            print(_format_locator_list([g.locator for g in out], sep=sep))
            return 0

        if args.cmd == "cover-line":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) != 3:
                        raise ValueError("Expected lines: start end precision")
                    start_raw, end_raw, precision = parts[0], parts[1], int(parts[2])
                    start = _parse_point(start_raw)
                    end = _parse_point(end_raw)
                    out.append([g.locator for g in cover_line(start, end, precision, method=args.method)])
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(sep.join(row) for row in out))
                return 0
            a_parts, b_parts = _split_two_points(args.points)
            out = cover_line(
                _parse_point_parts(a_parts),
                _parse_point_parts(b_parts),
                args.precision,
                method=args.method,
            )
            sep = "," if args.csv else " "
            print(_format_locator_list([g.locator for g in out], sep=sep))
            return 0

        if args.cmd == "from-latlon":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) != 2:
                        raise ValueError("Latitude/longitude must be 'lat lon' or 'lat,lon'")
                    lat, lon = float(parts[0]), float(parts[1])
                    out.append(
                        from_latlon(lat, lon, precision=args.precision, clamp=(not args.no_clamp)).locator
                    )
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            if not args.latlon:
                raise ValueError("lat/lon is required unless --file/--stdin is provided")
            lat, lon = _parse_latlon(args.latlon)
            g = from_latlon(
                lat,
                lon,
                precision=args.precision,
                clamp=(not args.no_clamp),
            )
            print(g.locator)
            return 0

        if args.cmd == "format":
            g = format_locator(args.locator, precision=args.precision, mode=args.mode)
            print(g.locator)
            return 0

        if args.cmd == "distance":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            d = distance_km(a, b, method=args.method)
            print(_fmt_float(d, args.digits))
            return 0

        if args.cmd == "bearing":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            br = bearing_deg(a, b)
            print(_fmt_float(br, args.digits))
            return 0

        if args.cmd == "midpoint":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            lat, lon = midpoint(a, b)
            sep = "," if args.csv else " "
            print(f"{_fmt_float(lat, args.digits)}{sep}{_fmt_float(lon, args.digits)}")
            return 0

        if args.cmd == "great-circle":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            pts = great_circle_path(a, b, n=args.points_count)
            if args.csv:
                print("\n".join(f"{_fmt_float(lat, args.digits)},{_fmt_float(lon, args.digits)}" for lat, lon in pts))
            else:
                print("\n".join(f"{_fmt_float(lat, args.digits)} {_fmt_float(lon, args.digits)}" for lat, lon in pts))
            return 0

        if args.cmd == "bearing-bin":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            binned = bearing_bin(a, b, bin_size=args.bin_size)
            print(_fmt_float(binned, args.digits))
            return 0

        if args.cmd == "azimuthal-sector":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            start, end = azimuthal_sector(a, b, width_deg=args.width)
            sep = "," if args.csv else " "
            print(f"{_fmt_float(start, args.digits)}{sep}{_fmt_float(end, args.digits)}")
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
