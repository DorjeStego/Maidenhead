# Maidenhead

A Python library for working with Maidenhead grid squares, geographic locators used mainly in Amateur Radio. Includes a command line utility for working with Maidenhead grid system.

## Maidenhead CLI (mh)

Command-line utilities for working with Maidenhead grid squares.

### Usage

mh <command> [options] [args]

### Commands

#### normalize

Normalize locator casing and validate.

mh normalize FN31pr

mh normalize qf56oc

#### validate

Validate a locator. Exit code 0 if valid, 2 if invalid.

mh validate JO22db

mh validate AA0

mh validate AA0 --print   # prints "invalid"

#### center

Print the center latitude/longitude of a locator.

mh center QF56oc

mh center QF56oc --digits 4

mh center QF56oc --csv

#### bbox

Print bounding box as min_lat min_lon max_lat max_lon.

mh bbox EM12rx

mh bbox EM12rx --digits 5

mh bbox EM12rx --csv

#### parts

Print locator components (field/square/subsquare/etc).

mh parts IO83ri17

mh parts FN31pr

#### size

Print cell size (width height) for a locator.

mh size IO83ri

mh size IO83ri --unit km

mh size IO83ri --unit km --lon-at 45

mh size IO83ri --unit miles --csv

#### from-latlon

Convert latitude/longitude to a locator.

mh from-latlon 35.6895 139.6917

mh from-latlon 35.6895,139.6917

mh from-latlon -22.9068 -43.1729 --precision 8

mh from-latlon 90 180 --no-clamp   # error

#### distance

Distance (km) between two locators or points (lat,lon).

mh distance IO83ri FN31pr

mh distance -33.8688,151.2093 51.5074,-0.1278

mh distance IO83ri FN31pr --method geodesic

#### bearing

Initial bearing (degrees) from A to B.

mh bearing CM98jw JO22db

mh bearing 37.7749,-122.4194 48.8566,2.3522

#### midpoint

Great-circle midpoint between A and B.

mh midpoint RF82ib JP12fk

mh midpoint 40.4168,-3.7038 55.7558,37.6173

mh midpoint RF82ib JP12fk --csv

### Global Options

Most coordinate outputs share:

- --digits N: decimal places for numeric output (default 6)

- --csv: comma-separated output

### Exit Codes

- 0: success (valid input)

- 2: invalid input / usage error

———
