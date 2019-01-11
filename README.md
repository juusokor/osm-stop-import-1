﻿# osm-stop-import

_Under construction_

```
usage: update-tags.py [-h] input.osm input.csv output.osm

Finds public transport stop ref-tags from jOSM-file (.osm). Prefixes ref-tag
values with letter 'H'. Adds 'shelter=yes/no'-tag. Adds name, name:fi and
name:sv-tags

positional arguments:
 input.osm   Source .OSM-file containing ref-tags
 input.csv   Jore data in CSV-format
 output.osm  The ouput .OSM-file with transformed ref-tags, name and shelter
             info.

optional arguments:
 -h, --help  show this help message and exit
```
