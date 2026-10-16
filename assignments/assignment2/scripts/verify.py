"""Build/test Ass2 plus Ass1 regression in independent modes; preserve every log/exit code."""

import argparse, json, os, subprocess
from pathlib import Path
from common import ROOT, kernel_digest, environment, executable


def verify(args):
    args.output.mkdir(parents=True, exist_ok=False)
    checks = []
    for mode in args.modes:
        sanitizer = mode if mode in ["address", "undefined", "thread"] else "none"
        build_type = "Release" if mode == "release" else "Debug"
        build = args.build_root / mode
        entry = {"mode": mode, "stages": [], "status": "passed"}
        env = os.environ.copy()
        if mode == "address" and args.disable_leak_detection:
            env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "") + ":detect_leaks=0"
            entry["limitations"] = (
                "LSan explicitly disabled for a host that blocks /proc/ptrace; address and UB checks stay enabled."
            )
        commands = [
            [
                str(args.cmake),
                "-S",
                str(ROOT),
                "-B",
                str(build),
                f"-DCMAKE_BUILD_TYPE={build_type}",
                f"-DPC_SANITIZER={sanitizer}",
            ],
            [str(args.cmake), "--build", str(build), "-j", str(args.jobs)],
            [str(args.ctest), "--test-dir", str(build), "--output-on-failure", "-j", "1"],
        ]
        for name, cmd in zip(["configure", "build", "ctest"], commands):
            try:
                r = subprocess.run(cmd, text=True, capture_output=True, timeout=360, env=env)
                log = r.stdout + r.stderr
                code = r.returncode
            except subprocess.TimeoutExpired as e:
                log = str(e)
                code = -1
            log_name = f"{mode}_{name}.log"
            (args.output / log_name).write_text(log)
            entry["stages"].append({"stage": name, "exit_code": code, "log": log_name})
            if code:
                entry["status"] = (
                    "unavailable"
                    if mode == "thread"
                    and "ThreadSanitizer: unexpected memory mapping" in log
                    and "WARNING: ThreadSanitizer" not in log
                    else "failed"
                )
                break
        checks.append(entry)
        print(mode, entry["status"], flush=True)
    if args.stress:
        for suite in ["lists", "search"]:
            name = f"stress_{suite}"
            cmd = [
                str(
                    executable(
                        args.build_root / "release/assignments/assignment2", f"a2_test_{suite}"
                    )
                ),
                "--stress",
            ]
            try:
                r = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
                log = r.stdout + r.stderr
                code = r.returncode
            except subprocess.TimeoutExpired as e:
                log = str(e)
                code = -1
            (args.output / (name + ".log")).write_text(log)
            checks.append(
                {"mode": name, "status": "passed" if code == 0 else "failed", "exit_code": code}
            )
            print(name, checks[-1]["status"], flush=True)
    result = {"source_sha256": kernel_digest(), "environment": environment(), "checks": checks}
    (args.output / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
    return int(any(x["status"] == "failed" for x in checks))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cmake", type=Path, default=Path("cmake"))
    p.add_argument("--ctest", type=Path, default=Path("ctest"))
    p.add_argument("--build-root", type=Path, default=ROOT / "build/ass2-verify")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument(
        "--modes",
        nargs="+",
        choices=["debug", "release", "address", "undefined", "thread"],
        default=["debug", "release", "address", "undefined", "thread"],
    )
    p.add_argument("--disable-leak-detection", action="store_true")
    p.add_argument("--stress", action="store_true")
    raise SystemExit(verify(p.parse_args()))
