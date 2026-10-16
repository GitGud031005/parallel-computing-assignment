"""Download one bounded public Overpass OSM road extract for local conversion."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def download(bbox, output):
    south, west, north, east = bbox
    if (
        not (-90 <= south < north <= 90 and -180 <= west < east <= 180)
        or (north - south) * (east - west) > 0.01
    ):
        raise ValueError("use a valid small bbox (area <= 0.01 square degrees)")
    if output.exists():
        raise ValueError("output must be new")
    query = f'[out:xml][timeout:60];way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]({south},{west},{north},{east});(._;>;);out body;'
    url = "https://overpass-api.de/api/interpreter"
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "ParallelComputingAssignment2/1.0 educational network study"},
    )
    raw = urllib.request.urlopen(request, timeout=90).read()
    root = ET.fromstring(raw)
    if root.find("remark") is not None or not root.findall("way"):
        raise ValueError("Overpass returned no valid road ways")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    output.with_suffix(output.suffix + ".json").write_text(
        json.dumps(
            {
                "url": url,
                "query": query,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "bbox": bbox,
                "attribution": "© OpenStreetMap contributors",
                "license": "ODbL-1.0",
                "copyright": "https://www.openstreetmap.org/copyright",
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "bytes": len(raw),
                "nodes": len(root.findall("node")),
                "ways": len(root.findall("way")),
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        default=[10.770, 106.685, 10.785, 106.705],
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
    )
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    download(a.bbox, a.output)
