import json
import unittest
from pathlib import Path

from scripts.catalog_intelligence import analyze_catalog


ROOT = Path(__file__).resolve().parents[1]


class CanonicalCatalogIntelligenceTests(unittest.TestCase):
    def test_canonical_catalog_can_be_scored_without_network_access(self):
        data = json.loads((ROOT / "public/data/software.json").read_text(encoding="utf-8"))
        report = analyze_catalog(data)
        self.assertEqual(report["entry_count"], len(data["software"]))
        self.assertEqual(report["algorithm"], "lsl-catalog-health-v1")
        self.assertGreaterEqual(report["overall_score"], 0)
        self.assertLessEqual(report["overall_score"], 100)
        self.assertEqual(report["finding_count"], len(report["findings"]))
        self.assertEqual(
            report["severity_counts"]["error"]
            + report["severity_counts"]["warning"]
            + report["severity_counts"]["info"],
            report["finding_count"],
        )

    def test_report_contains_no_source_catalog_mutations(self):
        path = ROOT / "public/data/software.json"
        before = path.read_bytes()
        data = json.loads(before)
        analyze_catalog(data)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
