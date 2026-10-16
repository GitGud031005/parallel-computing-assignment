import itertools, json, subprocess, sys, tempfile
from pathlib import Path

bin_dir, fixture = map(Path, sys.argv[1:])
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from oracle import read_graph, frontier, check_paths

vertices, edges = read_graph(fixture)


def run(name, args, valid=True):
    r = subprocess.run(
        [str(bin_dir / name), *map(str, args)], capture_output=True, text=True, timeout=60
    )
    assert (r.returncode == 0) == valid, (name, args, r.stdout, r.stderr)
    return json.loads(r.stdout) if valid else None


for engine, heuristic, objective in itertools.product(
    ["sequential", "coarse", "fine"],
    ["zero", "landmark", "dynamic", "uncertain"],
    ["distance", "time", "pareto"],
):
    args = [
        "--graph",
        fixture,
        "--engine",
        engine,
        "--heuristic",
        heuristic,
        "--objective",
        objective,
        "--threads",
        1 if engine == "sequential" else 3,
        "--source",
        0,
        "--target",
        3,
        "--dynamic-period",
        1,
    ]
    result = run("a2_route", args)
    check_paths(edges, result["paths"], 0, 3, objective, frontier(edges, 0, 3, objective))
for options in [
    ["--source-osm-id", 100, "--target-osm-id", 103],
    [
        "--source-lat",
        10.770,
        "--source-lon",
        106.685,
        "--target-lat",
        10.771,
        "--target-lon",
        106.686,
    ],
]:
    r = run("a2_route", ["--graph", fixture, *options])
    assert r["source"] == 0 and r["target"] == 3
for args in [
    ["--threads", 0],
    ["--threads", -1],
    ["--threads", 1025],
    ["--engine", "bad"],
    ["--objective", "bad"],
    ["--heuristic", "bad"],
    ["--source", 99],
    ["--source-osm-id", 999],
    ["--source-lat", 10],
    ["--source-lat", "nan", "--source-lon", 10],
    ["--source", 0, "--source-osm-id", 100],
    ["--max-labels", 1],
    ["--threads", 2],
    ["--threads", 1, "--threads", 1],
    ["--unknown", 1],
    ["--threads"],
]:
    run("a2_route", ["--graph", fixture, *args], False)
for kind in ["coarse", "fine"]:
    r = run(
        "a2_bench_set",
        ["--implementation", kind, "--threads", 8, "--operations", 3, "--key-range", 1],
    )
    assert r["reads"] + r["inserts"] + r["erases"] == 3
for args in [
    ["--operations", 0],
    ["--key-range", 0],
    ["--seed", 0],
    ["--mix", "bad"],
    ["--implementation", "bad"],
    ["--threads", 1025],
]:
    run("a2_bench_set", args, False)
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "bad.road"
    for content in [
        "bad",
        "PCROAD1\n-1 0",
        "PCROAD1\n1 0\n1 nan 0",
        "PCROAD1\n1 1\n1 0 0\n0 0 -1 1",
        "PCROAD1\n1 0\n1 0 0\nextra",
    ]:
        p.write_text(content)
        run("a2_route", ["--graph", p], False)
print("PASS CLI, all combinations, GPS/OSM endpoints, invalid inputs, partition and path replay")
