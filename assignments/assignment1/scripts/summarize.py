"""Validate raw samples against the manifest and derive median/IQR statistics."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
from collections import defaultdict

GROUP = ["platform_id", "revision", "source_sha256", "suite", "implementation", "mode", "threads",
         "iterations_per_thread", "total_operations", "episodes", "prime_n", "outside_work"]


def quantile(values, percentile):
    values = sorted(values)
    index = (len(values) - 1) * percentile
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def prime(n):
    return n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))


def summarize(run_dir, output):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    expected = {case["config_id"]: case for case in manifest["resolved_cases"]}
    rows = list(csv.DictReader((run_dir / "raw.csv").open()))
    groups, seen, counts = defaultdict(list), set(), defaultdict(int)
    failed = []
    for row in rows:
        key = (row["config_id"], int(row["repetition"]))
        if key in seen: raise ValueError("duplicate sample")
        seen.add(key); counts[row["config_id"]] += 1
        case = expected[row["config_id"]]
        if row["run_id"] != manifest["run_id"] or row["platform_id"] != manifest["platform_id"]:
            raise ValueError("mixed run/platform")
        if row["status"] != "ok":
            failed.append(row)
            continue
        if row["source_sha256"] != manifest["source_sha256"]: raise ValueError("source fingerprint mismatch")
        for field in ["suite", "implementation", "threads", "mode", *case.keys()]:
            if field in ["config_id"] or field not in case: continue
            if field in row and row[field] != str(case[field]): raise ValueError(f"wrong configuration {field}")
        program, worker = int(row["program_elapsed_ns"]), int(row["worker_elapsed_ns"])
        if not 0 < worker <= program: raise ValueError("invalid time")
        if row["suite"] == "locks":
            total = int(case["total_operations"]) if case["mode"] == "fixed_total" else int(case["iterations_per_thread"]) * int(case["threads"])
            calls = total * (int(case["outside_work"]) + 1)
            checksum = calls if prime(int(case["prime_n"])) else 0
            if int(row["total_operations"]) != total or int(row["checksum"]) != checksum:
                raise ValueError("lock workload count/checksum mismatch")
        elif row["suite"] == "counters":
            total = int(case["total_operations"])
            if int(row["final_value"]) != total or int(row["checksum"]) != (total * (total - 1) // 2) % (1 << 64):
                raise ValueError("counter count/checksum mismatch")
        elif row["suite"] == "barriers":
            if int(row["episodes"]) != int(case["episodes"]): raise ValueError("episode mismatch")
        else: raise ValueError("unknown suite")
        if int(row["is_warmup"]) != int(int(row["repetition"]) < 0): raise ValueError("warmup mismatch")
        if not int(row["is_warmup"]): groups[tuple(row[field] for field in GROUP)].append(row)
    per_case = manifest["matrix"]["warmup_repetitions"] + manifest["matrix"]["measured_repetitions"]
    if set(counts) != set(expected) or any(n != per_case for n in counts.values()): raise ValueError("incomplete raw run")
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    for key, samples in sorted(groups.items()):
        entry = dict(zip(GROUP, key))
        entry["samples"] = len(samples)
        entry["complete"] = int(len(samples) == manifest["matrix"]["measured_repetitions"])
        for name, field in [("program_ms", "program_elapsed_ns"), ("worker_ms", "worker_elapsed_ns")]:
            values = [int(r[field]) / 1e6 for r in samples]
            for label, fraction in [("q1", .25), ("median", .5), ("q3", .75)]:
                entry[f"{label}_{name}"] = quantile(values, fraction)
        throughput = [int(r["episodes"]) * 1e9 / int(r["worker_elapsed_ns"]) if r["suite"] == "barriers"
                      else int(r["total_operations"]) * 1e9 / int(r["program_elapsed_ns"]) for r in samples]
        for label, fraction in [("q1", .25), ("median", .5), ("q3", .75)]:
            entry[f"{label}_throughput"] = quantile(throughput, fraction)
        entry["throughput_unit"] = "episodes/s" if entry["suite"] == "barriers" else "operations/s"
        entry["speedup"] = ""
        summary.append(entry)
    identity = lambda r: tuple(r[k] for k in GROUP if k != "threads")
    serial = {identity(row): row for row in summary if row["threads"] == "1" and row["mode"] == "fixed_total"}
    for row in summary:
        if row["mode"] == "fixed_total" and identity(row) in serial:
            row["speedup"] = serial[identity(row)]["median_program_ms"] / row["median_program_ms"]
    if not summary: raise ValueError("no valid measured samples")
    with (output / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    result = {"run_id": manifest["run_id"], "raw_samples": len(rows), "configurations": len(expected),
              "summary_groups": len(summary), "failed_samples": len(failed),
              "failed_measured_samples": sum(1 for row in failed if int(row["repetition"]) >= 0),
              "failed_warmups": [{k: row[k] for k in ["config_id", "repetition", "implementation", "threads", "mode",
                                                       "outside_work", "status", "error"]}
                                 for row in failed if int(row["repetition"]) < 0],
              "all_groups_complete": all(row["complete"] for row in summary),
              "source_sha256": manifest["source_sha256"]}
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    if failed:
        with (output / "failed_samples.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(failed)
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.run_dir, args.output)
    # A failed warmup is reported, but only measured samples decide whether the statistics are usable.
    if result["failed_measured_samples"] or not result["all_groups_complete"]: raise SystemExit(1)
