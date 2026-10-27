import copy
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs

from scripts.sync_supabase_catalog import (
    EXPECTED_SUPABASE_URL,
    build_stale_filter,
    catalog_rows_match,
    load_catalog,
    to_record,
    validate_supabase_url,
)


class SupabaseCatalogSyncTests(unittest.TestCase):
    def test_current_catalog_passes_sync_preflight(self):
        data = load_catalog()
        self.assertEqual(data["schemaVersion"], 2)
        self.assertGreaterEqual(len(data["software"]), 1)

    def test_catalog_entry_maps_to_database_columns(self):
        data = load_catalog()
        app = next(item for item in data["software"] if item["id"] == "sorot")
        record = to_record(app, 1, "2026-10-25T00:00:00+00:00")
        self.assertEqual(record["id"], "sorot")
        self.assertEqual(record["detail_url"], app["detailUrl"])
        self.assertEqual(record["icon_image"], app["iconImage"])
        self.assertEqual(record["updated_at"], app["updatedAt"])
        self.assertTrue(record["published"])
        self.assertEqual(record["sort_order"], 1)

    def test_only_the_exact_supabase_project_origin_is_accepted(self):
        self.assertEqual(validate_supabase_url(EXPECTED_SUPABASE_URL + "/"), EXPECTED_SUPABASE_URL)
        invalid_urls = [
            "",
            "http://ttofugaqwthmvhvntdlc.supabase.co",
            "https://ttofugaqwthmvhvntdlc.supabase.co.attacker.example",
            "https://attacker.supabase.co",
            EXPECTED_SUPABASE_URL + "/path",
        ]
        for value in invalid_urls:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "match the configured"):
                    validate_supabase_url(value)

    def test_verification_compares_all_catalogue_fields(self):
        data = load_catalog()
        rows = [
            to_record(app, index, "2026-10-25T00:00:00+00:00")
            for index, app in enumerate(data["software"])
        ]
        self.assertTrue(catalog_rows_match(rows, copy.deepcopy(rows)))
        changed = copy.deepcopy(rows)
        changed[1]["summary"] = "Unexpected database value"
        self.assertFalse(catalog_rows_match(rows, changed))
        self.assertFalse(catalog_rows_match(rows, rows[:1]))
        self.assertFalse(catalog_rows_match(rows, [{"id": "paketscope"}]))

    def test_stale_row_filter_is_encoded_from_validated_slugs(self):
        query = build_stale_filter(["paketscope", "sorot"])
        parameters = parse_qs(query)
        self.assertEqual(parameters["id"], ["not.in.(paketscope,sorot)"])
        self.assertNotIn(" ", query)

    def test_stale_row_filter_rejects_injection_and_ambiguous_ids(self):
        malicious_ids = [
            ["sorot') OR 1=1 --"],
            ["sorot;DROP TABLE software_catalog"],
            ["../../secret"],
            ["sorot", "another slug"],
            ["sorot'--"],
            ["sorot", "sorot"],
            [],
        ]
        for identifiers in malicious_ids:
            with self.subTest(identifiers=identifiers):
                with self.assertRaises(ValueError):
                    build_stale_filter(identifiers)

    def test_missing_metadata_is_rejected(self):
        data = load_catalog()
        data["software"][0].pop("name")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "software.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required fields"):
                load_catalog(path)

    def test_invalid_identifier_is_rejected(self):
        data = load_catalog()
        data["software"][0]["id"] = "Not A Slug"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "software.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid id"):
                load_catalog(path)


if __name__ == "__main__":
    unittest.main()
