import json, sys, tempfile, unittest, shutil
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_data import convert
from oracle import read_graph, frontier, check_paths
from common import sha256
from summarize import summarize, quartiles


class DataTests(unittest.TestCase):
    def test_oneway_roundabout_missing_access(self):
        xml = """<osm><node id="1" lat="10" lon="106"/><node id="2" lat="10.001" lon="106"/><node id="3" lat="10.002" lon="106"/>
        <way><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="-1"/></way>
        <way><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
        <way><nd ref="3"/><nd ref="1"/><tag k="highway" v="service"/><tag k="access" v="private"/></way>
        <way><nd ref="3"/><nd ref="999"/><tag k="highway" v="primary"/></way></osm>"""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            p = d / "x.osm"
            p.write_text(xml)
            metadata = convert(p, d / "out", "unit fixture")
            nodes, edges = read_graph(d / "out/network.road")
            self.assertFalse(edges[0])
            self.assertTrue(any(v == 0 for v, _, _ in edges[1]))
            self.assertEqual(metadata["directed_edges"], 3)
            self.assertEqual(metadata["skipped_missing_segments"], 1)
            self.assertTrue(all(d > 0 and t > 0 for row in edges for _, (d, t), _ in row))
            with self.assertRaises(ValueError):
                convert(p, d / "out", "unit fixture")

    def test_frontier_and_corrupt_path(self):
        _, edges = read_graph(Path(__file__).resolve().parents[1] / "data/tradeoff.road")
        self.assertEqual(frontier(edges, 0, 3, "pareto"), [(2, 18), (12, 12), (18, 2)])
        with self.assertRaises(ValueError):
            check_paths(
                edges,
                [{"vertices": [0, 3], "edge_ids": [4], "cost": [1, 1]}],
                0,
                3,
                "pareto",
                [(12, 12)],
            )


class AnalysisTests(unittest.TestCase):
    def fixture(self, root):
        run = root / "run"
        run.mkdir()
        shutil.copyfile(
            Path(__file__).resolve().parents[1] / "data/tradeoff.road", run / "network.road"
        )
        case = {
            "id": "c0000",
            "suite": "sets",
            "implementation": "coarse",
            "threads": 1,
            "mix": "read_heavy",
            "key_range": 32,
            "operations": 100,
            "seed": 1,
        }
        manifest = {
            "matrix": {"warmups": 1, "repetitions": 3},
            "cases": [case],
            "graph_sha256": sha256(run / "network.road"),
            "source_sha256": "fixture",
            "oracle": {},
        }
        (run / "manifest.json").write_text(json.dumps(manifest))
        rows = []
        for rep, ms in [(-1, 999), (0, 1), (1, 2), (2, 4)]:
            sample = {
                "suite": "sets",
                "implementation": "coarse",
                "threads": 1,
                "mix": "read_heavy",
                "key_range": 32,
                "operations": 100,
                "seed": 1,
                "reads": 80,
                "inserts": 10,
                "erases": 10,
                "successful_operations": 50,
                "final_size": 16,
                "program_elapsed_ns": ms * 1000000,
                "source_sha256": "fixture",
                "build_type": "Release",
                "sanitizer": "none",
            }
            rows.append(
                {
                    "case_id": "c0000",
                    "repetition": rep,
                    "warmup": rep < 0,
                    "status": "ok",
                    "sample": sample,
                }
            )
        (run / "raw.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
        return run, rows

    def test_known_answer(self):
        self.assertEqual(quartiles([1, 2, 4]), (1.5, 3))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, _ = self.fixture(root)
            rows = summarize(run, root / "summary")
            self.assertEqual(rows[0]["median_ms"], 2)
            self.assertEqual(rows[0]["samples"], 3)
            self.assertEqual(rows[0]["speedup_vs_own_p1"], 1)

    def test_corruption_duplicates_and_missing(self):
        for kind in ["duplicate", "missing", "corrupt"]:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                run, rows = self.fixture(root)
                if kind == "duplicate":
                    rows.append(deepcopy(rows[0]))
                if kind == "missing":
                    rows.pop()
                if kind == "corrupt":
                    rows[1]["sample"]["reads"] = 0
                (run / "raw.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
                with self.assertRaises(ValueError):
                    summarize(run, root / "summary")


if __name__ == "__main__":
    unittest.main()
