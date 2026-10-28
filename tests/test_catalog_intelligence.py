import unittest
from datetime import date

from scripts.catalog_intelligence import analyze_catalog


class CatalogIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 28)
        self.base = {
            "id": "demo", "status": "released", "releaseUrl": "https://example.com/release",
            "keywords": ["demo"], "features": ["Search"], "updatedAt": "2026-10-20",
        }

    def test_healthy_entry_scores_ready(self):
        report = analyze_catalog({"software": [self.base]}, self.today)
        self.assertEqual(report["overall_score"], 100)
        self.assertEqual(report["recommendation"], "ready")
        self.assertEqual(report["finding_count"], 0)

    def test_stale_testing_entry_gets_explainable_findings(self):
        app = {**self.base, "status": "testing", "updatedAt": "2026-08-01",
               "keywords": [], "features": []}
        report = analyze_catalog({"software": [app]}, self.today)
        rules = {finding["rule"] for finding in report["findings"]}
        self.assertIn("testing_stale", rules)
        self.assertIn("missing_keywords", rules)
        self.assertIn("missing_features", rules)
        self.assertEqual(report["recommendation"], "review")
        self.assertLess(report["overall_score"], 100)

    def test_planned_entry_with_release_url_is_error(self):
        app = {**self.base, "status": "planned"}
        report = analyze_catalog({"software": [app]}, self.today)
        self.assertEqual(report["severity_counts"]["error"], 1)
        self.assertEqual(report["recommendation"], "needs_attention")

    def test_bad_root_and_empty_catalog_are_rejected(self):
        for value in ({}, {"software": []}, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze_catalog(value, self.today)

    def test_report_is_deterministic_for_fixed_date(self):
        first = analyze_catalog({"software": [self.base]}, self.today)
        second = analyze_catalog({"software": [self.base]}, self.today)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
