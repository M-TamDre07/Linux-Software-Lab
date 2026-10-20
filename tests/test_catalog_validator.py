import copy
import tempfile
import unittest
from pathlib import Path

from scripts.validate_catalog import validate_data


class CatalogValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "software").mkdir()
        (self.root / "assets" / "images").mkdir(parents=True)
        (self.root / "software" / "demo.html").write_text("<html></html>", encoding="utf-8")
        (self.root / "assets" / "images" / "demo-icon.svg").write_text("<svg/>", encoding="utf-8")
        (self.root / "assets" / "images" / "demo-preview.svg").write_text("<svg/>", encoding="utf-8")
        self.data = {
            "schemaVersion": 2,
            "catalog": {
                "name": "Test catalog",
                "description": "Test catalog fixture",
                "searchMode": "client-side",
                "pageSize": 12,
                "updatedAt": "2026-10-20",
            },
            "software": [{
                "id": "demo",
                "slug": "demo",
                "name": "Demo",
                "version": "1.0",
                "summary": "Small test entry",
                "description": "Test application used to check the validator.",
                "category": "Testing",
                "status": "testing",
                "type": "desktop",
                "platforms": ["Linux"],
                "tags": ["Python"],
                "keywords": ["catalog search"],
                "features": ["Search"],
                "detailUrl": "/software/demo.html",
                "sourceUrl": "https://github.com/example/demo",
                "releaseUrl": "",
                "icon": "package",
                "iconImage": "/assets/images/demo-icon.svg",
                "previewImage": "/assets/images/demo-preview.svg",
                "previewAlt": "Concept preview of the demo application.",
                "updatedAt": "2026-10-20",
            }],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_catalog_passes(self):
        self.assertEqual(validate_data(self.data, self.root), [])

    def test_duplicate_ids_and_slugs_are_rejected(self):
        second = copy.deepcopy(self.data["software"][0])
        second["name"] = "Second demo"
        self.data["software"].append(second)
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("duplicate id" in error for error in errors))
        self.assertTrue(any("duplicate slug" in error for error in errors))

    def test_missing_local_preview_is_rejected(self):
        self.data["software"][0]["previewImage"] = "/assets/images/not-there.svg"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("missing local file" in error for error in errors))

    def test_http_source_link_is_rejected(self):
        self.data["software"][0]["sourceUrl"] = "http://example.com/source"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("HTTPS URL" in error for error in errors))

    def test_release_link_requires_released_status(self):
        self.data["software"][0]["releaseUrl"] = "https://example.com/download"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("only be shown for status 'released'" in error for error in errors))

    def test_unsafe_detail_path_is_rejected(self):
        self.data["software"][0]["detailUrl"] = "/software/../secret.html"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("unsafe path" in error for error in errors))

    def test_unknown_schema_version_is_rejected(self):
        self.data["schemaVersion"] = 1
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("schemaVersion must be 2" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
