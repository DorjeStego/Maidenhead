# maidenhead/cli.py
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .core import (
    area_km2,
    cell_size,
    cover_circle,
    cover_line,
    diagonal_km,
    from_latlon,
    format_locator,
    corners,
    azimuth,
    normalize,
    parse,
    precision_of,
    neighbors,
    adjacent,
    initial_bearing,
    parent,
    children,
    contains,
    contains_point,
    intersects_bbox,
    intersects_polygon,
    split_bbox_list,
    step,
    to_bbox,
    to_center_latlon,
    to_geojson_bbox,
    to_geojson_envelope,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_utm_zone,
    to_wkt,
)
from .bulk import normalize_many as bulk_normalize_many
from .vector import from_latlon_many as vector_from_latlon_many
from .vector import to_bbox_many as vector_to_bbox_many
from .vector import to_center_latlon_many as vector_to_center_many
from .geo import (
    azimuthal_sector,
    bearing_bin,
    bearing_deg,
    distance_km,
    geodesic_midpoint,
    great_circle_path,
    midpoint,
)
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
        description="Maidenhead grid square utilities for encoding and decoding locators.",
        epilog=(
            "Examples:\n"
            "  mh normalize IO91wm\n"
            "  mh center IO83ri\n"
            "  mh from-latlon 53.365418,-2.574069\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    p_bbox.add_argument(
        "--split",
        action="store_true",
        help="Split bbox across antimeridian when needed.",
    )
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
        choices=["feature", "featurecollection", "bbox", "envelope"],
        default="feature",
        help="GeoJSON output type (default: feature).",
    )
    p_geo.add_argument(
        "--split",
        action="store_true",
        help="Split bbox across antimeridian when needed.",
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
        help="Locator precision (character length): 2, 4, 6, 8, 10 (default: 6)",
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

    # corners
    p_corners = sub.add_parser("corners", help="Print NW NE SW SE corners of a locator.")
    p_corners.add_argument("locator", help="Maidenhead locator")
    _add_common_args(p_corners)

    # precision
    p_prec = sub.add_parser("precision", help="Print locator precision (character length).")
    p_prec.add_argument("locator", help="Maidenhead locator")

    # neighbors
    p_neighbors = sub.add_parser("neighbors", help="List neighboring locators.")
    p_neighbors.add_argument("locator", help="Maidenhead locator")
    p_neighbors.add_argument("--ring", type=int, default=1, help="Ring distance (default: 1).")
    p_neighbors.add_argument(
        "--diagonals",
        dest="diagonals",
        action="store_true",
        help="Include diagonals (default).",
    )
    p_neighbors.add_argument(
        "--no-diagonals",
        dest="diagonals",
        action="store_false",
        help="Exclude diagonals.",
    )
    p_neighbors.set_defaults(diagonals=True)
    p_neighbors.add_argument(
        "--csv",
        action="store_true",
        help="Use comma-separated output instead of spaces.",
    )

    # adjacent
    p_adj = sub.add_parser("adjacent", help="List adjacent locators with directions.")
    p_adj.add_argument("locator", help="Maidenhead locator")
    p_adj.add_argument(
        "--diagonals",
        action="store_true",
        help="Include diagonals.",
    )
    p_adj.add_argument(
        "--csv",
        action="store_true",
        help="Use comma-separated output instead of spaces.",
    )

    # wkt
    p_wkt = sub.add_parser("wkt", help="Print WKT polygon for a locator or lat/lon.")
    p_wkt.add_argument("locator", nargs="?", help="Maidenhead locator or lat,lon")
    p_wkt.add_argument(
        "-p",
        "--precision",
        type=int,
        default=6,
        help="Locator precision for lat/lon input (default: 6).",
    )
    _add_batch_args(p_wkt)

    # bbox-split
    p_bbox_split = sub.add_parser("bbox-split", help="Split a bbox that crosses the antimeridian.")
    p_bbox_split.add_argument("min_lat", type=float, help="Minimum latitude")
    p_bbox_split.add_argument("min_lon", type=float, help="Minimum longitude")
    p_bbox_split.add_argument("max_lat", type=float, help="Maximum latitude")
    p_bbox_split.add_argument("max_lon", type=float, help="Maximum longitude")
    _add_common_args(p_bbox_split)

    # bbox-split-list
    p_bbox_split_list = sub.add_parser(
        "bbox-split-list", help="List non-degenerate bbox parts after antimeridian split."
    )
    p_bbox_split_list.add_argument("min_lat", type=float, help="Minimum latitude")
    p_bbox_split_list.add_argument("min_lon", type=float, help="Minimum longitude")
    p_bbox_split_list.add_argument("max_lat", type=float, help="Maximum latitude")
    p_bbox_split_list.add_argument("max_lon", type=float, help="Maximum longitude")
    _add_common_args(p_bbox_split_list)
    _add_batch_args(p_bbox_split_list)

    # bulk
    p_bulk = sub.add_parser("bulk", help="Bulk operations for locators/latlon.")
    p_bulk.add_argument(
        "op",
        choices=[
            "from-latlon",
            "center",
            "bbox",
            "normalize",
            "wkt",
            "contains-point",
            "contains",
            "intersects-bbox",
            "azimuth",
            "initial-bearing",
            "intersects-polygon",
            "neighbors",
            "adjacent",
            "corners",
            "precision",
            "parent",
            "children",
            "size",
            "area",
            "diagonal",
            "utm",
            "geojson",
            "bbox-split",
            "bbox-split-list",
        ],
        help="Bulk operation.",
    )
    p_bulk.add_argument(
        "-p",
        "--precision",
        type=int,
        default=None,
        help="Locator precision for from-latlon (default: 6).",
    )
    p_bulk.add_argument(
        "--range",
        dest="range_mode",
        action="store_true",
        help="Include min/max range for azimuth.",
    )
    p_bulk.add_argument(
        "--digits",
        type=int,
        default=6,
        help="Decimal places for numeric output (default: 6).",
    )
    p_bulk.add_argument(
        "--diagonals",
        dest="diagonals",
        action="store_true",
        help="Include diagonals for neighbors/adjacent (default).",
    )
    p_bulk.add_argument(
        "--no-diagonals",
        dest="diagonals",
        action="store_false",
        help="Exclude diagonals for neighbors/adjacent.",
    )
    p_bulk.set_defaults(diagonals=True)
    p_bulk.add_argument(
        "--ring",
        type=int,
        default=1,
        help="Ring distance for neighbors (default: 1).",
    )
    p_bulk.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of results for bulk children.",
    )
    p_bulk.add_argument(
        "--unit",
        choices=["deg", "km", "miles"],
        default="deg",
        help="Unit for bulk size (default: deg).",
    )
    p_bulk.add_argument(
        "--at-lat",
        type=float,
        default=None,
        help="Latitude for bulk size east-west distance.",
    )
    p_bulk.add_argument(
        "--method",
        choices=["spherical", "geodesic"],
        default="spherical",
        help="Method for bulk area/diagonal/size (default: spherical).",
    )
    p_bulk.add_argument(
        "--geojson-format",
        choices=["feature", "featurecollection", "bbox", "envelope"],
        default="feature",
        help="GeoJSON output type for bulk geojson (default: feature).",
    )
    p_bulk.add_argument(
        "--split",
        action="store_true",
        help="Split bbox across antimeridian for bulk geojson.",
    )
    _add_batch_args(p_bulk)

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
    p_mid.add_argument(
        "--method",
        choices=["greatcircle", "geodesic"],
        default="greatcircle",
        help="Midpoint method (default: greatcircle).",
    )
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

    # azimuth
    p_az = sub.add_parser("azimuth", help="Bearing and distance between A and B.")
    p_az.add_argument("points", nargs="+", help="Two points as locators or 'lat,lon'")
    p_az.add_argument(
        "--range",
        dest="range_mode",
        action="store_true",
        help="Include min/max range using corner-to-corner distances.",
    )
    _add_common_args(p_az)

    # initial-bearing
    p_ib = sub.add_parser("initial-bearing", help="Initial bearing between two locators.")
    p_ib.add_argument("locator_a", help="Origin locator")
    p_ib.add_argument("locator_b", help="Destination locator")
    _add_common_args(p_ib)

    # parent
    p_parent = sub.add_parser("parent", help="Return parent locator at lower precision.")
    p_parent.add_argument("locator", help="Maidenhead locator")
    p_parent.add_argument(
        "-p",
        "--precision",
        type=int,
        default=None,
        help="Target precision (character length).",
    )

    # children
    p_children = sub.add_parser("children", help="List child locators at higher precision.")
    p_children.add_argument("locator", help="Maidenhead locator")
    p_children.add_argument(
        "-p",
        "--precision",
        type=int,
        default=None,
        help="Target precision (character length).",
    )
    p_children.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of children output.",
    )
    p_children.add_argument(
        "--csv",
        action="store_true",
        help="Use comma-separated output instead of spaces.",
    )

    # contains
    p_contains = sub.add_parser("contains", help="Check if one locator contains another.")
    p_contains.add_argument("outer", help="Outer (less precise) locator")
    p_contains.add_argument("inner", help="Inner (more precise) locator")

    # contains-point
    p_contains_pt = sub.add_parser(
        "contains-point", help="Check if a locator contains a lat/lon point."
    )
    p_contains_pt.add_argument("locator", help="Maidenhead locator")
    p_contains_pt.add_argument("latlon", nargs="+", help="Point as 'lat lon' or 'lat,lon'")
    _add_batch_args(p_contains_pt)

    # intersects-bbox
    p_ib = sub.add_parser("intersects-bbox", help="Check if locator intersects a bbox.")
    p_ib.add_argument("locator", help="Maidenhead locator")
    p_ib.add_argument("min_lat", type=float, help="Minimum latitude")
    p_ib.add_argument("min_lon", type=float, help="Minimum longitude")
    p_ib.add_argument("max_lat", type=float, help="Maximum latitude")
    p_ib.add_argument("max_lon", type=float, help="Maximum longitude")
    _add_batch_args(p_ib)

    # intersects-polygon
    p_ip = sub.add_parser(
        "intersects-polygon", help="Check if locator intersects a polygon."
    )
    p_ip.add_argument("locator", help="Maidenhead locator")
    p_ip.add_argument("points", nargs="+", help="Polygon points as lat,lon pairs")
    _add_batch_args(p_ip)

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


def _format_bbox_line(
    bbox: tuple[float, float, float, float],
    *,
    digits: int,
    sep: str,
) -> str:
    min_lat, min_lon, max_lat, max_lon = bbox
    return (
        f"{_fmt_float(min_lat, digits)}{sep}{_fmt_float(min_lon, digits)}"
        f"{sep}{_fmt_float(max_lat, digits)}{sep}{_fmt_float(max_lon, digits)}"
    )


def _bbox_polygon(bbox: tuple[float, float, float, float]) -> dict:
    min_lat, min_lon, max_lat, max_lon = bbox
    ring = [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


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


def _parse_polygon_points(parts: Sequence[str]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for item in parts:
        if "," not in item:
            raise ValueError("Polygon points must be in lat,lon form")
        lat, lon = _parse_latlon([item])
        points.append((lat, lon))
    if len(points) < 3:
        raise ValueError("Polygon must have at least 3 points")
    return points


def _split_bulk_line(line: str) -> list[str]:
    if any(ch.isspace() for ch in line):
        return line.split()
    return [p.strip() for p in line.split(",")]


def _parse_latlon_lines(lines: Sequence[str]) -> tuple[list[float], list[float]]:
    lats: list[float] = []
    lons: list[float] = []
    for line in lines:
        parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
        if len(parts) != 2:
            raise ValueError("Latitude/longitude must be 'lat lon' or 'lat,lon'")
        lats.append(float(parts[0]))
        lons.append(float(parts[1]))
    return lats, lons


def _format_latlon_rows(rows: Sequence[tuple[float, float]], *, digits: int, sep: str) -> str:
    return "\n".join(
        f"{_fmt_float(lat, digits)}{sep}{_fmt_float(lon, digits)}" for lat, lon in rows
    )


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
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if not raw_argv:
        parser.print_help()
        return 0
    args = parser.parse_args(raw_argv)

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
                rows = []
                for loc in batch:
                    bbox = to_bbox(loc)
                    if args.split:
                        parts = split_bbox_list(bbox) or [bbox]
                        rows.extend(parts)
                    else:
                        rows.append(bbox)
                if args.format == "json":
                    print(_json_dumps([list(row) for row in rows]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(_format_bbox_line(row, digits=args.digits, sep=sep) for row in rows))
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            bbox = to_bbox(args.locator)
            sep = "," if args.csv else " "
            if args.split:
                parts = split_bbox_list(bbox) or [bbox]
                print("\n".join(_format_bbox_line(row, digits=args.digits, sep=sep) for row in parts))
            else:
                print(_format_bbox_line(bbox, digits=args.digits, sep=sep))
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
                if args.geojson_format != "featurecollection" or args.split:
                    raise ValueError("Batch geojson requires --geojson-format featurecollection")
                out = to_geojson_feature_collection(batch)
                print(_json_dumps(out))
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            if args.geojson_format == "featurecollection":
                out = to_geojson_feature_collection([args.locator])
            elif args.geojson_format == "bbox":
                bbox = to_geojson_bbox(args.locator)
                if args.split:
                    parts = split_bbox_list(to_bbox(args.locator)) or [to_bbox(args.locator)]
                    out = [list(b) for b in parts]
                else:
                    out = bbox
            elif args.geojson_format == "envelope":
                if args.split:
                    parts = split_bbox_list(to_bbox(args.locator)) or [to_bbox(args.locator)]
                    out = {
                        "type": "FeatureCollection",
                        "features": [
                            {"type": "Feature", "geometry": _bbox_polygon(b), "properties": {}}
                            for b in parts
                        ],
                    }
                else:
                    out = to_geojson_envelope(args.locator)
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
                width, height = cell_size(
                    args.locator,
                    unit="km",
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

        if args.cmd == "corners":
            nw, ne, sw, se = corners(args.locator)
            sep = "," if args.csv else " "
            rows = [nw, ne, sw, se]
            print(_format_latlon_rows(rows, digits=args.digits, sep=sep))
            return 0

        if args.cmd == "precision":
            print(precision_of(args.locator))
            return 0

        if args.cmd == "neighbors":
            neigh = neighbors(args.locator, ring=args.ring, diagonals=args.diagonals)
            sep = "," if args.csv else " "
            print(sep.join(g.locator for g in neigh))
            return 0

        if args.cmd == "adjacent":
            adj = adjacent(args.locator, diagonals=args.diagonals)
            sep = "," if args.csv else " "
            print("\n".join(f"{k}{sep}{v.locator}" for k, v in adj.items()))
            return 0

        if args.cmd == "wkt":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    if "," in line:
                        lat, lon = _parse_latlon([line])
                        loc = from_latlon(lat, lon, precision=args.precision)
                        out.append(to_wkt(loc))
                    else:
                        out.append(to_wkt(line))
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            if args.locator is None:
                raise ValueError("locator is required unless --file/--stdin is provided")
            if "," in args.locator:
                lat, lon = _parse_latlon([args.locator])
                loc = from_latlon(lat, lon, precision=args.precision)
                print(to_wkt(loc))
            else:
                print(to_wkt(args.locator))
            return 0

        if args.cmd == "bbox-split":
            bbox = (args.min_lat, args.min_lon, args.max_lat, args.max_lon)
            parts = split_bbox_list(bbox) or [bbox]
            sep = "," if args.csv else " "
            print("\n".join(_format_bbox_line(row, digits=args.digits, sep=sep) for row in parts))
            return 0

        if args.cmd == "bbox-split-list":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) != 4:
                        raise ValueError("Expected lines: min_lat min_lon max_lat max_lon")
                    bbox = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                    out.append([list(b) for b in split_bbox_list(bbox)])
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            ";".join(_format_bbox_line(tuple(b), digits=args.digits, sep=sep) for b in row)
                            for row in out
                        )
                    )
                return 0
            bbox = (args.min_lat, args.min_lon, args.max_lat, args.max_lon)
            parts = split_bbox_list(bbox)
            if args.format == "json":
                print(_json_dumps([list(b) for b in parts]))
            else:
                sep = "," if args.csv else " "
                print("\n".join(_format_bbox_line(row, digits=args.digits, sep=sep) for row in parts))
            return 0

        if args.cmd == "bulk":
            lines = _read_batch_lines(args.file, args.stdin)
            if not lines:
                raise ValueError("bulk requires --file or --stdin input")

            if args.op == "normalize":
                out = bulk_normalize_many(lines)
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "from-latlon":
                lats, lons = _parse_latlon_lines(lines)
                precision = args.precision if args.precision is not None else 6
                out = vector_from_latlon_many(
                    lats,
                    lons,
                    precision=precision,
                    return_type="list",
                )
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "center":
                lat_out, lon_out = vector_to_center_many(lines, return_type="tuple")
                rows = list(zip(lat_out, lon_out))
                if args.format == "json":
                    print(_json_dumps([[lat, lon] for lat, lon in rows]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(_format_latlon_rows(rows, digits=args.digits, sep=sep))
                return 0

            if args.op == "bbox":
                min_lats, min_lons, max_lats, max_lons = vector_to_bbox_many(lines, return_type="tuple")
                rows = list(zip(min_lats, min_lons, max_lats, max_lons))
                if args.format == "json":
                    print(_json_dumps([list(row) for row in rows]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(_format_bbox_line(row, digits=args.digits, sep=sep) for row in rows))
                return 0

            if args.op == "wkt":
                out = []
                precision = args.precision if args.precision is not None else 6
                for line in lines:
                    if "," in line:
                        lat, lon = _parse_latlon([line])
                        loc = from_latlon(lat, lon, precision=precision)
                        out.append(to_wkt(loc))
                    else:
                        out.append(to_wkt(line))
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "contains-point":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) == 2:
                        locator = parts[0]
                        lat, lon = _parse_latlon([parts[1]])
                    else:
                        if len(parts) < 3:
                            raise ValueError("Expected lines: locator lat lon")
                        locator = parts[0]
                        lat, lon = _parse_latlon(parts[1:])
                    out.append(contains_point(locator, lat, lon))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join("true" if v else "false" for v in out))
                else:
                    print("\n".join("true" if v else "false" for v in out))
                return 0

            if args.op == "contains":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 2:
                        raise ValueError("Expected lines: outer inner")
                    outer, inner = parts[0], parts[1]
                    out.append(contains(outer, inner))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join("true" if v else "false" for v in out))
                else:
                    print("\n".join("true" if v else "false" for v in out))
                return 0

            if args.op == "intersects-bbox":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 5:
                        raise ValueError("Expected lines: locator min_lat min_lon max_lat max_lon")
                    locator = parts[0]
                    bbox = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                    out.append(intersects_bbox(locator, bbox))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join("true" if v else "false" for v in out))
                else:
                    print("\n".join("true" if v else "false" for v in out))
                return 0

            if args.op == "intersects-polygon":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) < 4:
                        raise ValueError("Expected lines: locator lat,lon lat,lon lat,lon ...")
                    locator = parts[0]
                    poly = _parse_polygon_points(parts[1:])
                    out.append(intersects_polygon(locator, poly))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join("true" if v else "false" for v in out))
                else:
                    print("\n".join("true" if v else "false" for v in out))
                return 0

            if args.op == "azimuth":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 2:
                        raise ValueError("Expected lines: point_a point_b")
                    a = _parse_point(parts[0])
                    b = _parse_point(parts[1])
                    if args.range_mode:
                        bearing, min_km, max_km = azimuth(a, b, range_mode=True)
                        out.append(
                            [
                                _fmt_float(bearing, args.digits),
                                _fmt_float(min_km, args.digits),
                                _fmt_float(max_km, args.digits),
                            ]
                        )
                    else:
                        bearing, dist = azimuth(a, b)
                        out.append(
                            [
                                _fmt_float(bearing, args.digits),
                                _fmt_float(dist, args.digits),
                            ]
                        )
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(sep.join(row) for row in out))
                return 0

            if args.op == "initial-bearing":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 2:
                        raise ValueError("Expected lines: locator_a locator_b")
                    out.append(_fmt_float(initial_bearing(parts[0], parts[1]), args.digits))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "neighbors":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    neigh = neighbors(parts[0], ring=args.ring, diagonals=args.diagonals)
                    out.append([g.locator for g in neigh])
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print("\n".join(",".join(row) for row in out))
                else:
                    print("\n".join(" ".join(row) for row in out))
                return 0

            if args.op == "adjacent":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    adj = adjacent(parts[0], diagonals=args.diagonals)
                    out.append([[k, v.locator] for k, v in adj.items()])
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print("\n".join(",".join(f"{k}:{v}" for k, v in row) for row in out))
                else:
                    print("\n".join(" ".join(f"{k}:{v}" for k, v in row) for row in out))
                return 0

            if args.op == "corners":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    nw, ne, sw, se = corners(parts[0])
                    out.append([nw, ne, sw, se])
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    point_sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            ";".join(
                                f"{_fmt_float(lat, args.digits)}{point_sep}{_fmt_float(lon, args.digits)}"
                                for lat, lon in row
                            )
                            for row in out
                        )
                    )
                return 0

            if args.op == "precision":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    out.append(precision_of(parts[0]))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(str(v) for v in out))
                else:
                    print("\n".join(str(v) for v in out))
                return 0

            if args.op == "parent":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    if args.precision is None:
                        out.append(parent(parts[0]).locator)
                    else:
                        out.append(parent(parts[0], precision=args.precision).locator)
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "children":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    if args.precision is None:
                        g = parse(parts[0])
                        precision = g.precision + 2
                    else:
                        precision = args.precision
                    items = list(children(parts[0], precision=precision))
                    if args.limit is not None:
                        items = items[: args.limit]
                    out.append([g.locator for g in items])
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print("\n".join(",".join(row) for row in out))
                else:
                    print("\n".join(" ".join(row) for row in out))
                return 0

            if args.op == "size":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    loc = parts[0]
                    if args.unit == "deg":
                        width, height = cell_size(loc, unit="deg")
                    else:
                        width, height = cell_size(
                            loc,
                            unit="km",
                            at_lat=args.at_lat,
                            method=args.method,
                        )
                        if args.unit == "miles":
                            miles_per_km = 0.621371
                            width *= miles_per_km
                            height *= miles_per_km
                    out.append([_fmt_float(width, args.digits), _fmt_float(height, args.digits)])
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    sep = "," if args.format == "csv" else " "
                    print("\n".join(sep.join(row) for row in out))
                return 0

            if args.op == "area":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    out.append(_fmt_float(area_km2(parts[0], method=args.method), args.digits))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "diagonal":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    out.append(_fmt_float(diagonal_km(parts[0], method=args.method), args.digits))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "utm":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 1:
                        raise ValueError("Expected lines: locator")
                    out.append(to_utm_zone(parts[0]))
                if args.format == "json":
                    print(_json_dumps(out))
                elif args.format == "csv":
                    print(",".join(out))
                else:
                    print("\n".join(out))
                return 0

            if args.op == "geojson":
                if args.geojson_format == "featurecollection":
                    out = to_geojson_feature_collection(lines)
                    print(_json_dumps(out))
                    return 0
                if args.geojson_format == "feature":
                    out = [to_geojson_feature(loc) for loc in lines]
                    print(_json_dumps(out))
                    return 0
                if args.geojson_format == "bbox":
                    if args.split:
                        out = [
                            [list(b) for b in (split_bbox_list(to_bbox(loc)) or [to_bbox(loc)])]
                            for loc in lines
                        ]
                    else:
                        out = [to_geojson_bbox(loc) for loc in lines]
                    print(_json_dumps(out))
                    return 0
                if args.geojson_format == "envelope":
                    if args.split:
                        out = {
                            "type": "FeatureCollection",
                            "features": [
                                {"type": "Feature", "geometry": _bbox_polygon(b), "properties": {}}
                                for loc in lines
                                for b in (split_bbox_list(to_bbox(loc)) or [to_bbox(loc)])
                            ],
                        }
                    else:
                        out = [to_geojson_envelope(loc) for loc in lines]
                    print(_json_dumps(out))
                    return 0

            if args.op == "bbox-split":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 4:
                        raise ValueError("Expected lines: min_lat min_lon max_lat max_lon")
                    bbox = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                    parts_out = split_bbox_list(bbox) or [bbox]
                    out.append(parts_out)
                if args.format == "json":
                    print(_json_dumps([[list(b) for b in row] for row in out]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            ";".join(_format_bbox_line(b, digits=args.digits, sep=sep) for b in row)
                            for row in out
                        )
                    )
                return 0

            if args.op == "bbox-split-list":
                out = []
                for line in lines:
                    parts = _split_bulk_line(line)
                    if len(parts) != 4:
                        raise ValueError("Expected lines: min_lat min_lon max_lat max_lon")
                    bbox = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                    out.append(split_bbox_list(bbox))
                if args.format == "json":
                    print(_json_dumps([[list(b) for b in row] for row in out]))
                else:
                    sep = "," if args.format == "csv" else " "
                    print(
                        "\n".join(
                            ";".join(_format_bbox_line(b, digits=args.digits, sep=sep) for b in row)
                            for row in out
                        )
                    )
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
            if args.method == "geodesic":
                lat, lon = geodesic_midpoint(a, b)
            else:
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

        if args.cmd == "azimuth":
            a_parts, b_parts = _split_two_points(args.points)
            a = _parse_point_parts(a_parts)
            b = _parse_point_parts(b_parts)
            if args.range_mode:
                bearing, min_km, max_km = azimuth(a, b, range_mode=True)
                sep = "," if args.csv else " "
                print(
                    f"{_fmt_float(bearing, args.digits)}{sep}"
                    f"{_fmt_float(min_km, args.digits)}{sep}"
                    f"{_fmt_float(max_km, args.digits)}"
                )
            else:
                bearing, dist = azimuth(a, b)
                sep = "," if args.csv else " "
                print(f"{_fmt_float(bearing, args.digits)}{sep}{_fmt_float(dist, args.digits)}")
            return 0

        if args.cmd == "initial-bearing":
            br = initial_bearing(args.locator_a, args.locator_b)
            print(_fmt_float(br, args.digits))
            return 0

        if args.cmd == "parent":
            g = parent(args.locator, precision=args.precision)
            print(g.locator)
            return 0

        if args.cmd == "children":
            if args.precision is None:
                g = parse(args.locator)
                precision = g.precision + 2
            else:
                precision = args.precision
            items = list(children(args.locator, precision=precision))
            if args.limit is not None:
                items = items[: args.limit]
            sep = "," if args.csv else " "
            print(sep.join(g.locator for g in items))
            return 0

        if args.cmd == "contains":
            print("true" if contains(args.outer, args.inner) else "false")
            return 0

        if args.cmd == "contains-point":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) < 3:
                        raise ValueError("Expected lines: locator lat lon")
                    locator = parts[0]
                    lat, lon = _parse_latlon(parts[1:])
                    out.append("true" if contains_point(locator, lat, lon) else "false")
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            lat, lon = _parse_latlon(args.latlon)
            print("true" if contains_point(args.locator, lat, lon) else "false")
            return 0

        if args.cmd == "intersects-bbox":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) != 5:
                        raise ValueError("Expected lines: locator min_lat min_lon max_lat max_lon")
                    locator = parts[0]
                    bbox = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                    out.append("true" if intersects_bbox(locator, bbox) else "false")
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            bbox = (args.min_lat, args.min_lon, args.max_lat, args.max_lon)
            print("true" if intersects_bbox(args.locator, bbox) else "false")
            return 0

        if args.cmd == "intersects-polygon":
            batch = _read_batch_lines(args.file, args.stdin)
            if batch:
                out = []
                for line in batch:
                    parts = [p.strip() for p in line.split(",")] if "," in line else line.split()
                    if len(parts) < 4:
                        raise ValueError("Expected lines: locator lat,lon lat,lon lat,lon ...")
                    locator = parts[0]
                    poly = _parse_polygon_points(parts[1:])
                    out.append("true" if intersects_polygon(locator, poly) else "false")
                if args.format == "json":
                    print(_json_dumps(out))
                else:
                    print("\n".join(out))
                return 0
            poly = _parse_polygon_points(args.points)
            print("true" if intersects_polygon(args.locator, poly) else "false")
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
