# Maidenhead

A Python library for working with Maidenhead grid squares, geographic locators used mainly in Amateur Radio. Includes a command line utility for working with Maidenhead grid system.

## Maidenhead CLI (mh)

Command-line utilities for working with Maidenhead grid squares.

### Usage

mh <command> [options] [args]

### Commands

#### normalize

Normalize locator casing and validate.

* mh normalize FN31pr

* mh normalize qf56oc

* mh normalize --stdin --format json

#### validate

Validate a locator. Exit code 0 if valid, 2 if invalid.

* mh validate JO22db

* mh validate AA0

* mh validate AA0 --print   # prints "invalid"

#### center

Print the center latitude/longitude of a locator.

* mh center QF56oc

* mh center QF56oc --digits 4

* mh center QF56oc --csv

* mh center --file locators.txt --format csv

* mh center --stdin --format json

#### bbox

Print bounding box as min_lat min_lon max_lat max_lon.

* mh bbox EM12rx

* mh bbox EM12rx --digits 5

* mh bbox EM12rx --csv

* mh bbox --file locators.txt --format csv

#### parts

Print locator components (field/square/subsquare/etc).

* mh parts IO83rj42

* mh parts FN31pr

#### size

Print cell size (width height) for a locator.

* mh size IO83rj

* mh size IO83rj --unit km

* mh size IO83rj --unit km --lon-at 45

* mh size IO83rj --unit km --at-lat 10 --method spherical

* mh size IO83rj --unit miles --csv

#### area

Print cell area (km^2).

* mh area IO83rj

* mh area IO83rj --method geodesic

#### diagonal

Print cell diagonal length (km).

* mh diagonal IO83rj

* mh diagonal IO83rj --method geodesic

#### step

Move a locator by a number of grid cells.

* mh step IO83rj --dlat-cells 1

* mh step IO83rj --dlon-cells -2

#### from-latlon

Convert latitude/longitude to a locator.

* mh from-latlon 35.6895 139.6917

* mh from-latlon 35.6895,139.6917

* mh from-latlon -22.9068 -43.1729 --precision 8

* mh from-latlon 90 180 --no-clamp   # error

* mh from-latlon --file coords.txt --format json

* mh from-latlon --stdin --format plain

Batch input expects one lat,lon (or lat lon) per line.

#### format

Coerce locator precision.

* mh format IO83rj --precision 4 --mode truncate

* mh format IO83rj --precision 6 --mode center

* mh format IO83rj --precision 6 --mode error

#### GeoJSON

Emit GeoJSON for a locator or batch.

* mh geojson JO22db

* mh geojson JO22db --geojson-format featurecollection

* mh geojson --stdin --geojson-format featurecollection

Notes:

- Batch GeoJSON requires --geojson-format featurecollection.

- JSON output uses orjson (install with pip install orjson).

#### utm

Print the UTM zone for a locator.

* mh utm IO83rj

#### cover-circle

Cover a circle with grid squares (space-separated output by default).

* mh cover-circle 0.0,0.0 5 --precision 4

* mh cover-circle IO83rj 10 --precision 6 --csv

Batch input expects: center radius_km precision

* mh cover-circle --stdin --format json

#### cover-line

Cover a line with grid squares.

* mh cover-line 0.0,0.0 1.0,1.0 --precision 4

* mh cover-line IO83rj FN31pr --precision 4 --method geodesic

Batch input expects: start end precision

* mh cover-line --file lines.txt --format csv

#### distance

Distance (km) between two locators or points (lat,lon).

* mh distance IO83rj FN31pr

* mh distance -33.8688,151.2093 51.5074,-0.1278

* mh distance IO83rj FN31pr --method geodesic

Mixed input is supported (locator and lat,lon together):

* mh distance IO83rj 51.5074,-0.1278

#### bearing

Initial bearing (degrees) from A to B.

* mh bearing CM98jw JO22db

* mh bearing 37.7749,-122.4194 48.8566,2.3522

Mixed input is supported (locator and lat,lon together):

* mh bearing IO83rj 51.5074,-0.1278

#### midpoint

Great-circle midpoint between A and B.

* mh midpoint RF82ib JP12fk

* mh midpoint 40.4168,-3.7038 55.7558,37.6173

* mh midpoint RF82ib JP12fk --csv

### Global Options

Most coordinate outputs share:

- --digits N: decimal places for numeric output (default 6)

- --csv: comma-separated output

Batch input options:

- --file PATH: read input lines from a file

- --stdin: read input lines from stdin

- --format plain|csv|json: output format for batch mode

### Exit Codes

- 0: success (valid input)

- 2: invalid input / usage error

———
