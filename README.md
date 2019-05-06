# osm-stop-import

_Under construction_

```
usage: update-tags.py [-h] [-s] input.osm input.csv output.osm

Finds HSL public transport stops from jOSM-file (.osm) and modifies it's OSM-tags
with HSL JORE stop data using 'ref'-tag value as an identifier.

Following transformations are made for the output jOSM-file:
 - 'ref'-tag values are prefixed with letter 'H'.
 - Adds 'shelter'-tag with value 'yes' or 'no'.
 - Adds 'name', 'name:fi', and 'name:sv'-tag if missing.

positional arguments:
  input.osm    Source .OSM-file
  input.csv    JORE data in CSV-format
  output.osm   The ouput .OSM-file with transformed ref-tags, name and shelter
               info.

optional arguments:
  -h, --help   show this help message and exit
  -s, --stats  Prints out more verbose stats about script results
```

Please see https://wiki.openstreetmap.org/wiki/Finland:HSL/HSL_bus_stop_import
