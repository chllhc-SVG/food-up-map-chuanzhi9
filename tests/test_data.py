"""Offline snapshot acceptance checks. Only the standard library is required."""
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


class SnapshotTests(unittest.TestCase):
    def test_map_records_link_to_author_catalog_and_have_honest_precision(self):
        for city in ("wuhan", "fuzhou"):
            with self.subTest(city=city):
                data = load(f"data/{city}.json")
                ids = {v["bvid"] for v in data["catalog"]}
                self.assertEqual(len(ids), len(data["catalog"]))
                for place in data["places"]:
                    with self.subTest(name=place["name"]):
                        self.assertTrue(place["videos"])
                        self.assertTrue(all(r["bvid"] in ids for r in place["videos"]))
                        self.assertIn(place["precision"], {"poi", "address", "area", "pending"})
                        if place["precision"] == "pending":
                            self.assertIsNone(place["lat"])
                            self.assertIsNone(place["lon"])
                        else:
                            south, north, west, east = (29, 32, 113, 116) if city == "wuhan" else (25.1, 26.7, 118.3, 120.6)
                            self.assertTrue(south <= place["lat"] <= north)
                            self.assertTrue(west <= place["lon"] <= east)

    def test_wuhan_preserves_location_grades(self):
        data = load("data/wuhan.json")
        self.assertEqual(len(data["catalog"]), 342)
        self.assertEqual(Counter(p["precision"] for p in data["places"]),
                         {"poi": 203, "address": 42, "area": 67, "pending": 14})

    def test_fuzhou_snapshot_matches_all_reviewed_pages(self):
        data = load("data/fuzhou.json")
        catalog = load("docs/fuzhou-catalog.json")
        expected = {(v["bvid"], v["title"], v["published"]) for v in catalog}
        self.assertEqual(len(expected), 293)
        self.assertEqual(data["up"]["mid"], "3493128128432841")
        self.assertEqual(expected, {(v["bvid"], v["title"], v["published"]) for v in data["catalog"]})
        self.assertTrue(data["coverage"]["catalogComplete"])
        macau = "BV1pM3b6SErN"
        self.assertTrue(any(v["bvid"] == macau for v in catalog))
        self.assertFalse(any(v["bvid"] == macau for p in data["places"] for v in p["videos"]))

    def test_fuzhou_can_be_republished_offline_from_the_included_evidence(self):
        with tempfile.TemporaryDirectory() as staging:
            output = Path(staging) / "fuzhou.json"
            subprocess.run([sys.executable, str(ROOT / "scripts/import_fuzhou.py"),
                            str(ROOT / "docs/fuzhou-reviewed.json"), "--out", str(output)],
                           check=True, cwd=staging)
            rebuilt = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(rebuilt, load("data/fuzhou.json"))

    def test_fuzhou_keeps_historical_closures_in_the_catalog(self):
        data = load("data/fuzhou.json")
        closed = {v["bvid"] for v in data["catalog"] if v.get("stance") == "historical_closure"}
        self.assertIn("BV1ThGHzREk5", closed)
        linked = {v["bvid"] for p in data["places"] for v in p["videos"]}
        self.assertTrue(closed.isdisjoint(linked))


if __name__ == "__main__":
    unittest.main()
