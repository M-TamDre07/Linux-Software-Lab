import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_supabase_catalog import load_catalog, to_record


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
