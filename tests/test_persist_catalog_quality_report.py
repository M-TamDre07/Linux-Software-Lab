import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import persist_catalog_quality_report as persistence


class PersistCatalogueReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.report_path = Path(self.temp.name) / "report.json"
        self.report = {
            "algorithm": "lsl-catalog-health-v1",
            "entry_count": 1,
            "overall_score": 88,
            "recommendation": "review",
            "finding_count": 1,
            "severity_counts": {"error": 0, "warning": 1, "info": 0},
            "entries": [{"software_id": "demo", "score": 88, "recommendation": "review", "finding_count": 1}],
            "findings": [{
                "software_id": "demo",
                "rule": "missing_keywords",
                "severity": "warning",
                "deduction": 8,
                "message": "Add search keywords.",
            }],
        }
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.env = patch.dict(os.environ, {
            "SUPABASE_URL": persistence.EXPECTED_SUPABASE_URL,
            "SUPABASE_SECRET_KEY": "unit-test-placeholder",
            "GITHUB_SHA": "a" * 40,
        })
        self.env.start()
        self.report_patch = patch.object(persistence, "REPORT", self.report_path)
        self.report_patch.start()

    def tearDown(self):
        self.report_patch.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_persists_summary_and_findings_to_configured_project(self):
        with patch.object(persistence, "api_request", side_effect=[
            [{"id": "00000000-0000-0000-0000-000000000001"}],
            None,
        ]) as api:
            self.assertEqual(persistence.main(), 0)
        self.assertEqual(api.call_count, 2)
        self.assertEqual(api.call_args_list[0].args[0], persistence.EXPECTED_SUPABASE_URL)
        self.assertEqual(api.call_args_list[0].args[2], "/rest/v1/catalog_quality_runs?select=id")
        self.assertEqual(api.call_args_list[0].args[4]["source_commit_sha"], "a" * 40)
        self.assertEqual(api.call_args_list[1].args[2], "/rest/v1/catalog_quality_findings")
        self.assertEqual(api.call_args_list[1].args[4][0]["run_id"],
                         "00000000-0000-0000-0000-000000000001")

    def test_rejects_unapproved_project_url_before_network_calls(self):
        os.environ["SUPABASE_URL"] = "https://other-project.supabase.co"
        with patch.object(persistence, "api_request") as api:
            self.assertEqual(persistence.main(), 2)
            api.assert_not_called()

    def test_failed_findings_insert_attempts_to_remove_incomplete_summary(self):
        with patch.object(persistence, "api_request", side_effect=[
            [{"id": "00000000-0000-0000-0000-000000000001"}],
            persistence.ApiError("simulated failure"),
            None,
        ]) as api:
            self.assertEqual(persistence.main(), 1)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(api.call_args_list[2].args[2],
                         "/rest/v1/catalog_quality_runs?id=eq.00000000-0000-0000-0000-000000000001")
        self.assertEqual(api.call_args_list[2].args[3], "DELETE")

    def test_rejects_invalid_commit_sha_before_network_calls(self):
        os.environ["GITHUB_SHA"] = "not-a-commit"
        with patch.object(persistence, "api_request") as api:
            self.assertEqual(persistence.main(), 2)
            api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
