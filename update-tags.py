#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command line script for importing HSL public transportation (JORE) stop data to OpenStreetMap.

Usage: python update-tags.py -h

Requires: Python 3.7 or later
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

STATS = {
    "matched": 0,
    "prefixed": 0,
    "sheltered_yes": 0,
    "sheltered_no": 0,
    "named": 0,
    "named_fi": 0,
    "named_sv": 0,
}
OSM_URL = "https://www.openstreetmap.org"


@dataclass
class Stop:
    """Dataclass object to represent JORE stop with import relevant attributes"""

    id: str
    stop_id: str
    name: str
    name_sv: str
    shelter_param: InitVar[str]
    municipality: str = None
    shelter: str = "yes"  # Default is that the stop is sheltered

    def __post_init__(self, shelter_param):
        """Get values for shelter and municipality
        """
        # JORE stop type values for non-sheltered stops converted to bo
        # 04 stands for a pole and 08 for stop position. 99 unknown.
        if shelter_param in ("04", "08"):
            self.shelter = "no"
        elif shelter_param == "99":
            self.shelter = "unknown"

        # Is the stop in Helsinki
        if self.stop_id[:1] == "H":
            self.municipality = "Helsinki"


def parse_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
        Finds HSL public transport stops from jOSM-file (.osm) and modifies it's OSM-tags
        with HSL (JORE) stop data (.csv) using 'ref'-tag value as an identifier.

        Following transformations are made for the output jOSM-file:
         - 'ref'-tag values of stops in Helsinki are prefixed with letter 'H'.
         - Adds 'shelter'-tag with value 'yes' or 'no'.
         - Adds 'name', 'name:fi', and 'name:sv'-tag if missing."""
        ),
    )
    parser.add_argument("input_osm", metavar="input.osm", help="Source .OSM-file")
    parser.add_argument(
        "input_stops", metavar="input.csv", help="HSL stop data in CSV-format"
    )
    parser.add_argument(
        "output",
        metavar="output.osm",
        help="The ouput .OSM-file with transformed ref-tags, name and shelter info.",
    )
    parser.add_argument(
        "-s",
        "--stats",
        help="Prints out more verbose stats about script results",
        action="store_true",
    )
    return parser.parse_args()


def read_stop_data(input_file):
    """Read stop data in CSV format and retur n a list of Stop-objects with the relevant data for import."""
    stops = []
    try:
        with open(input_file, newline="", encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            for row in reader:
                new_stop = Stop(
                    row["SOLMUTUNNU"],
                    row["LYHYTTUNNU"],
                    row["NIMI1"],
                    row["NAMN1"],
                    row["PYSAKKITYY"],
                )
                stops.append(new_stop)

    except Exception as e:
        logging.error(f"Error reading JORE stop data {input_file}:", exc_info=True)

    return stops


def read_stop_data_geojson(input_file):
    """Read stop data in GeoJSON format and return a list of Stop-objects with the relevant data for import."""
    stops = []
    try:
        with open(input_file, newline="", encoding="utf8") as jsonfile:
            data = json.load(jsonfile)
            for feature in data["features"]:
                jore_stop = feature["properties"]
                new_stop = Stop(
                    jore_stop["SOLMUTUNNU"],
                    jore_stop["LYHYTTUNNU"],
                    jore_stop["NIMI1"],
                    jore_stop["NAMN1"],
                    jore_stop["PYSAKKITYY"],
                )
                stops.append(new_stop)
    except Exception as e:
        logging.error(f"Error reading JORE stop data {input_file}:", exc_info=True)

    return stops


def get_osm_tags(xml_element):
    """Return tags as a dict for OSM XML element."""
    return {
        element.get("k"): element.get("v") for element in xml_element.findall("tag")
    }


def update_tag(elem, key, value):
    """Add modify action to element. Updates value of chosen key of the 'tag'-element."""
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


def main():
    log_filename = "update-tags-log-{:%H-%M-%S}.log".format(datetime.datetime.now())
    logging.basicConfig(
        filename=log_filename, filemode="w", level=logging.INFO, format="%(message)s",
    )

    args = parse_args()
    print("Executing...")
    etree = et.parse(args.input_osm)

    stops = read_stop_data(args.input_stops)

    all_jore_ref = {x.stop_id: x for x in stops}
    all_osm_refs = []
    osm_ref_missing_jore_match = []

    for elem in etree.getroot():

        osm_tags = get_osm_tags(elem)
        osm_ref = osm_tags.get("ref")

        if osm_ref:
            osm_id = elem.get("id")
            all_osm_refs.append(osm_ref)

            jore_stop = all_jore_ref.get(osm_ref) or all_jore_ref.get("H" + osm_ref)
            if jore_stop:
                # In Helsinki the OSM ref-might already have the H-prefix.
                if osm_ref == jore_stop.stop_id or (
                    jore_stop.municipality == "Helsinki"
                    and osm_ref == jore_stop.stop_id[1:]
                ):
                    STATS["matched"] += 1
                    logging.info(
                        f"Matched ref {jore_stop.stop_id} between OSM-id: {OSM_URL}/{elem.tag}/{osm_id} and JORE stop: {jore_stop.id}"
                    )

                    stoptype = osm_tags.get("highway") or osm_tags.get(
                        "public_transport"
                    )
                    if stoptype:
                        logging.info(f"   Stop type: {stoptype}")

                    if jore_stop.municipality == "Helsinki" and osm_ref[:1] != "H":
                        new_ref_value = "H" + osm_ref
                        update_tag(elem, "ref", new_ref_value)
                        STATS["prefixed"] += 1

                    if "shelter" not in osm_tags.keys():
                        if jore_stop.shelter == "yes":
                            create_tag(elem, "shelter", "yes")
                            STATS["sheltered_yes"] += 1
                        elif jore_stop.shelter == "no":
                            create_tag(elem, "shelter", "no")
                            STATS["sheltered_no"] += 1
                        elif jore_stop.shelter == "unknown":
                            logging.info(f"   No shelter info in data.")

                    any_name_tag_is_missing = any(
                        key not in osm_tags.keys()
                        for key in ["name", "name:fi", "name:sv"]
                    )
                    if any_name_tag_is_missing:
                        add_stop_name(elem, jore_stop)

                    # Update the tags in case the element tree got a new tag
                    osm_tags = get_osm_tags(elem)
            else:
                osm_ref_missing_jore_match.append(osm_ref)

    if args.stats:
        # Print stats if optional command line argument: -s
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
        osm_missing_freq = Counter((osm_ref_missing_jore_match))
        osm_missing_freq_sorted = {
            k: v
            for k, v in sorted(
                osm_missing_freq.items(), key=lambda item: item[1], reverse=True
            )
        }
        logging.info(
            "OSM stops 'ref'-tag values missing JORE match occurrence count (value  / count):"
        )
        logging.info(osm_missing_freq_sorted)

    stat_msg2 = "\nResults\n-------\n" + "".join(
        [f"{key}: {value}\n" for key, value in STATS.items()]
    )
    print(stat_msg2)
    logging.info(stat_msg2)
    print(f"Log file: {log_filename}")
    try:
        etree.write(args.output, encoding="utf-8")
        print(f"\nSaved {args.output} with updated tags.")
    except Exception as e:
        print(f"\nError writing file {args.output}: {e}")
        logging.error(f"Error writing file {args.ouput}: {e}")


if __name__ == "__main__":
    main()
