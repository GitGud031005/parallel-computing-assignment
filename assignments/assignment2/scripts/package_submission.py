"""Package self-contained Ass2 source, report, exact data and validation without course originals."""

import argparse, hashlib, json, zipfile
from pathlib import Path
from common import ROOT, A2, kernel_digest


def package(args):
    required = [
        A2 / "report/report.pdf",
        A2 / "report/report.md",
        args.checks_dir / "checks.json",
        args.run_dir / "network.road",
        args.run_dir / "raw.jsonl",
        args.processed / "validation.json",
    ]
    for p in required:
        if not p.is_file():
            raise ValueError(f"missing required artifact: {p}")
    digest = kernel_digest()
    checks = json.loads((args.checks_dir / "checks.json").read_text())
    validation = json.loads((args.processed / "validation.json").read_text())
    if (
        checks["source_sha256"] != digest
        or validation["source_sha256"] != digest
        or not validation["complete"]
        or not validation["quality_exact"]
        or any(c["status"] == "failed" for c in checks["checks"])
    ):
        raise ValueError("source or validation mismatch")
    entries = {}
    for p in [ROOT / "CMakeLists.txt", ROOT / ".editorconfig", ROOT / ".gitignore"]:
        entries[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    for p in A2.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix in {".pyc", ".o", ".exe"}:
            continue
        if p.suffix in {".pdf", ".ipynb", ".osm", ".bz2", ".zip"} and p != A2 / "report/report.pdf":
            continue
        entries[p.relative_to(ROOT).as_posix()] = p.read_bytes()
    for folder, target in [
        (args.run_dir, "experiments/reference"),
        (args.processed, "experiments/processed"),
        (args.figures, "experiments/figures"),
        (args.checks_dir, "experiments/validation"),
    ]:
        for p in folder.rglob("*"):
            if p.is_file():
                entries[target + "/" + p.relative_to(folder).as_posix()] = p.read_bytes()
    entries["README.md"] = (
        b"# Assignment 2 source and report ZIP\n\nBuild from this directory with cmake -S . -B build -DCMAKE_BUILD_TYPE=Release, cmake --build build -j 4, and ctest --test-dir build --output-on-failure.\n\nSee assignments/assignment2/README.md for APIs, data and all commands. Report: assignments/assignment2/report/report.pdf. Reproducible graph/raw/summary/figures/checks: experiments/. Original course slides/statements/notebook are excluded. OSM-derived input: OpenStreetMap contributors, ODbL, https://www.openstreetmap.org/copyright.\n"
    )
    manifest = {
        "source_sha256": digest,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(entries.items())},
    }
    entries["submission_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, raw in sorted(entries.items()):
            z.writestr("Assignment2/" + name, raw)
    with zipfile.ZipFile(args.output) as z:
        if z.testzip():
            raise ValueError("ZIP CRC failed")
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "files": len(entries),
                "bytes": args.output.stat().st_size,
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["run-dir", "processed", "figures", "checks-dir"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "dist/Assignment2_GitGud031005.zip")
    package(p.parse_args())
