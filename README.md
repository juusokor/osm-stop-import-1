# osm-stop-import

This repo consists of tools for one-time OSM import for importing attributes of [HSL public transportation stop data](https://public-transport-hslhrt.opendata.arcgis.com/datasets/hsln-pys%C3%A4kit) into OSM. Further details: https://wiki.openstreetmap.org/wiki/Finland:HSL/HSL_bus_stop_import.

The import has two goals:
1. Add "H"-prefix to OSM public transportation stops `ref`-tag within Helsinki.
2. Add attributes from HSL stop data to OSM public transportation stops within **whole** HSL area: name, finnish name, swedish name and info if stop is sheltered.

## Requirements:

Python 3.8 (or you can [run it with Docker](#Run-with-Docker) )

[jOSM](https://josm.openstreetmap.de/)

## Get data

This repo has example data tagged as EXAMPLE for testing purposes. To use up-to-date data follow these steps.

Get OSM stop data via [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) query `hsl-osm-stops-overpassturbo-query.txt` using jOSM:
1. Open jOSM > Preferences (F12) > Enable "Expert mode" by ticking box in bottom left corner of the Settings dialog.
2. Download map data (Ctrl + Shift + Down) > Choose tab "Download from Overpass API" > Copy and paste the content of `hsl-osm-stops-overpassturbo-query.txt` > Download data
3. Save the resulting data set: File > Save as > Save as `hsl-osm-stops.osm`

Get HSL public transportation stop data from [HSL ArcGIS Online portal](https://public-transport-hslhrt.opendata.arcgis.com/datasets/hsln-pys%C3%A4kit)
1. Choose APIs > GeoJSON 
2. Save the resulting .geojson-file, for example `hsl-stop-data.geojson`

## Run the script

`python update-tags.py hsl-osm-stops.osm hsl-stop-data.geojson output.osm`

```
usage: update-tags.py [-h] input.osm input.geojson output.osm

Finds HSL public transport stops from a jOSM-file (.osm) and modifies it's OSM-tags
with HSL (JORE) stop data (.geojson) using 'ref'-tag value as an identifier.

Following transformations are made for the output jOSM-file:
 - 'ref'-tag values of stops in Helsinki are prefixed with the letter 'H'.
 - Adds 'shelter'-tag with value 'yes' or 'no'.
 - Adds 'name', 'name:fi', and 'name:sv'-tag if missing.

positional arguments:
  input.osm      Source .OSM-file
  input.geojson  HSL stop data in GeoJSON-format
  output.osm     The ouput .OSM-file with transformed ref-tags, name and shelter info.

optional arguments:
  -h, --help     show this help message and exit
```

### Run with Docker

Build image

`docker build -t osm-stop-import .`

Run the container with current directory containing the necessary data as bind mount and pass the files as required command line parameters.:

`docker run -it -v $PWD:/osm-stop-import/ osm-stop-import input.osm stops.csv output.osm`

## Validate results

Inspect log files:

|     |     |
| --- | --- |
| update-tags.log | General output, matches, errors, stats |
| osm_refs_missing_jore_match.csv | OSM-stops that are missing a JORE stop match |
| shelter_conflicts.csv | OSM-stops where shelter info is in conflict with JORE data |
| matched_stops_exceeding_max_distance_limit.csv | OSM-stops that have a JORE match, but the distance between the two stops exceeds max distance limit (default 100m) |


Open the `output.osm` in JOSM and eyball and validate the changes.


Please see https://wiki.openstreetmap.org/wiki/Finland:HSL/HSL_bus_stop_import
