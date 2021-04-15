#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command line tool for importing HSL public transportation (JORE) stop data to OpenStreetMap.

Usage: python update-tags.py -h

Requires: Python 3.8 or later
"""
from dataclasses import dataclass, InitVar
from xml.etree import ElementTree as et
import csv
import argparse
import textwrap
import logging
import json
from collections import Counter
import datetime
import functools
from shapely import geometry
from pyproj import CRS, Transformer

STATS = {
    "matched": 0,
    "not_within_max_distance": 0,
    "prefixed": 0,
    "sheltered_yes": 0,
    "sheltered_no": 0,
    "shelter_nodata": 0,
    "named": 0,
    "named_fi": 0,
    "named_sv": 0,
}
OSM_URL = "https://www.openstreetmap.org"

# Global coordinate transformer object. WGS84 is EPSG:4326 and ETRS-TM35FIN is EPSG:3067
COORD_TRANSFORMER = Transformer.from_crs(4326, 3067)


@dataclass
class Stop:
    """Dataclass object that represents JORE stop with attributes relevant to the stop import."""

    id: str
    stop_id: str
    name: str
    name_sv: str
    lat: str
    lon: str
    shelter_param: InitVar[str]
    valid_route_param: InitVar[int]
    valid_timetable_param: InitVar[int]
    municipality: str = None
    shelter: str = "yes"  # The stop is sheltered by default
    valid_route_and_timetable: bool = True

    def __post_init__(self, shelter_param, valid_route_param, valid_timetable_param):
        """Get values for shelter and municipality"""
        # JORE stop type values for non-sheltered stops
        # 04 stands for a pole and 08 for stop position. 99 unknown.
        if shelter_param in ("04", "08"):
            self.shelter = "no"
        elif shelter_param == "99":
            self.shelter = "unknown"

        # Is the stop in Helsinki? H for Helsinki, XH for virtual stop in Helsinki
        if self.stop_id[:1] == "H" or self.stop_id[:2] == "XH":
            self.municipality = "Helsinki"

        # A stop withouth valid routes or timetables is excluded from the import
        if valid_route_param == 0 and valid_timetable_param == 0:
            self.valid_route_and_timetable = False


def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
        Finds HSL public transport stops from a jOSM-file (.osm) and modifies it's OSM-tags
        with HSL (JORE) stop data (.geojson) using 'ref'-tag value as an identifier.

        Following transformations are made for the output jOSM-file:
         - 'ref'-tag values of stops in Helsinki are prefixed with the letter 'H'.
         - Adds 'shelter'-tag with value 'yes' or 'no'.
         - Adds 'name', 'name:fi', and 'name:sv'-tag if missing."""
        ),
    )
    parser.add_argument("input_osm", metavar="input.osm", help="Source .OSM-file")
    parser.add_argument(
        "input_stops", metavar="input.geojson", help="HSL stop data in GeoJSON-format"
    )
    parser.add_argument(
        "output",
        metavar="output.osm",
        help="The ouput .OSM-file with transformed ref-tags, name and shelter info.",
    )
    return parser.parse_args()


def read_stop_data_geojson(input_file):
    """Read stop data in GeoJSON format and return a list of Stop-objects with the relevant data for import."""
    stops = []
    try:
        with open(input_file, newline="", encoding="utf8") as jsonfile:
            data = json.load(jsonfile)
            for feature in data["features"]:
                jore_stop = feature["properties"]
                lat, lon = feature["geometry"]["coordinates"]
                new_stop = Stop(
                    jore_stop["SOLMUTUNNU"],
                    jore_stop["LYHYTTUNNU"],
                    jore_stop["NIMI1"],
                    jore_stop["NAMN1"],
                    lon,
                    lat,
                    jore_stop["PYSAKKITYY"],
                    jore_stop["REI_VOIM"],
                    jore_stop["AIK_VOIM"],
                )
                stops.append(new_stop)
    except Exception as e:
        logging.error(f"Error reading JORE stop data {input_file}: {e}", exc_info=True)
    return stops


def get_osm_tags(xml_element):
    """Return tags as a dict for OSM XML element."""
    return {
        element.get("k"): element.get("v") for element in xml_element.findall("tag")
    }


def update_tag(elem, key, value):
    """Add modify action to the XML element. Update value of chosen key of the 'tag'-element."""
    elem.set("action", "modify")
    for tag in elem.findall("tag"):
        if tag.attrib["k"] == key:
            tag.set("v", value)
            logging.info(f"   Updated '{key}'-tag with value: {value}")


def create_tag(elem, key, value):
    """Add modify action to element. Add a new tag-element to param elem with key and value."""
    elem.set("action", "modify")
    new_tag = {"k": key, "v": value}
    elem.append(et.Element("tag", new_tag))
    logging.info(f"   Created new tag {key}={value}")


def add_stop_name(elem, jore_stop):
    """Add stop name tag in Finnish and/or Swedish from JORE stop object with
    tag 'name' or 'name:sv' if the tag is missing.
    """
    tags = get_osm_tags(elem)

    if "name" not in tags.keys():
        create_tag(elem, "name", jore_stop.name)
        STATS["named"] += 1
    if "name:fi" not in tags.keys():
        create_tag(elem, "name:fi", jore_stop.name)
        STATS["named_fi"] += 1
    if "name:sv" not in tags.keys():
        create_tag(elem, "name:sv", jore_stop.name_sv)
        STATS["named_sv"] += 1


def write_list_dict_to_csv(filename, list_of_dicts):
    """Write list of dicts to csv. Use keys as fieldnames"""
    fieldnames = list_of_dicts[0].keys()
    with open(filename, mode="w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for item in list_of_dicts:
            writer.writerow(item)


def get_planar_distance_between_points(jore_coords, osm_coords):
    """Transform two WGS84 coordinate pairs to projected ETRS-TM35FIN coordinates and return rounded planar distance (m) between the two points"""

    jore_lat, jore_lon = COORD_TRANSFORMER.transform(jore_coords[0], jore_coords[1])
    osm_lat, osm_lon = COORD_TRANSFORMER.transform(osm_coords[0], osm_coords[1])

    jore_point = geometry.Point(jore_lat, jore_lon)
    osm_point = geometry.Point(osm_lat, osm_lon)

    return int(jore_point.distance(osm_point))


def main():
    log_filename = "update-tags.log"
    logging.basicConfig(
        filename=log_filename,
        filemode="w",
        level=logging.INFO,
        format="%(message)s",
    )
    args = parse_args()
    print("Executing...")
    etree = et.parse(args.input_osm)

    stops = read_stop_data_geojson(args.input_stops)

    all_jore_ref = {x.stop_id: x for x in stops}
    all_osm_refs = []
    osm_ref_missing_jore_match = []
    matched_stops_with_conflicting_shelter_info = []
    matched_but_not_within_distance_limit = []

    for elem in etree.getroot():

        osm_tags = get_osm_tags(elem)
        osm_ref = osm_tags.get("ref")

        if osm_ref:
            osm_id = elem.get("id")
            all_osm_refs.append(osm_ref)

            jore_stop = (
                all_jore_ref.get(osm_ref)
                or all_jore_ref.get("H" + osm_ref)
                or all_jore_ref.get("XH" + osm_ref[1:])
            )
            if jore_stop and jore_stop.valid_route_and_timetable:
                # In Helsinki the OSM ref-might already have the H-prefix.
                if osm_ref == jore_stop.stop_id or (
                    jore_stop.municipality == "Helsinki"
                    and osm_ref == jore_stop.stop_id[1:]
                    or osm_ref.replace("X", "XH") == jore_stop.stop_id
                ):
                    STATS["matched"] += 1
                    logging.info(
                        f"Matched ref {jore_stop.stop_id} between OSM-id: {OSM_URL}/{elem.tag}/{osm_id} and JORE stop: {jore_stop.id}"
                    )

                    stoptype = (
                        osm_tags.get("highway")
                        or osm_tags.get("railway")
                        or osm_tags.get("public_transport")
                    )
                    if stoptype:
                        logging.info(f"   Stop type: {stoptype}")

                    jore_coordinates = (jore_stop.lat, jore_stop.lon)
                    osm_coordinates = (elem.get("lat"), elem.get("lon"))
                    distance_difference = 0
                    if elem.tag == "node":
                        distance_difference = get_planar_distance_between_points(
                            jore_coordinates, osm_coordinates
                        )
                    if distance_difference < 100:
                        if jore_stop.municipality == "Helsinki":
                            new_ref_value = False
                            if osm_ref.startswith("X") and not osm_ref.startswith("XH"):
                                new_ref_value = osm_ref.replace("X", "XH")
                                logging.info(f"X -> Xh {new_ref_value}")
                            elif not osm_ref.startswith("H") and not osm_ref.startswith(
                                "X"
                            ):
                                new_ref_value = "H" + osm_ref
                            if new_ref_value:
                                update_tag(elem, "ref", new_ref_value)
                                STATS["prefixed"] += 1

                        if (
                            "shelter" not in osm_tags.keys()
                            and elem.tag != "relation"
                            and stoptype != "stop_position"
                        ):
                            if jore_stop.shelter == "yes":
                                create_tag(elem, "shelter", "yes")
                                STATS["sheltered_yes"] += 1
                            elif jore_stop.shelter == "no":
                                create_tag(elem, "shelter", "no")
                                STATS["sheltered_no"] += 1
                            elif jore_stop.shelter == "unknown":
                                STATS["shelter_nodata"] += 1
                                logging.info(f"   No shelter info in data.")
                        elif (
                            "shelter" in osm_tags.keys()
                            and jore_stop.shelter != "unknown"
                            and jore_stop.shelter != osm_tags.get("shelter")
                        ):
                            logging.info(
                                f"   Conflict in shelter info: JORE value: '{jore_stop.shelter}' vs OSM-value: '{osm_tags.get('shelter')}'"
                            )
                            matched_stops_with_conflicting_shelter_info.append(
                                {
                                    "JORE-ID": jore_stop.id,
                                    "REF": jore_stop.stop_id,
                                    "JORE-SHELTER": jore_stop.shelter,
                                    "OSM-SHELTER": osm_tags.get("shelter"),
                                    "OSM-ID": f"{OSM_URL}/{elem.tag}/{osm_id}",
                                }
                            )

                        any_name_tag_is_missing = any(
                            key not in osm_tags.keys()
                            for key in ["name", "name:fi", "name:sv"]
                        )
                        if any_name_tag_is_missing:
                            add_stop_name(elem, jore_stop)
                    else:
                        logging.info(
                            f"   SKIPPING: Distance difference {distance_difference} m between JORE stop and OSM stop is above max distance."
                        )
                        STATS["not_within_max_distance"] += 1
                        matched_but_not_within_distance_limit.append(
                            {
                                "JORE-ID": jore_stop.id,
                                "REF": jore_stop.stop_id,
                                "JORE-LAT": "{0:.5f}".format(jore_stop.lat),
                                "JORE-LON": "{0:.5f}".format(jore_stop.lon),
                                "OSM-LAT": osm_coordinates[0],
                                "OSM-LON": osm_coordinates[1],
                                "DISTANCE": distance_difference,
                                "OSM-ID": f"{OSM_URL}/{elem.tag}/{osm_id}",
                            }
                        )
            else:
                osm_ref_missing_jore_match.append(
                    {
                        "REF": osm_ref,
                        "OSM-ID": f"{OSM_URL}/{elem.tag}/{osm_id}",
                    }
                )

    # Print stats and results of transformation
    all_jore_ref_set = set(all_jore_ref)
    all_osm_refs_set = set(all_osm_refs)

    stat_msg = (
        f"JORE-stops: {len(all_jore_ref)}\n"
        f"Unique JORE stop_ids: {len(all_jore_ref_set)}\n"
        f"OSM stops with 'ref'-tag: {len(all_osm_refs)}\n"
        f"Unique OSM 'ref'-tags: {len(all_osm_refs_set)}\n"
        f"OSM stops 'ref'-tag values with JORE match: {STATS['matched']}\n"
        f"OSM stops 'ref'-tag values missing JORE match: {len(osm_ref_missing_jore_match)}"
    )
    print(stat_msg)
    logging.info(stat_msg)
    osm_missing_freq = Counter(([x["REF"] for x in osm_ref_missing_jore_match]))
    osm_missing_freq_sorted = {
        k: v for k, v in sorted(osm_missing_freq.items(), key=lambda item: item[1])
    }
    logging.info(
        "OSM stops 'ref'-tag values missing JORE match occurrence count (value  / count):"
    )
    logging.info(osm_missing_freq_sorted)

    write_list_dict_to_csv(
        "shelter_conflicts.csv",
        sorted(
            matched_stops_with_conflicting_shelter_info,
            key=lambda i: (i["JORE-SHELTER"], i["REF"]),
            reverse=True,
        ),
    )

    write_list_dict_to_csv(
        "osm_refs_missing_jore_match.csv",
        sorted(
            [x for x in osm_ref_missing_jore_match if len(x["REF"]) > 2],
            key=lambda i: i["REF"],
            reverse=True,
        ),  # Filter two digit refs as they are mostly platform refs for trains
    )

    write_list_dict_to_csv(
        "matched_stops_exceeding_max_distance_limit.csv",
        sorted(
            [x for x in matched_but_not_within_distance_limit],
            key=lambda i: i["DISTANCE"],
            reverse=True,
        ),
    )

    stat_msg2 = "\nResults\n-------\n" + "".join(
        f"{key}: {value}\n" for key, value in STATS.items()
    )

    print(stat_msg2)
    logging.info(stat_msg2)
    print(
        f"Log file: {log_filename}\nosm_refs_missing_jore_match.csv\nshelter_conflicts.csv\nmatched_stops_exceeding_max_distance_limit.csv"
    )

    try:
        etree.write(args.output, encoding="utf-8")
        print(f"\nSaved {args.output} with updated tags.")
    except Exception as e:
        print(f"\nError writing file {args.output}: {e}")
        logging.error(f"Error writing file {args.ouput}: {e}")


if __name__ == "__main__":
    main()
