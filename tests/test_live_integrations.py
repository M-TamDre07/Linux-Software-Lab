from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_live_integrations import (
    IntegrationCheckError,
    _catalogue_diff,
    _supabase_diff,
    check_supabase,
    check_vercel,
    load_catalog,
    load_public_supabase_config,
)
from scripts.sync_supabase_catalog import CATALOG_PATH, to_record


ROOT = Path(__file__).resolve().parents[1]


class LiveIntegrationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog(CATALOG_PATH)

    def test_local_canonical_catalogue_matches_its_deployed_json_shape(self) -> None:
        with CATALOG_PATH.open(encoding="utf-8") as handle:
            canonical = json.load(handle)
        self.assertEqual(_catalogue_diff(canonical, canonical), [])

    def test_vercel_parity_check_reports_stale_fields_without_dumping_values(self) -> None:
        canonical = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        stale = json.loads(json.dumps(canonical))
        stale["software"][0]["previewAlt"] = "stale value"
        issues = _catalogue_diff(canonical, stale)
        self.assertTrue(any("previewAlt" in issue and "differs" in issue for issue in issues))
        self.assertNotIn("stale value", " ".join(issues))

    def test_supabase_parity_uses_the_same_mapping_as_the_trusted_sync(self) -> None:
        expected = [
            to_record(app, index, "")
            for index, app in enumerate(self.catalog["software"])
        ]
        actual = [
            to_record(app, index, "2026-10-27T00:00:00+00:00")
            for index, app in enumerate(self.catalog["software"])
        ]
        self.assertEqual(_supabase_diff(expected, actual), [])

        actual[0]["preview_alt"] = "stale value"
        issues = _supabase_diff(expected, actual)
        self.assertTrue(any("preview_alt" in issue for issue in issues))
        self.assertNotIn("stale value", " ".join(issues))

    def test_live_audit_fails_on_missing_and_extra_published_rows(self) -> None:
        expected = [
            to_record(app, index, "")
            for index, app in enumerate(self.catalog["software"])
        ]
        missing = _supabase_diff(expected, expected[:-1])
        self.assertTrue(any("missing from Supabase" in issue for issue in missing))
        extra = [*expected, {**expected[0], "id": "extra-app"}]
        self.assertTrue(any("unexpected published application" in issue for issue in _supabase_diff(expected, extra)))

    def test_browser_config_parser_accepts_only_exact_project_and_public_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.js"
            path.write_text(
                'window.LSL_SUPABASE_CONFIG = Object.freeze({ url: "https://ttofugaqwthmvhvntdlc.supabase.co", '
                'publishableKey: "sb_publishable_test-key" });',
                encoding="utf-8",
            )
            self.assertEqual(
                load_public_supabase_config(path),
                ("https://ttofugaqwthmvhvntdlc.supabase.co", "sb_publishable_test-key"),
            )

            path.write_text(
                'window.LSL_SUPABASE_CONFIG = { url: "https://attacker.example", '
                'publishableKey: "sb_publishable_test-key" };',
                encoding="utf-8",
            )
            with self.assertRaises(IntegrationCheckError):
                load_public_supabase_config(path)

            path.write_text(
                'window.LSL_SUPABASE_CONFIG = { url: "https://ttofugaqwthmvhvntdlc.supabase.co", '
                'publishableKey: "service_role_fake" };',
                encoding="utf-8",
            )
            with self.assertRaises(IntegrationCheckError):
                load_public_supabase_config(path)

    def test_config_parser_rejects_duplicate_url_or_key_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.js"
            path.write_text(
                'const a = { url: "https://ttofugaqwthmvhvntdlc.supabase.co", '
                'url: "https://ttofugaqwthmvhvntdlc.supabase.co", '
                'publishableKey: "sb_publishable_test-key" };',
                encoding="utf-8",
            )
            with self.assertRaises(IntegrationCheckError):
                load_public_supabase_config(path)

    def test_live_endpoint_wrappers_report_drift_without_writing(self) -> None:
        with CATALOG_PATH.open(encoding="utf-8") as handle:
            canonical = json.load(handle)
        with patch("scripts.check_live_integrations._http_get_json", return_value=canonical):
            check_vercel(canonical)

        supabase_rows = [
            to_record(app, index, "")
            for index, app in enumerate(self.catalog["software"])
        ]
        with (
            patch("scripts.check_live_integrations.load_public_supabase_config", return_value=(
                "https://ttofugaqwthmvhvntdlc.supabase.co", "sb_publishable_test-key"
            )),
            patch("scripts.check_live_integrations._http_get_json", return_value=supabase_rows),
        ):
            check_supabase(canonical)

        with patch("scripts.check_live_integrations._http_get_json", return_value={"unexpected": True}):
            with self.assertRaises(IntegrationCheckError):
                check_vercel(canonical)


if __name__ == "__main__":
    unittest.main()
