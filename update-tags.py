import xml.etree.ElementTree as et
import csv
import argparse


class Stop:
    def __init__(self, id, stop_id, name, name_sv, shelter):
        self.id = id
        self.stop_id = stop_id
        self.name = name
        self.name_sv = name_sv

        if shelter in ("04", "08", ""):
            self.shelter = "no"
        else:
            self.shelter = "yes"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Finds public transport stop ref-tags from jOSM-file (.osm). Prefixes ref-tag values with letter 'H'. Adds 'shelter=yes'-tag. Adds name, name:fi and name:sv-tags"
    )
    parser.add_argument(
        "input_osm", metavar="input.osm", help="Source .OSM-file containing ref-tags"
    )
    parser.add_argument(
        "input_stops", metavar="input.csv", help="Jore data in CSV-format"
    )
    parser.add_argument(
        "output",
        metavar="output.osm",
        help="The ouput .OSM-file with transformed ref-tags, name and shelter info.",
    )
    return parser.parse_args()


def read_stop_data(input_file):
    """Reads stop data in CSV format and returns a list of Stop-objects with the relevant data for import."""
    stops = []
    with open(input_file, newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            new_stop = Stop(
                row["soltunnus"],
                row["sollistunn"],
                row["pysnimi"],
                row["pysnimir"],
                row["pysakkityy"],
            )
            stops.append(new_stop)
    return stops


def get_osm_tags(xml_element):
    """Returns tags as a dict for OSM XML element"""
    return {
        element.get("k"): element.get("v") for element in xml_element.findall("tag")
    }


def add_prefix_h_to_ref(elem):
    """Adds modify action to element and adds prefix 'H' to the value of tag 'ref'"""
    tags = get_osm_tags(elem)
    new_ref_value = "H" + tags.get("ref")

    elem.set("action", "modify")
    for tag in elem.findall("tag"):
        if tag.attrib["k"] == "ref":
            tag.set("v", new_ref_value)


def add_shelter(elem, value):
    """Adds modify action to element and adds 'shelter'-tag with param value (should be 'yes' or 'no')."""
    elem.set("action", "modify")

    shelter = {"k": "shelter", "v": value}
    new_tag = et.Element("tag", shelter)

    elem.append(new_tag)


def add_stop_name(elem):
    """Adds modify action to element and adds stop name in Finnish and/or Swedish with
    tags 'name:fi' and 'name:sv' if tag is missing."""

    elem.set("action", "modify")

    tags = get_osm_tags(elem).keys()

    if "name" not in tags or "name:fi" not in tags:
        name_fi = {"k": "name:fi", "v": "NEW_FINNISH_NAME_FOR_STOP"}
        new_name_fi_tag = et.Element("tag", name_fi)
        elem.append(new_name_fi_tag)

    if "name:sv" not in tags:
        name_sv = {"k": "name:sv", "v": "NEW_SWEDISH_NAME_FOR_STOP"}
        new_name_sv_tag = et.Element("tag", name_sv)
        elem.append(new_name_sv_tag)


def main():
    args = parse_args()

    etree = et.parse(args.input_osm)
    stops = read_stop_data(args.input_stops)

    prefixed = 0
    sheltered = 0
    named = 0

    for stop in stops:
        print(stop)

    for elem in etree.getroot():
        tags = get_osm_tags(elem)

        if "ref" in tags.keys():
            for stop in stops:
                if tags["ref"] == stop.stop_id:
                    add_prefix_h_to_ref(elem)
                    prefixed += 1
        if "shelter" not in tags:
            add_shelter(elem, "yes")
            sheltered += 1
        if "name:fi" not in tags or "name:sv" not in tags:
            add_stop_name(elem)
            named += 1

    etree.write(args.output, encoding="utf-8")
    print(f"prefixed: {prefixed}, sheltered: {sheltered}, named: {named}")


if __name__ == "__main__":
    main()
