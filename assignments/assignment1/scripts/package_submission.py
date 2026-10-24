"""Create a self-contained source + PDF + data ZIP from an explicit allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from collect_environment import ROOT, ASSIGNMENT, kernel_digest


def package(output):
    required = [ASSIGNMENT / "report/Assignment1_Report_EN.pdf",
                ASSIGNMENT / "include/pc/locks/mcs_lock.hpp", ASSIGNMENT / "tests/test_locks.cpp"]
    for path in required:
        if not path.is_file(): raise ValueError(f"missing required deliverable: {path.relative_to(ROOT)}")
    # The statement asks for the PDF report and the relevant C++ source; internal notes stay out.
    allowed = [ROOT / "CMakeLists.txt", ROOT / ".editorconfig", ASSIGNMENT / "README.md",
               ASSIGNMENT / "CMakeLists.txt", ASSIGNMENT / "report/Assignment1_Report_EN.pdf"]
    for folder in ["include", "src", "benchmarks", "tests", "config", "scripts", "results"]:
        allowed.extend(p for p in (ASSIGNMENT / folder).rglob("*") if p.is_file())
    files = []
    for path in sorted(set(allowed)):
        relative = path.relative_to(ROOT)
        if any(part in ["build", "local", "__pycache__", ".git"] for part in relative.parts): continue
        if path.suffix in [".pyc", ".o", ".exe"] or path.name == ".gitkeep": continue
        files.append(path)
    manifest = {"kernel_source_sha256": kernel_digest(),
                "files": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files: archive.write(path, "Assignment1/" + path.relative_to(ROOT).as_posix())
        archive.writestr("Assignment1/submission_manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(output) as archive:
        if archive.testzip(): raise ValueError("ZIP CRC failed")
    print(json.dumps({"output": str(output.resolve()), "files": len(files) + 1, "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Assignment1_GitGud031005.zip")
    package(parser.parse_args().output)
