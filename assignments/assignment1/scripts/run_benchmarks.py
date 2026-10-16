"""Run a concrete JSON experiment matrix serially; retain every raw sample/error."""
import argparse
import csv
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
from collect_environment import collect, executable, sha256, read

FIELDS = ["run_id", "platform_id", "revision", "timestamp_utc", "config_id", "repetition", "is_warmup",
          "suite", "implementation", "mode", "threads", "iterations_per_thread", "total_operations", "episodes",
          "prime_n", "outside_work", "program_elapsed_ns", "worker_elapsed_ns", "checksum", "final_value",
          "backoff_policy", "backoff_initial", "backoff_max", "source_sha256", "build_type", "sanitizer", "status", "error"]
FLAG_NAMES = {"iterations_per_thread": "iterations-per-thread", "total_operations": "total-operations",
              "prime_n": "prime-n", "outside_work": "outside-work", "episodes": "episodes"}


def expand(matrix):
    cases = []
    for experiment in matrix["experiments"]:
        grid = experiment["parameters"]
        names = list(grid)
        for values in itertools.product(*(grid[name] for name in names)):
            case = dict(zip(names, values))
            case["suite"] = experiment["suite"]
            case["config_id"] = f"{experiment['name']}-{len(cases):04d}"
            if not isinstance(case["threads"], int) or not 1 <= case["threads"] <= 1024:
                raise ValueError("concrete thread counts in [1,1024] are required")
            cases.append(case)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="NEW run directory; existing paths are refused")
    parser.add_argument("--platform-id", required=True)
    parser.add_argument("--revision", default="unrecorded")
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    cases = expand(matrix)
    metadata = collect(args.bin_dir, args.platform_id, args.revision)
    capabilities = metadata["capabilities"]
    if capabilities["source_sha256"] != metadata["kernel_source_sha256"]:
        raise ValueError("binary/source fingerprint mismatch: rebuild ALL targets")
    if capabilities["build_type"] not in ["Release", "RelWithDebInfo"] or capabilities["sanitizer"] != "none":
        raise ValueError("performance requires a Release/RelWithDebInfo build without sanitizers")
    if "-flto" in " ".join(metadata["build_cache"].values()):
        raise ValueError("LTO is not permitted in the reference workload protocol")
    for experiment in matrix["experiments"]:
        if experiment["suite"] not in ["locks", "barriers", "counters"]:
            raise ValueError("unknown suite")
    warmups, repetitions = matrix["warmup_repetitions"], matrix["measured_repetitions"]
    if warmups < 0 or repetitions < 1:
        raise ValueError("invalid repetition counts")
    args.output.mkdir(parents=True, exist_ok=False)
    run_id = args.output.name
    (args.output / "environment.json").write_text(json.dumps(metadata, indent=2) + "\n")
    manifest = {"run_id": run_id, "matrix": matrix, "resolved_cases": cases,
                "matrix_sha256": sha256(args.matrix), "runner_sha256": sha256(__file__),
                "platform_id": args.platform_id, "revision": args.revision,
                "source_sha256": capabilities["source_sha256"],
                "timing_note": "program=spawn to join; worker=max(end)-min(start); allocations precede timers"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    rng = random.Random(matrix.get("order_seed", 20261016))
    failures = 0
    done = 0
    total = len(cases) * (warmups + repetitions)
    with (args.output / "raw.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        # Warmup rounds precede measurements; configurations are shuffled in each round.
        for round_id in range(-warmups, repetitions):
            order = list(cases)
            rng.shuffle(order)
            for case in order:
                row = {k: v for k, v in case.items() if k in FIELDS}
                row.update(run_id=run_id, platform_id=args.platform_id, revision=args.revision,
                           timestamp_utc=datetime.now(timezone.utc).isoformat(),
                           repetition=round_id, is_warmup=int(round_id < 0), status="ok", error="")
                argv = [str(executable(args.bin_dir.resolve(), f"bench_{case['suite']}"))]
                for key, value in case.items():
                    if key in ["suite", "config_id"]: continue
                    argv += ["--" + FLAG_NAMES.get(key, key.replace("_", "-")), str(value)]
                try:
                    result = subprocess.run(argv, capture_output=True, text=True, timeout=matrix.get("timeout_seconds", 60))
                    if result.returncode:
                        raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
                    sample = json.loads(result.stdout)
                    if sample["source_sha256"] != capabilities["source_sha256"]:
                        raise ValueError("benchmark binary differs from environment fingerprint")
                    if sample["sanitizer"] != "none" or sample["build_type"] != capabilities["build_type"]:
                        raise ValueError("benchmark build mode mismatch")
                    if not 0 < sample["worker_elapsed_ns"] <= sample["program_elapsed_ns"]:
                        raise ValueError("invalid timing interval")
                    for key in ["suite", "implementation", "threads"]:
                        if sample[key] != case[key]: raise ValueError(f"configuration mismatch: {key}")
                    row.update(sample)
                except subprocess.TimeoutExpired:
                    row.update(status="timeout", error="process exceeded configured timeout")
                    failures += 1
                except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
                    row.update(status="failed", error=str(error))
                    failures += 1
                writer.writerow(row)
                stream.flush()
                done += 1
                if done % 50 == 0 or done == total:
                    print(f"{done}/{total} samples; failures={failures}", flush=True)
    end = {"samples": done, "failures": failures, "cpu_stat_after": read("/sys/fs/cgroup/cpu.stat")}
    (args.output / "completion.json").write_text(json.dumps(end, indent=2) + "\n")
    print(json.dumps(end), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
