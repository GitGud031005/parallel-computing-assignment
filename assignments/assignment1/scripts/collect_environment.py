"""Collect only reproducibility metadata; also shared by the benchmark runner."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

ASSIGNMENT = Path(__file__).resolve().parents[1]
ROOT = ASSIGNMENT.parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kernel_digest():
    paths = list(ASSIGNMENT.rglob("*.cpp")) + list(ASSIGNMENT.rglob("*.hpp"))
    paths += [ROOT / "CMakeLists.txt", ASSIGNMENT / "CMakeLists.txt"]
    catalog = "".join(f"{p.relative_to(ROOT).as_posix()}:{sha256(p)}\n" for p in sorted(paths))
    return hashlib.sha256(catalog.encode()).hexdigest()


def command(args):
    try:
        run = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return run.stdout.strip() if run.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def executable(directory, name):
    return Path(directory) / (name + (".exe" if os.name == "nt" else ""))


def collect(bin_dir, platform_id, revision="unrecorded"):
    bin_dir = Path(bin_dir).resolve()
    capabilities = json.loads(subprocess.check_output([str(executable(bin_dir, "pc_environment"))], text=True))
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    physical = set()
    for cpu in affinity or []:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        package, core = read(base / "physical_package_id"), read(base / "core_id")
        if package is not None and core is not None:
            physical.add((package, core))
    cpuinfo = read("/proc/cpuinfo") or ""
    model = next((line.split(":", 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith("model name")), platform.processor())
    cache_path = next((parent / "CMakeCache.txt" for parent in bin_dir.parents if (parent / "CMakeCache.txt").exists()), None)
    cache = {}
    if cache_path:
        for line in cache_path.read_text().splitlines():
            if line.startswith("CMAKE_") and "=" in line and ":" in line:
                key, value = line.split("=", 1)
                key = key.split(":", 1)[0]
                if key in ["CMAKE_CXX_COMPILER", "CMAKE_CXX_FLAGS", "CMAKE_CXX_FLAGS_RELEASE", "CMAKE_CXX_FLAGS_RELWITHDEBINFO", "CMAKE_BUILD_TYPE", "CMAKE_COMMAND"]:
                    cache[key] = value
    compiler = cache.get("CMAKE_CXX_COMPILER", "c++")
    binaries = {name: sha256(executable(bin_dir, name)) for name in ["pc_environment", "bench_locks", "bench_barriers", "bench_counters"]}
    return {
        "platform_id": platform_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "revision": revision,
        "kernel_source_sha256": kernel_digest(),
        "capabilities": capabilities,
        "binary_sha256": binaries,
        "machine": platform.machine(), "os": platform.platform(),
        "cpu_model": model, "os_logical_cpus": os.cpu_count(),
        "affinity_cpus": affinity, "affinity_logical_cpus": len(affinity) if affinity else os.cpu_count(),
        "physical_cores_in_affinity": len(physical) if physical else None,
        "cpu_quota": read("/sys/fs/cgroup/cpu.max"),
        "memory_limit_bytes": read("/sys/fs/cgroup/memory.max"),
        "meminfo": read("/proc/meminfo"),
        "cpu_stat_before": read("/sys/fs/cgroup/cpu.stat"),
        "virtualization": command(["systemd-detect-virt"]),
        "compiler_version": command([compiler, "--version"]),
        "cmake_version": command([cache.get("CMAKE_COMMAND", "cmake"), "--version"]),
        "build_cache": cache,
        "affinity_policy": "none; inherits process affinity",
        "power_mode": "not controlled/unknown on managed environment",
        "alignment_bytes": 64,
        "provenance_note": "Reference execution environment; not a measurement of the student's personal computer."
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--platform-id", required=True)
    parser.add_argument("--revision", default="unrecorded")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collect(args.bin_dir, args.platform_id, args.revision), indent=2) + "\n")
