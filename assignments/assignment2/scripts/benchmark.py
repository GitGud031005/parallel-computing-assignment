"""Run an immutable experiment matrix, retaining every sample and independently checking route quality."""

import argparse, hashlib, itertools, json, random, shutil, subprocess, time
from pathlib import Path
from common import A2, kernel_digest, pipeline_digest, environment, executable, sha256
from oracle import read_graph, frontier, check_paths


def configurations(matrix, queries):
    cases = []
    for q, h, o, e in itertools.product(
        queries, matrix["heuristics"], matrix["objectives"], ["sequential", "coarse", "fine"]
    ):
        for p in ([1] if e == "sequential" else matrix["threads"]):
            cases.append(
                {
                    "suite": "routes",
                    "query": q,
                    "heuristic": h,
                    "objective": o,
                    "engine": e,
                    "threads": p,
                    "dynamic_period": matrix["dynamic_period"],
                    "max_labels": matrix["max_labels"],
                }
            )
    for kind, p, mix, r in itertools.product(
        ["coarse", "fine"], matrix["threads"], matrix["set_mixes"], matrix["set_key_ranges"]
    ):
        cases.append(
            {
                "suite": "sets",
                "implementation": kind,
                "threads": p,
                "mix": mix,
                "key_range": r,
                "operations": matrix["set_operations"],
                "seed": matrix["seed"],
            }
        )
    return [{"id": f"c{i:04}", **c} for i, c in enumerate(cases)]


def command(case, bins, graph):
    if case["suite"] == "routes":
        q = case["query"]
        return [
            str(executable(bins, "a2_route")),
            "--graph",
            str(graph),
            "--source",
            str(q["source"]),
            "--target",
            str(q["target"]),
            "--engine",
            case["engine"],
            "--threads",
            str(case["threads"]),
            "--objective",
            case["objective"],
            "--heuristic",
            case["heuristic"],
            "--dynamic-period",
            str(case["dynamic_period"]),
            "--max-labels",
            str(case["max_labels"]),
        ]
    args = [str(executable(bins, "a2_bench_set"))]
    for k in ["implementation", "threads", "mix", "key_range", "operations", "seed"]:
        args += ["--" + k.replace("_", "-"), str(case[k])]
    return args


def validate_sample(case, sample, edges, oracle, digest):
    if (
        sample["source_sha256"] != digest
        or sample["build_type"] != "Release"
        or sample["sanitizer"] != "none"
    ):
        raise ValueError("source/build mismatch")
    if sample["suite"] != case["suite"] or sample["threads"] != case["threads"]:
        raise ValueError("configuration mismatch")
    if case["suite"] == "routes":
        q = case["query"]
        for k in ["engine", "heuristic", "objective", "dynamic_period", "max_labels"]:
            if sample[k] != case[k]:
                raise ValueError("route parameter mismatch")
        if sample["source"] != q["source"] or sample["target"] != q["target"]:
            raise ValueError("endpoint mismatch")
        check_paths(
            edges,
            sample["paths"],
            q["source"],
            q["target"],
            case["objective"],
            oracle[f"{q['name']}:{case['objective']}"],
        )
        for k in ["query_elapsed_ns", "end_to_end_ns", "preprocess_elapsed_ns"]:
            if sample[k] <= 0:
                raise ValueError("nonpositive timing")
    else:
        for k in ["implementation", "operations", "mix", "key_range", "seed"]:
            if sample[k] != case[k]:
                raise ValueError("set parameter mismatch")
        if (
            sample["reads"] + sample["inserts"] + sample["erases"] != case["operations"]
            or not 0 <= sample["final_size"] <= case["key_range"]
            or not 0 <= sample["successful_operations"] <= case["operations"]
            or sample["program_elapsed_ns"] <= 0
        ):
            raise ValueError("set output invariant")


def run(args):
    if args.output.exists():
        raise ValueError("run output must be new")
    matrix = json.loads(args.matrix.read_text())
    queries = json.loads(args.queries.read_text())[: matrix["query_count"]]
    if not queries or len({q["name"] for q in queries}) != len(queries):
        raise ValueError("queries missing/duplicate")
    cases = configurations(matrix, queries)
    digest = kernel_digest()
    nodes, edges = read_graph(args.graph)
    oracle = {}
    for q in queries:
        for objective in matrix["objectives"]:
            key = f"{q['name']}:{objective}"
            oracle[key] = frontier(edges, q["source"], q["target"], objective)
            print("oracle", key, "solutions", len(oracle[key]), flush=True)
    # Inspect real executable identity before any timed sample.
    probe = json.loads(
        subprocess.check_output(
            command(cases[0], args.bin_dir, args.graph),
            text=True,
            timeout=matrix["timeout_seconds"],
        )
    )
    if (
        probe["source_sha256"] != digest
        or probe["build_type"] != "Release"
        or probe["sanitizer"] != "none"
    ):
        raise ValueError("rebuild Release binaries for current source")
    cache_path = next(
        (
            p / "CMakeCache.txt"
            for p in args.bin_dir.resolve().parents
            if (p / "CMakeCache.txt").exists()
        ),
        None,
    )
    cache = cache_path.read_text() if cache_path else ""
    if any(
        "-flto" in line or "/GL" in line
        for line in cache.splitlines()
        if line.startswith("CMAKE_CXX_FLAGS")
    ):
        raise ValueError("LTO not allowed in reference protocol")
    args.output.mkdir(parents=True)
    shutil.copyfile(args.graph, args.output / "network.road")
    if args.graph.with_name("metadata.json").exists():
        shutil.copyfile(args.graph.with_name("metadata.json"), args.output / "road-metadata.json")
    manifest = {
        "schema": 1,
        "platform_id": args.platform_id,
        "revision": args.revision,
        "source_sha256": digest,
        "pipeline_sha256": pipeline_digest(),
        "graph_sha256": sha256(args.graph),
        "matrix": matrix,
        "cases": cases,
        "oracle": oracle,
        "environment": environment(),
        "binary_sha256": {
            n: sha256(executable(args.bin_dir, n)) for n in ["a2_route", "a2_bench_set"]
        },
        "build_flags": cache,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    failed = 0
    count = 0
    randomizer = random.Random(matrix["seed"])
    with (args.output / "raw.jsonl").open("w") as raw:
        for repetition in range(-matrix["warmups"], matrix["repetitions"]):
            order = list(cases)
            randomizer.shuffle(order)
            for case in order:
                row = {
                    "case_id": case["id"],
                    "repetition": repetition,
                    "warmup": repetition < 0,
                    "status": "ok",
                }
                begin = time.perf_counter_ns()
                try:
                    proc = subprocess.run(
                        command(case, args.bin_dir, args.graph),
                        capture_output=True,
                        text=True,
                        timeout=matrix["timeout_seconds"],
                    )
                    row["process_elapsed_ns"] = time.perf_counter_ns() - begin
                    if proc.returncode:
                        raise RuntimeError(proc.stderr)
                    row["sample"] = json.loads(proc.stdout)
                    validate_sample(case, row["sample"], edges, oracle, digest)
                except Exception as error:
                    row.update(status="failed", error=str(error))
                    failed += 1
                raw.write(json.dumps(row) + "\n")
                raw.flush()
                count += 1
                if count % 100 == 0:
                    print(count, "samples; failures", failed, flush=True)
    completion = {
        "samples": count,
        "cases": len(cases),
        "failed": failed,
        "all_complete": count == len(cases) * (matrix["warmups"] + matrix["repetitions"]),
    }
    (args.output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion), flush=True)
    return int(failed != 0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["bin-dir", "graph", "queries", "matrix", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--platform-id", required=True)
    p.add_argument("--revision", default="working-tree")
    raise SystemExit(run(p.parse_args()))
