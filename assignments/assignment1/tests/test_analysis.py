"""Independent known-answer checks for episode rates, quartiles and strong scaling."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_benchmarks import FIELDS
from summarize import summarize


class AnalysisTests(unittest.TestCase):
    def fixture(self, root):
        cases, rows = [], []
        for suite in ["barriers", "locks"]:
            for p in [1, 2]:
                cid = f"{suite}-{p}"
                case = {"suite": suite, "implementation": "std_barrier" if suite == "barriers" else "std_mutex",
                        "threads": p, "config_id": cid}
                if suite == "barriers": case.update(episodes=6)
                else: case.update(mode="fixed_total", total_operations=100, prime_n=2, outside_work=0)
                cases.append(case)
                for repetition in range(3):
                    program = (repetition + 1) * 1000000 * (p if suite == "barriers" else 1 / p)
                    row = {key: "" for key in FIELDS}
                    row.update(case)
                    row.update(run_id="known", platform_id="synthetic", revision="test", source_sha256="test",
                               repetition=repetition, is_warmup=0, status="ok", program_elapsed_ns=int(program),
                               worker_elapsed_ns=int(program / 2), mode=case.get("mode", "fixed_episodes"))
                    if suite == "locks": row.update(checksum=100)
                    rows.append(row)
        manifest = {"run_id": "known", "platform_id": "synthetic", "source_sha256": "test",
                    "matrix": {"warmup_repetitions": 0, "measured_repetitions": 3}, "resolved_cases": cases}
        (root / "manifest.json").write_text(json.dumps(manifest))
        self.write(root, rows)
        return rows

    def write(self, root, rows):
        with (root / "raw.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)

    def test_known_rates_and_speedup(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.fixture(root)
            result = summarize(root, root / "processed")
            self.assertEqual(result["failed_samples"], 0)
            rows = list(csv.DictReader((root / "processed/summary.csv").open()))
            barrier = next(r for r in rows if r["suite"] == "barriers" and r["threads"] == "2")
            # Worker ns are [1m,2m,3m], so episode/s [6000,3000,2000]. No x2 threads.
            self.assertAlmostEqual(float(barrier["median_throughput"]), 3000)
            self.assertAlmostEqual(float(barrier["q1_throughput"]), 2500)
            self.assertAlmostEqual(float(barrier["q3_throughput"]), 4500)
            lock = next(r for r in rows if r["suite"] == "locks" and r["threads"] == "2")
            self.assertAlmostEqual(float(lock["speedup"]), 2)

    def test_corruption_and_duplicates_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            rows = self.fixture(root)
            rows[-1]["checksum"] = 99
            self.write(root, rows)
            with self.assertRaises(ValueError): summarize(root, root / "bad")
            rows = self.fixture(root)
            self.write(root, rows + [rows[0]])
            with self.assertRaises(ValueError): summarize(root, root / "bad")


if __name__ == "__main__": unittest.main()
