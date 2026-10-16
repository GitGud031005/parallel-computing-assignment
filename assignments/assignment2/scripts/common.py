"""Source identity and small portable helpers for Ass2 experiments."""

from datetime import datetime, timezone
import hashlib, json, os, platform, subprocess
from pathlib import Path

A2 = Path(__file__).resolve().parents[1]
ROOT = A2.parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kernel_digest():
    paths = (
        list(A2.rglob("*.cpp"))
        + list(A2.rglob("*.hpp"))
        + [ROOT / "CMakeLists.txt", A2 / "CMakeLists.txt"]
    )
    catalog = "".join(f"{p.relative_to(ROOT).as_posix()}:{sha256(p)}\n" for p in sorted(paths))
    return hashlib.sha256(catalog.encode()).hexdigest()


def pipeline_digest():
    paths = sorted((A2 / "scripts").glob("*.py")) + sorted((A2 / "config").glob("*.json"))
    return hashlib.sha256("".join(f"{p.name}:{sha256(p)}\n" for p in paths).encode()).hexdigest()


def executable(directory, name):
    return Path(directory) / (name + (".exe" if os.name == "nt" else ""))


def environment():
    def read(p):
        try:
            return Path(p).read_text().strip()
        except OSError:
            return None

    try:
        compiler = subprocess.check_output(["c++", "--version"], text=True).splitlines()[0]
    except (OSError, subprocess.SubprocessError):
        compiler = None
    cpu = read("/proc/cpuinfo") or ""
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "machine": platform.machine(),
        "compiler": compiler,
        "cpu_model": next(
            (s.split(":", 1)[1].strip() for s in cpu.splitlines() if s.startswith("model name")),
            None,
        ),
        "logical_cpus": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "cpu_quota": read("/sys/fs/cgroup/cpu.max"),
        "power_mode": "not controlled",
        "platform_scope": "Execution host; label honestly when rerunning on a personally owned machine.",
    }
