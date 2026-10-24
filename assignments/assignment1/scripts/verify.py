"""Build and test independent configurations, retaining exact logs and exit codes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from collect_environment import ROOT, kernel_digest, executable


def verify(args):
    args.output.mkdir(parents=True, exist_ok=False)
    entries = []
    for mode in args.modes:
        sanitizer = mode if mode in ["address", "undefined", "thread"] else "none"
        build_type = "Release" if mode == "release" else "Debug"
        build = args.build_root.resolve() / mode
        entry = {"mode": mode, "sanitizer": sanitizer, "build_type": build_type, "stages": []}
        environment = os.environ.copy()
        if mode == "address" and args.disable_leak_detection:
            environment["ASAN_OPTIONS"] = environment.get("ASAN_OPTIONS", "") + ":detect_leaks=0"
            entry["limitations"] = "LeakSanitizer disabled explicitly: host blocks /proc task inspection. Address/UB checks remain enabled."
        commands = [
            [str(args.cmake), "-S", str(ROOT), "-B", str(build), f"-DCMAKE_BUILD_TYPE={build_type}", f"-DPC_SANITIZER={sanitizer}"],
            [str(args.cmake), "--build", str(build), "-j", str(args.jobs)],
            # Scope to this assignment's tests; the root build also registers Assignment 2 tests.
            [str(args.ctest), "--test-dir", str(build / "assignments" / "assignment1"), "--output-on-failure", "-j", "1"],
        ]
        for stage, command in zip(["configure", "build", "ctest"], commands):
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=300, env=environment)
                log = run.stdout + run.stderr
                code = run.returncode
            except subprocess.TimeoutExpired as error:
                log, code = str(error), -1
            log_path = args.output / f"{mode}_{stage}.log"
            log_path.write_text(log)
            entry["stages"].append({"stage": stage, "exit_code": code, "log": log_path.name})
            if code:
                # Recognize a real runtime limitation, never suppress a data-race finding.
                unsupported = mode == "thread" and "ThreadSanitizer: unexpected memory mapping" in log and "WARNING: ThreadSanitizer" not in log
                entry["status"] = "unavailable" if unsupported else "failed"
                if unsupported: entry["reason"] = "TSan runtime cannot initialize under this host memory mapping; no race-free claim from TSan."
                break
        else:
            entry["status"] = "passed"
        entries.append(entry)
        print(mode, entry["status"], flush=True)
    if args.stress:
        directory = args.build_root.resolve() / "release" / "assignments" / "assignment1"
        for suite in ["locks", "barriers", "counters"]:
            command = [str(executable(directory, f"test_{suite}")), "--stress"]
            try:
                run = subprocess.run(command, capture_output=True, text=True, timeout=300)
                log, code = run.stdout + run.stderr, run.returncode
            except subprocess.TimeoutExpired as error:
                log, code = str(error), -1
            log_name = f"stress_{suite}.log"
            (args.output / log_name).write_text(log)
            entries.append({"mode": f"stress_{suite}", "status": "passed" if code == 0 else "failed", "exit_code": code, "log": log_name})
            print(f"stress_{suite}", entries[-1]["status"], flush=True)
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "kernel_source_sha256": kernel_digest(), "checks": entries}
    (args.output / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
    return 1 if any(e["status"] == "failed" for e in entries) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmake", type=Path, default=Path("cmake"))
    parser.add_argument("--ctest", type=Path, default=Path("ctest"))
    parser.add_argument("--build-root", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--modes", nargs="+", choices=["debug", "release", "address", "undefined", "thread"], default=["debug", "release", "address"])
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--disable-leak-detection", action="store_true", help="Explicitly disable only LSan for ptrace-restricted hosts; recorded in checks.json")
    raise SystemExit(verify(parser.parse_args()))
