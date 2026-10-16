"""Executable-level oracles: uneven partition, checksum, metrics and invalid inputs."""
import json
from pathlib import Path
import subprocess
import sys

directory = Path(sys.argv[1])


def invoke(suite, *args, valid=True):
    exe = directory / (f"bench_{suite}" + (".exe" if sys.platform == "win32" else ""))
    result = subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True, timeout=15)
    if not valid:
        assert result.returncode != 0, (suite, args, result.stdout)
        return
    assert result.returncode == 0, (suite, args, result.stderr)
    data = json.loads(result.stdout)
    assert data["program_elapsed_ns"] >= data["worker_elapsed_ns"] > 0
    return data


for impl in ["tas", "ttas", "mcs", "std_mutex", "ttas_backoff"]:
    for n, expected in [(97, 51), (100, 0)]:
        r = invoke("locks", "--implementation", impl, "--threads", 3, "--mode", "fixed_total",
                   "--total-operations", 17, "--prime-n", n, "--outside-work", 2)
        assert r["checksum"] == expected and r["total_operations"] == 17
    r = invoke("locks", "--implementation", impl, "--threads", 3,
               "--iterations-per-thread", 7, "--prime-n", 97, "--outside-work", 1)
    assert r["checksum"] == 42 and r["total_operations"] == 21
    r = invoke("locks", "--implementation", impl, "--threads", 3, "--mode", "fixed_total",
               "--total-operations", 1, "--prime-n", 97)
    assert r["checksum"] == 1
for impl in ["mutex_tas", "mutex_ttas", "mutex_mcs", "mutex_std", "cas", "faa", "cas_backoff"]:
    for count in [1, 17, 1001]:
        r = invoke("counters", "--implementation", impl, "--threads", 3, "--total-operations", count)
        assert r["final_value"] == count and r["checksum"] == count * (count - 1) // 2
for impl in ["sense_reversing", "std_barrier"]:
    r = invoke("barriers", "--implementation", impl, "--threads", 3, "--episodes", 101)
    assert r["episodes"] == 101 and r["total_operations"] is None
for suite in ["locks", "barriers", "counters"]:
    for bad in ["0", "-1", "abc", "1x", "18446744073709551616", "1025"]:
        invoke(suite, "--threads", bad, valid=False)
    invoke(suite, "--implementation", "not-an-algorithm", valid=False)
    invoke(suite, "--unknown", 1, valid=False)
    invoke(suite, "--threads", valid=False)
    invoke(suite, "--threads", 1, "--threads", 2, valid=False)
invoke("locks", "--prime-n", 1, valid=False)
invoke("locks", "--outside-work", "18446744073709551615", valid=False)
invoke("locks", "--iterations-per-thread", "18446744073709551615", "--threads", 2, valid=False)
invoke("locks", "--mode", "fixed_total", "--iterations-per-thread", 2, valid=False)
invoke("locks", "--total-operations", 2, valid=False)
invoke("barriers", "--episodes", 0, valid=False)
invoke("counters", "--total-operations", 0, valid=False)
print("PASS CLI: real executables, required/extra variants, uneven and tiny workload, invalid input/overflow")
