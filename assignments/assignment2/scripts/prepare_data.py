"""Convert a real OSM road extract to deterministic directed integer PCROAD1 format."""

import argparse
import bz2
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

OSM_BLOB = "8cf84a8abccdf84f110ecf315654c68c77f9b496"
OSM_URL = (
    "https://raw.githubusercontent.com/gboeing/osmnx/main/tests/input_data/West-Oakland.osm.bz2"
)
SPEEDS = {
    "motorway": 90,
    "trunk": 70,
    "primary": 50,
    "secondary": 40,
    "tertiary": 35,
    "unclassified": 30,
    "residential": 25,
    "living_street": 10,
    "service": 15,
    "motorway_link": 40,
    "trunk_link": 35,
    "primary_link": 30,
    "secondary_link": 25,
    "tertiary_link": 25,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distance_mm(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    x = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return max(1, math.ceil(6371009 * 2000 * math.asin(min(1, math.sqrt(max(0, x))))))


def convert(xml_path, output, provenance):
    output = Path(output)
    if output.exists():
        raise ValueError("output directory must be new")
    raw = Path(xml_path).read_bytes()
    root = ET.fromstring(bz2.decompress(raw) if raw[:3] == b"BZh" else raw)
    if root.find("remark") is not None:
        raise ValueError(root.findtext("remark"))
    nodes = {
        n.attrib["id"]: (float(n.attrib["lat"]), float(n.attrib["lon"]))
        for n in root.findall("node")
    }
    links = []
    skipped = 0
    for way in root.findall("way"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
        road = tags.get("highway")
        if road not in SPEEDS or any(
            tags.get(k) in {"no", "private"} for k in ["access", "vehicle", "motor_vehicle"]
        ):
            continue
        refs = [r.attrib["ref"] for r in way.findall("nd")]
        one = tags.get(
            "oneway", "yes" if tags.get("junction") == "roundabout" or road == "motorway" else "no"
        ).lower()
        if one == "-1":
            refs.reverse()
        for u, v in zip(refs, refs[1:]):
            if u not in nodes or v not in nodes:
                skipped += 1
                continue
            d = distance_mm(nodes[u], nodes[v])
            t = max(1, math.ceil(d * 3.6 / SPEEDS[road]))
            links.append((u, v, d, t))
            if one not in {"yes", "true", "1", "-1"}:
                links.append((v, u, d, t))
    used = sorted({x for e in links for x in e[:2]}, key=int)
    if not used:
        raise ValueError("no modeled motor-road segments")
    ids = {x: i for i, x in enumerate(used)}
    output.mkdir(parents=True)
    path = output / "network.road"
    with path.open("w") as f:
        f.write(f"PCROAD1\n{len(used)} {len(links)}\n")
        for x in used:
            f.write(f"{x} {nodes[x][0]:.9f} {nodes[x][1]:.9f}\n")
        for u, v, d, t in links:
            f.write(f"{ids[u]} {ids[v]} {d} {t}\n")
    metadata = {
        "name": provenance,
        "downloaded_or_converted_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "graph_sha256": sha256(path),
        "osm_base": (
            root.find("meta").attrib.get("osm_base") if root.find("meta") is not None else None
        ),
        "vertices": len(used),
        "directed_edges": len(links),
        "skipped_missing_segments": skipped,
        "speeds_kmh": SPEEDS,
        "cost_model": "Spherical segment length rounded up to mm; static road-class speed estimate rounded up to ms. Not live traffic or observed travel times; no turn restrictions.",
        "attribution": "© OpenStreetMap contributors",
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "copyright_url": "https://www.openstreetmap.org/copyright",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    adjacency = [[] for _ in used]
    reverse = [[] for _ in used]
    for u, v, *_ in links:
        adjacency[ids[u]].append(ids[v])
        reverse[ids[v]].append(ids[u])
    # Iterative Kosaraju solely chooses queries in the largest strongly connected component.
    seen = set()
    order = []
    for s in range(len(used)):
        if s in seen:
            continue
        stack = [(s, False)]
        while stack:
            u, exit = stack.pop()
            if exit:
                order.append(u)
                continue
            if u in seen:
                continue
            seen.add(u)
            stack.append((u, True))
            stack.extend((v, False) for v in adjacency[u] if v not in seen)
    seen = set()
    largest = []
    for s in reversed(order):
        if s in seen:
            continue
        comp = []
        stack = [s]
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in reverse[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if len(comp) > len(largest):
            largest = comp
    if len(largest) < 2:
        raise ValueError("no nontrivial strongly connected road component")
    west = min(largest, key=lambda i: (nodes[used[i]][1], nodes[used[i]][0], i))
    east = max(largest, key=lambda i: (nodes[used[i]][1], nodes[used[i]][0], i))
    south = min(largest, key=lambda i: (nodes[used[i]][0], nodes[used[i]][1], i))
    north = max(largest, key=lambda i: (nodes[used[i]][0], nodes[used[i]][1], i))
    queries = [
        {"name": "west-east", "source": west, "target": east},
        {"name": "south-north", "source": south, "target": north},
        {"name": "east-west", "source": east, "target": west},
    ]
    (output / "queries.json").write_text(json.dumps(queries, indent=2) + "\n")
    print(
        json.dumps(
            {
                "graph": str(path.resolve()),
                "vertices": len(used),
                "edges": len(links),
                "largest_scc": len(largest),
                "queries": queries,
            }
        )
    )
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--osm-xml", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--name", default="West Oakland OSM test extract (OSMnx)")
    a = p.parse_args()
    if a.osm_xml is None:
        raw = urllib.request.urlopen(OSM_URL, timeout=60).read()
        if hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != OSM_BLOB:
            raise ValueError("pinned OSM fixture changed; review source before use")
        source = a.output.parent / "West-Oakland.osm.bz2"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(raw)
    else:
        source = a.osm_xml
    convert(source, a.output, a.name)


if __name__ == "__main__":
    main()
