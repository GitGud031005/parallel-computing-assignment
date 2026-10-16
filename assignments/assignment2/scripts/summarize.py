"""Revalidate raw records, exclude warmups, and compute median/inclusive IQR and matched speedups."""

import argparse, csv, json, statistics
from pathlib import Path
from collections import defaultdict
from common import sha256
from oracle import read_graph
from benchmark import validate_sample


def quartiles(values):
    if len(values) == 1:
        return values[0], values[0]
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], q[2]


def summarize(run_dir, output):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    matrix = manifest["matrix"]
    if sha256(run_dir / "network.road") != manifest["graph_sha256"]:
        raise ValueError("graph SHA mismatch")
    _, edges = read_graph(run_dir / "network.road")
    cases = {c["id"]: c for c in manifest["cases"]}
    seen = set()
    groups = defaultdict(list)
    count = 0
    for line in (run_dir / "raw.jsonl").read_text().splitlines():
        row = json.loads(line)
        count += 1
        key = (row["case_id"], row["repetition"])
        if key in seen or row["case_id"] not in cases:
            raise ValueError("duplicate/unknown sample")
        seen.add(key)
        if row["repetition"] not in range(-matrix["warmups"], matrix["repetitions"]) or row[
            "warmup"
        ] != (row["repetition"] < 0):
            raise ValueError("repetition/warmup mismatch")
        if row["status"] != "ok":
            raise ValueError("failed samples retained; report blocked")
        validate_sample(
            cases[row["case_id"]],
            row["sample"],
            edges,
            manifest["oracle"],
            manifest["source_sha256"],
        )
        if not row["warmup"]:
            groups[row["case_id"]].append(row["sample"])
    expected = {(c, r) for c in cases for r in range(-matrix["warmups"], matrix["repetitions"])}
    if seen != expected:
        raise ValueError("missing samples")
    rows = []
    for cid, case in cases.items():
        samples = groups[cid]
        route = case["suite"] == "routes"
        field = "query_elapsed_ns" if route else "program_elapsed_ns"
        values = [s[field] / 1e6 for s in samples]
        q1, q3 = quartiles(values)
        r = {
            "case_id": cid,
            "suite": case["suite"],
            "query": case.get("query", {}).get("name", ""),
            "engine": case.get("engine", case.get("implementation")),
            "objective": case.get("objective", ""),
            "heuristic": case.get("heuristic", ""),
            "mix": case.get("mix", ""),
            "key_range": case.get("key_range", ""),
            "threads": case["threads"],
            "median_ms": statistics.median(values),
            "q1_ms": q1,
            "q3_ms": q3,
            "samples": len(values),
            "quality_exact": True,
            "solutions": len(samples[0]["paths"]) if route else "",
            "end_to_end_median_ms": (
                statistics.median(s["end_to_end_ns"] / 1e6 for s in samples) if route else ""
            ),
            "preprocess_median_ms": (
                statistics.median(s["preprocess_elapsed_ns"] / 1e6 for s in samples)
                if route
                else ""
            ),
            "speedup_vs_sequential": "",
            "speedup_vs_own_p1": "",
        }
        rows.append(r)
    for r in rows:
        match = [
            x
            for x in rows
            if all(
                x[k] == r[k]
                for k in ["suite", "query", "objective", "heuristic", "mix", "key_range"]
            )
            and x["threads"] == 1
        ]
        own = next((x for x in match if x["engine"] == r["engine"]), None)
        sequential = next((x for x in match if x["engine"] == "sequential"), None)
        if own:
            r["speedup_vs_own_p1"] = own["median_ms"] / r["median_ms"]
        if sequential:
            r["speedup_vs_sequential"] = sequential["median_ms"] / r["median_ms"]
    output.mkdir(parents=True, exist_ok=False)
    with (output / "summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    validation = {
        "source_sha256": manifest["source_sha256"],
        "graph_sha256": manifest["graph_sha256"],
        "raw_samples": count,
        "cases": len(cases),
        "measured_samples": sum(len(g) for g in groups.values()),
        "failures": 0,
        "complete": True,
        "quality_exact": True,
        "raw_sha256": sha256(run_dir / "raw.jsonl"),
    }
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation))
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    summarize(a.run_dir, a.output)
