# Maidenhead

A Python library for working with Maidenhead grid squares, geographic locators used mainly in Amateur Radio. Includes a command line utility for working with Maidenhead grid system.

## Release

Planned tag: `v1.0.0rc1`.

## Changelog

### 1.0.0rc1

- Release candidate for 1.0 with expanded and stabilized API surface.
- Adds comprehensive bulk and vectorized helpers (list, numpy, pandas).
- Adds CLI parity for new API features, plus improved help output.
- Adds GeoJSON/WKT support for locator and lat/lon inputs, including mixed inputs.
- Improves antimeridian handling and adds polar-edge test coverage.
- Updates README with full API/CLI coverage, output shapes, and 1.0 checklist items.

## Install

From a local package build (recommended to avoid PyPI name conflicts):

- Wheel: `python -m pip install dist/maidenhead-1.0.0rc1-py3-none-any.whl`
- sdist: `python -m pip install dist/maidenhead-1.0.0rc1.tar.gz`

Editable install for development:

`python -m pip install -e .`

## Quickstart

Python:

```python
from maidenhead import from_latlon

grid = from_latlon(53.073219, -3.934023, precision=6)
print(grid.locator)
```

CLI:

`mh from-latlon 53.073219,-3.934023`

## Python API

Basic usage:

```python
from maidenhead import normalize, from_latlon, to_center_latlon, to_bbox

loc = normalize("io83ri")
grid = from_latlon(53.073219, -3.934023, precision=6)
center = to_center_latlon("IO83ri")
bbox = to_bbox("IO83ri")
```

Precision:

- Locators use even precision lengths: 2, 4, 6, 8, 10 (strict validation).
- Use `format_locator(locator, precision=..., mode="truncate|center|error")` to coerce precision.
- Use `precision_of(locator)` to read the precision.

GridSquare:

- `from_latlon` returns a `GridSquare`, and most helpers accept either a locator string or `GridSquare`.
- Useful attributes: `.locator`, `.precision`, `.center`, `.bbox`.

Neighborhood and topology:

- `neighbors(locator, ring=1, diagonals=True)` returns surrounding locators.
- `adjacent(locator, diagonals=True)` returns a direction map.
- `step(locator, dlat_cells=0, dlon_cells=1)` moves by grid cells.
- `parent(locator, precision=...)` and `children(locator, precision=...)` adjust precision.

Geometry and containment:

- `corners(locator)` returns NW/NE/SW/SE.
- `contains(outer, inner)` and `contains_point(locator, lat, lon)`.
- `intersects_bbox(locator, bbox)` and `intersects_polygon(locator, polygon)`.
- `split_bbox(bbox)` / `split_bbox_list(bbox)` for antimeridian-safe handling.

Geo outputs:

- `to_geojson_polygon`, `to_geojson_feature`, `to_geojson_feature_collection`
- `to_geojson_bbox`, `to_geojson_envelope`
- `to_wkt(locator)`
- `to_utm_zone(locator)`

Geodesy helpers:

- `distance_km(a, b, method="spherical|geodesic")`
- `bearing_deg(a, b)`
- `initial_bearing(locator_a, locator_b)`
- `azimuth(a, b, range_mode=False)`
- `midpoint(a, b)`
- `great_circle_path(a, b, n=100)`
- `bearing_bin(a, b, bin_size=5)`
- `azimuthal_sector(a, b, width_deg)`

Bulk and vectorized APIs:

- `maidenhead.bulk` provides list-based helpers like `from_latlon_many`, `to_bbox_many`.
- `maidenhead.vector` provides numpy/pandas-aware helpers (Series in -> Series out).
- Both bulk and vector helpers require equal-length inputs for paired operations and raise `ValueError` on mismatch.

Bulk/vector output shapes (examples):

- `from_latlon_many([lat...],[lon...])` -> `["IO83ri", "FN31pr"]`
- `to_center_many(["IO83ri", "FN31pr"])` -> `[(lat, lon), (lat, lon)]`
- `to_bbox_many(["IO83ri"])` -> `[(min_lat, min_lon, max_lat, max_lon)]`
- `corners_many(["IO83ri"])` -> `[{"nw": (lat, lon), "ne": ..., "sw": ..., "se": ...}]`
- `split_bbox_many(["RR00"])` -> `[[(min_lat, min_lon, max_lat, max_lon), (min_lat, min_lon, max_lat, max_lon)]]`
- `to_geojson_polygon_many(["IO83ri"])` -> `[{"type": "Polygon", "coordinates": ...}]`
- `to_geojson_feature_many(["IO83ri"])` -> `[{"type": "Feature", "geometry": ..., "properties": ...}]`
- `to_geojson_features_many(["IO83ri"])` -> `[{"type": "Feature", ...}, ...]`
- `to_geojson_bbox_many(["IO83ri"])` -> `[{"type": "Polygon", "bbox": ..., "coordinates": ...}]`
- `to_wkt_many(["IO83ri"])` -> `["POLYGON ((...))"]`
- `azimuth_many(["IO83ri"], ["FN31pr"])` -> `[(bearing_deg, distance_km)]`
- `precision_many(["IO83ri"])` -> `[6]`

Vectorized helpers in `maidenhead.vector` mirror the bulk names and return pandas Series when the inputs are Series; otherwise they return lists or numpy arrays depending on the input types.

Exceptions:

- `InvalidLocatorError`, `PrecisionError`, `OutOfRangeError` surface validation failures.

Additional exported helpers:

Core:

- `MaidenheadError`: base exception for library errors. Example: `except MaidenheadError: ...`
- `parse`: parse a locator into a `GridSquare`. Example: `parse("IO83ri").precision`
- `is_valid`: boolean validation. Example: `is_valid("IO83")`
- `normalize_many`: normalize a list of locators. Example: `normalize_many(["io83ri", "fn31pr"])`
- `to_bbox_split`: split a locator bbox across the dateline. Example: `to_bbox_split("RR00")`

Cell metrics:

- `cell_size`: cell size with units. Example: `cell_size("IO83ri", unit="km", at_lat=53.0)`
- `cell_size_deg`: cell size in degrees. Example: `cell_size_deg("IO83ri")`
- `area_km2`: area estimate in km^2. Example: `area_km2("IO83ri")`
- `diagonal_km`: diagonal length in km. Example: `diagonal_km("IO83ri")`

Coverage:

- `cover_circle`: cells intersecting a circle. Example: `cover_circle("IO83rj", 5, 6)`
- `cover_line`: cells intersecting a path. Example: `cover_line("IO83rj", "FN31pr", 4)`

Bulk list helpers (list in, list out):

- `cell_size_many`: `cell_size_many(["IO83ri", "FN31pr"], unit="km")`
- `cell_size_deg_many`: `cell_size_deg_many(["IO83ri", "FN31pr"])`
- `cell_size_km_many`: `cell_size_km_many(["IO83ri", "FN31pr"])`
- `area_km2_many`: `area_km2_many(["IO83ri", "FN31pr"])`
- `diagonal_km_many`: `diagonal_km_many(["IO83ri", "FN31pr"])`
- `parent_many`: `parent_many(["IO83ri", "FN31pr"], precision=4)`
- `children_many`: `children_many(["IO83ri"], precision=8)`
- `to_wkt_many`: `to_wkt_many(["IO83ri", "FN31pr"])`
- `azimuth_many`: `azimuth_many(["IO83ri"], ["FN31pr"])`
- `contains_point_many`: `contains_point_many(["IO83ri"], [(53.1, -3.9)])`
- `contains_many`: `contains_many(["IO83ri"], ["IO83rj"])`
- `corners_many`: `corners_many(["IO83ri", "FN31pr"])`
- `split_bbox_many`: `split_bbox_many(["RR00", "IO83ri"])`
- `neighbors_many`: `neighbors_many(["IO83ri", "FN31pr"])`
- `adjacent_many`: `adjacent_many(["IO83ri"])`
- `precision_many`: `precision_many(["IO83ri", "FN31pr"])`
- `intersects_bbox_many`: `intersects_bbox_many(["IO83ri"], [(-1, -2, 1, 2)])`
- `intersects_polygon_many`: `intersects_polygon_many(["IO83ri"], [[[0, 0], [1, 0], [1, 1], [0, 1]]])`
- `initial_bearing_many`: `initial_bearing_many(["IO83ri"], ["FN31pr"])`
- `to_utm_zone_many`: `to_utm_zone_many(["IO83ri", "FN31pr"])`
- `to_geojson_polygon_many`: `to_geojson_polygon_many(["IO83ri", "FN31pr"])`
- `to_geojson_feature_many`: `to_geojson_feature_many(["IO83ri", "FN31pr"])`
- `to_geojson_features_many`: `to_geojson_features_many(["IO83ri", "FN31pr"])`
- `to_geojson_bbox_many`: `to_geojson_bbox_many(["IO83ri", "FN31pr"])`
- `to_geojson_envelope_many`: `to_geojson_envelope_many(["IO83ri", "FN31pr"])`
- `to_center_many`: `to_center_many(["IO83ri", "FN31pr"])`

Optional dependencies:

Required dependencies:

- `pandas`: vectorized Series helpers in `maidenhead.vector`.
- `orjson`: JSON output in CLI and GeoJSON helpers.

Optional dependencies:

- `numpy`: vectorized numeric outputs in `maidenhead.vector`.
- `geographiclib`: geodesic distance and area calculations.

## Maidenhead CLI (mh)

Command-line utilities for working with Maidenhead grid squares.

### Usage

`mh <command> [options] [args]`

Show version:

- `mh --version`

### Commands

#### normalize

Normalize locator casing and validate.

- `mh normalize FN31pr`
- `mh normalize qf56oc`
- `mh normalize --stdin --format json`

#### validate

Validate a locator. Exit code 0 if valid, 2 if invalid.

- `mh validate JO22db`
- `mh validate AA0`
- `mh validate AA0 --print   # prints "invalid"`

#### center

Print the center latitude/longitude of a locator.

- `mh center QF56oc`
- `mh center QF56oc --digits 4`
- `mh center QF56oc --csv`
- `mh center --file locators.txt --format csv`
- `mh center --stdin --format json`

#### bbox

Print bounding box as min_lat min_lon max_lat max_lon.

- `mh bbox EM12rx`
- `mh bbox EM12rx --digits 5`
- `mh bbox EM12rx --csv`
- `mh bbox --file locators.txt --format csv`

#### bbox-split

Split a bbox that crosses the antimeridian.

- `mh bbox-split 10 170 20 -170`
- `mh bbox-split 10 170 20 -170 --csv`

#### bbox-split-list

Return a list of bboxes (1 or 2).

- `mh bbox-split-list 10 170 20 -170 --format json`

#### parts

Print locator components (field/square/subsquare/etc).

- `mh parts IO83rj42`
- `mh parts FN31pr`

#### size

Print cell size (width height) for a locator.

- `mh size IO83rj`
- `mh size IO83rj --unit km`
- `mh size IO83rj --unit km --lon-at 45`
- `mh size IO83rj --unit km --at-lat 10 --method spherical`
- `mh size IO83rj --unit miles --csv`

#### area

Print cell area (km^2).

- `mh area IO83rj`
- `mh area IO83rj --method geodesic`

#### diagonal

Print cell diagonal length (km).

- `mh diagonal IO83rj`
- `mh diagonal IO83rj --method geodesic`

#### corners

Print the NW, NE, SW, SE corners of a locator.

- `mh corners IO83ri`
- `mh corners IO83ri --csv`

#### precision

Print locator precision (character length).

- `mh precision IO83ri`

#### neighbors

List neighboring locators.

- `mh neighbors IO83ri`
- `mh neighbors IO83ri --ring 2`
- `mh neighbors IO83ri --diagonals`
- `mh neighbors IO83ri --no-diagonals`

#### adjacent

List adjacent locators with directions.

- `mh adjacent IO83ri`
- `mh adjacent IO83ri --diagonals`
- `mh adjacent IO83ri --no-diagonals`

#### step

Move a locator by a number of grid cells.

- `mh step IO83rj --dlat-cells 1`
- `mh step IO83rj --dlon-cells -2`

#### from-latlon

Convert latitude/longitude to a locator.

- `mh from-latlon 35.6895 139.6917`
- `mh from-latlon 35.6895,139.6917`
- `mh from-latlon 53.073219, -3.934023`
- `mh from-latlon -22.9068 -43.1729 --precision 8`
- `mh from-latlon 90 180 --no-clamp   # error`
- `mh from-latlon --file coords.txt --format json`
- `mh from-latlon --stdin --format plain`

Batch input expects one lat,lon (or lat lon) per line.

#### format

Coerce locator precision.

- `mh format IO83rj --precision 4 --mode truncate`
- `mh format IO83rj --precision 6 --mode center`
- `mh format IO83rj --precision 6 --mode error`

#### parent

Return parent locator at lower precision.

- `mh parent IO83ri`
- `mh parent IO83ri --precision 4`

#### children

List child locators at higher precision.

- `mh children IO83ri`
- `mh children IO83ri --precision 8 --limit 10`

#### GeoJSON

Emit GeoJSON for a locator, a lat/lon point, or batch input.

- `mh geojson JO22db`
- `mh geojson 53.073219,-3.934023`
- `mh geojson 53.073219, -3.934023`
- `mh geojson JO22db 53.073219,-3.934023   # mixed inputs`
- `mh geojson JO22db --geojson-format featurecollection`
- `mh geojson --stdin --geojson-format featurecollection`

Notes:

- `--geojson-format` supports: `polygon` | `feature` | `featurecollection` | `bbox` | `envelope`
- Mixed inputs are supported for `feature` and `featurecollection` outputs.
- `--split outputs` antimeridian-safe geometry for bbox/envelope formats.
- Batch GeoJSON requires `--geojson-format featurecollection`.
- JSON output uses orjson (install with pip install orjson).

#### wkt

Emit WKT polygon for a locator or lat/lon.

- `mh wkt IO83ri`
- `mh wkt 53.073219,-3.934023`
- `mh wkt 53.073219, -3.934023`

#### utm

Print the UTM zone for a locator.

- `mh utm IO83rj`

#### contains

Check if one locator contains another.

- `mh contains IO83 IO83ri`

#### contains-point

Check if locator contains a point (lat lon).

- `mh contains-point IO83ri 53.073219,-3.934023`

#### intersects-bbox

Check if a locator intersects a bbox.

- `mh intersects-bbox IO83ri 50.0 -4.0 55.0 2.0`

#### intersects-polygon

Check if a locator intersects a polygon.

- `mh intersects-polygon IO83ri 50.0,-4.0 50.0,2.0 55.0,2.0 55.0,-4.0`

#### cover-circle

Cover a circle with grid squares (space-separated output by default).

- `mh cover-circle 0.0,0.0 5 --precision 4`
- `mh cover-circle IO83rj 10 --precision 6 --csv`
- `mh cover-circle 53.073219, -3.934023 5 --precision 4`

Batch input expects: center radius_km precision

- `mh cover-circle --stdin --format json`

#### cover-line

Cover a line with grid squares.

- `mh cover-line 0.0,0.0 1.0,1.0 --precision 4`
- `mh cover-line IO83rj FN31pr --precision 4 --method geodesic`
- `mh cover-line 53.073219, -3.934023 51.5074,-0.1278 --precision 4`

Batch input expects: start end precision

- `mh cover-line --file lines.txt --format csv`

#### great-circle

Print points along a great-circle path.

- `mh great-circle 0.0,0.0 1.0,1.0 --points-count 5`
- `mh great-circle 53.073219, -3.934023 51.5074,-0.1278 --points-count 10 --csv`

Outputs one point per line as lat lon (or lat,lon with --csv).

#### bearing-bin

Return the bearing bin start angle from A to B.

- `mh bearing-bin 0.0,0.0 0.0,10.0 --bin-size 10`

#### azimuthal-sector

Return a bearing sector (start end) from A to B.

- `mh azimuthal-sector 0.0,0.0 0.0,10.0 --width 20`
- `mh azimuthal-sector 0.0,0.0 0.0,10.0 --width 20 --csv`

#### distance

Distance (km) between two locators or points (lat,lon).

- `mh distance IO83rj FN31pr`
- `mh distance -33.8688,151.2093 51.5074,-0.1278`
- `mh distance IO83rj FN31pr --method geodesic`

Mixed input is supported (locator and lat,lon together):

- `mh distance IO83rj 51.5074,-0.1278`

Comma-space input is supported:

- `mh distance 53.073219, -3.934023 51.5074,-0.1278`

#### bearing

Initial bearing (degrees) from A to B.

- `mh bearing CM98jw JO22db`
- `mh bearing 37.7749,-122.4194 48.8566,2.3522`

Mixed input is supported (locator and lat,lon together):

- `mh bearing IO83rj 51.5074,-0.1278`
- `mh bearing 53.073219, -3.934023 51.5074,-0.1278`

#### azimuth

Return bearing and distance between A and B.

- `mh azimuth IO83ri FN31pr`
- `mh azimuth 53.073219,-3.934023 51.5074,-0.1278`
- `mh azimuth IO83ri 51.5074,-0.1278`
- `mh azimuth IO83ri FN31pr --range`

#### initial-bearing

Initial bearing (deg) between two locators.

- `mh initial-bearing IO83ri FN31pr`

#### midpoint

Great-circle midpoint between A and B.

- `mh midpoint RF82ib JP12fk`
- `mh midpoint 40.4168,-3.7038 55.7558,37.6173`
- `mh midpoint RF82ib JP12fk --csv`

#### bulk

Bulk operations for locators/latlon.

- `mh bulk normalize --stdin`
- `mh bulk from-latlon --file coords.txt --format json`
- `mh bulk center --stdin --format csv`
- `mh bulk bbox --stdin --format json`
- `mh bulk size --stdin --unit km --format csv`
- `mh bulk geojson --stdin --geojson-format featurecollection --format json`

Batch input:

- locators: one per line
- lat/lon: "lat lon" or "lat,lon" (comma+space accepted)

Supported ops:

normalize, from-latlon, center, bbox, wkt, contains-point, contains,
intersects-bbox, intersects-polygon, azimuth, initial-bearing, neighbors,
adjacent, corners, precision, parent, children, size, area, diagonal, utm,
geojson, bbox-split, bbox-split-list

### Global Options

Most coordinate outputs share:

- `--digits N`: decimal places for numeric output (default 6)
- `--csv`: comma-separated output

Batch input options:

- `--file PATH`: read input lines from a file
- `--stdin`: read input lines from stdin
- `--format plain|csv|json`: output format for batch mode

### Exit Codes

- `0`: success (valid input)
- `2`: invalid input / usage error

———
