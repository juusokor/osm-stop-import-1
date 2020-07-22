# osm-stop-import

_Under construction_

This repo consists of tools and documentation for https://wiki.openstreetmap.org/wiki/Finland:HSL/HSL_bus_stop_import.

Goal of the import is twofold:
1. Add "H"-prefix to OSM public transportation stops `ref`-tag within Helsinki.
2. Add features from HSL stop data to OSM public transportation stops within whole HSL area: name, finnish name, swedish name and if stop is sheltered.

## Requirements:

Python 3.8 (or you can [run it with Docker](#Run-with-Docker) )

[jOSM](https://josm.openstreetmap.de/)

## Get data

This repo has example data tagged as EXAMPLE for testing purposes. To use up-to-date data follow these steps.

Get OSM stop data via [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) query `hki-osm-stops-overpassturbo-query.txt` using jOSM:
1. Open jOSM > Preferences (F12) > Enable "Expert mode" by ticking box in bottom left corner of the Settings dialog.
2. Download map data (Ctrl + Shift + Down) > Choose tab "Download from Overpass API" > Copy and paste the content of `hki-osm-stops-overpassturbo-query.txt` > Download data
3. Save the resulting data set: File > Save as > Save as `hsl-osm-stops.osm`

Get HSL public transportation stop data from [HSL ArcGIS Online portal](https://public-transport-hslhrt.opendata.arcgis.com/datasets/hsln-pys%C3%A4kit)
1. Choose Download > Spreadsheet
2. Save the resulting .csv-file, for example `hsl-stop-data.csv`

## Run the script

`python update-tags.py -s hsl-osm-stops.osm hsl-stop-data.csv output.osm`

```
usage: update-tags.py [-h] [-s] input.osm input.csv output.osm

Finds HSL public transport stops from jOSM-file (.osm) and modifies it's OSM-tags with HSL (JORE) stop data (.csv) using 'ref'-tag value as an identifier.

Following transformations are made for the output jOSM-file:
 - 'ref'-tag values of stops in Helsinki are prefixed with letter 'H'.
 - Adds 'shelter'-tag with value 'yes' or 'no'.
 - Adds 'name', 'name:fi', and 'name:sv'-tag if missing.

positional arguments:
  input.osm    Source .OSM-file
  input.csv    HSL stop data in CSV-format
  output.osm   The ouput .OSM-file with transformed ref-tags, name and shelter info.

optional arguments:
  -h, --help   show this help message and exit
  -s, --stats  Prints out more verbose stats about script results
```

### Run with Docker

Build image

`docker build -t osm-stop-import .`

Run the container with current directory containing the necessary data as bind mount and pass the required command line parameters as environment variables (INPUT, STOPS, OUTPUT):

`docker run -v $PWD:$PWD -w $PWD -e INPUT='hsl-osm-stops-2020-07-22-EXAMPLE-ONLY.osm' -e STOPS='hsl-stop-data-2020-07-22-EXAMPLE-ONLY.csv' -e OUTPUT='output-2020-07-22-EXAMPLE.osm' osm-stop-import`

## Validate results

Open the output.osm in JOSM and validate the changes.

TODO


Please see https://wiki.openstreetmap.org/wiki/Finland:HSL/HSL_bus_stop_import
