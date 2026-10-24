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
    # Must match CMake's case-sensitive list(SORT); WindowsPath ordering is case-insensitive.
    paths.sort(key=lambda p: p.as_posix())
    catalog = "".join(f"{p.relative_to(ROOT).as_posix()}:{sha256(p)}\n" for p in paths)
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


def windows_hardware():
    if os.name != "nt":
        return {}
    script = ("$p = Get-CimInstance Win32_Processor | Select-Object -First 1; "
              "$b = Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus -ErrorAction SilentlyContinue | Select-Object -First 1; "
              "[pscustomobject]@{cpu=$p.Name; cores=$p.NumberOfCores; "
              "memory=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory; "
              "ac=if ($b) { [bool]$b.PowerOnline } else { $null }} | ConvertTo-Json -Compress")
    raw = command(["powershell", "-NoProfile", "-Command", script])
    info = json.loads(raw) if raw else {}
    info["power_scheme"] = command(["powercfg", "/getactivescheme"])
    return info


def power_mode(windows):
    if not windows:
        return "not controlled/unknown"
    ac = {True: "AC power", False: "battery", None: "AC state unknown"}[windows.get("ac")]
    return f"{windows.get('power_scheme') or 'power scheme unknown'}; {ac}"


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
    windows = windows_hardware()
    model = next((line.split(":", 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith("model name")),
                 windows.get("cpu") or platform.processor())
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
        "physical_cores_in_affinity": len(physical) if physical else windows.get("cores"),
        "cpu_quota": read("/sys/fs/cgroup/cpu.max"),
        "memory_limit_bytes": read("/sys/fs/cgroup/memory.max"),
        "memory_total_bytes": windows.get("memory"),
        "meminfo": read("/proc/meminfo"),
        "cpu_stat_before": read("/sys/fs/cgroup/cpu.stat"),
        "virtualization": command(["systemd-detect-virt"]),
        "compiler_version": command([compiler, "--version"]),
        "cmake_version": command([cache.get("CMAKE_COMMAND", "cmake"), "--version"]),
        "build_cache": cache,
        "affinity_policy": "none; inherits process affinity",
        "power_mode": power_mode(windows),
        "alignment_bytes": 64
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
