"""Create a self-contained source + PDF + data ZIP from an explicit allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from collect_environment import ROOT, ASSIGNMENT, kernel_digest


LATEX = ASSIGNMENT / "report/latex"
REPORT = LATEX / "build/main.pdf"
REPORT_NAME = "Assignment1_Report.pdf"


def stale_report_inputs():
    # The PDF embeds the C++ sources as listings, so editing either without rebuilding it ships a mismatch.
    inputs = [p for p in LATEX.rglob("*") if p.is_file() and "build" not in p.relative_to(LATEX).parts
              and p.name != "build-run.txt"]
    for folder in ["include", "src", "benchmarks"]:
        inputs.extend(p for p in (ASSIGNMENT / folder).rglob("*") if p.is_file())
    built = REPORT.stat().st_mtime
    return [p.relative_to(ROOT).as_posix() for p in inputs if p.stat().st_mtime > built]


def package(output):
    required = [REPORT, ASSIGNMENT / "include/pc/locks/mcs_lock.hpp", ASSIGNMENT / "tests/test_locks.cpp"]
    for path in required:
        if not path.is_file(): raise ValueError(f"missing required deliverable: {path.relative_to(ROOT)}")
    stale = stale_report_inputs()
    if stale: raise ValueError(f"report PDF is older than its inputs, rebuild it with latexmk: {stale[:5]}")
    # The statement asks for the PDF report and the relevant C++ source; internal notes stay out.
    allowed = [ROOT / "CMakeLists.txt", ROOT / ".editorconfig", ASSIGNMENT / "README.md", ASSIGNMENT / "CMakeLists.txt"]
    for folder in ["include", "src", "benchmarks", "tests", "config", "scripts", "results"]:
        allowed.extend(p for p in (ASSIGNMENT / folder).rglob("*") if p.is_file())
    files = []
    for path in sorted(set(allowed)):
        relative = path.relative_to(ROOT)
        if any(part in ["build", "local", "__pycache__", ".git"] for part in relative.parts): continue
        if path.suffix in [".pyc", ".o", ".exe"] or path.name == ".gitkeep": continue
        files.append(path)
    entries = [(REPORT, REPORT_NAME)] + [(p, p.relative_to(ROOT).as_posix()) for p in files]
    manifest = {"kernel_source_sha256": kernel_digest(),
                "files": {name: hashlib.sha256(path.read_bytes()).hexdigest() for path, name in entries}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in entries: archive.write(path, "Assignment1/" + name)
        archive.writestr("Assignment1/submission_manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(output) as archive:
        if archive.testzip(): raise ValueError("ZIP CRC failed")
    print(json.dumps({"output": str(output.resolve()), "files": len(entries) + 1, "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Assignment1_GitGud031005.zip")
    package(parser.parse_args().output)
