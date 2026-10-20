import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_catalog import validate_data, validate_schema_contract


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


    def test_repository_schema_matches_runtime_validator(self):
        self.assertEqual(validate_schema_contract(), [])

    def test_malformed_schema_shapes_report_errors_without_crashing(self):
        canonical_schema_path = Path(__file__).resolve().parents[1] / "public" / "data" / "software.schema.json"
        schema = json.loads(canonical_schema_path.read_text(encoding="utf-8"))
        schema["required"] = None
        schema["properties"]["catalog"]["required"] = None
        schema["properties"]["software"]["items"]["required"] = None
        schema["properties"]["software"]["items"]["properties"]["status"]["enum"] = None
        schema["properties"]["software"]["items"]["properties"]["type"]["enum"] = None
        schema["properties"]["software"]["items"]["allOf"] = [
            {"if": {"properties": None}, "then": {"properties": None}}
        ]
        (self.root / "data" / "software.schema.json").write_text(
            json.dumps(schema), encoding="utf-8"
        )
        errors = validate_schema_contract(self.root)
        self.assertTrue(errors)

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

    def test_malformed_port_is_rejected(self):
        self.data["software"][0]["sourceUrl"] = "https://example.com:not-a-port/source"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("HTTPS URL" in error for error in errors))

    def test_release_link_requires_released_status(self):
        self.data["software"][0]["releaseUrl"] = "https://example.com/download"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("only be shown for status 'released'" in error for error in errors))

    def test_released_status_requires_release_url(self):
        self.data["software"][0]["status"] = "released"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("requires a verified HTTPS releaseUrl" in error for error in errors))

    def test_released_status_with_https_release_url_passes(self):
        self.data["software"][0]["status"] = "released"
        self.data["software"][0]["releaseUrl"] = "https://github.com/example/demo/releases/download/v1/demo.tar.gz"
        self.assertEqual(validate_data(self.data, self.root), [])

    def test_unsafe_detail_path_is_rejected(self):
        self.data["software"][0]["detailUrl"] = "/software/../secret.html"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("unsafe path" in error for error in errors))

    def test_detail_url_must_match_slug(self):
        self.data["software"][0]["detailUrl"] = "/software/some-other-app.html"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("detailUrl must be '/software/demo.html'" in error for error in errors))

    def test_unknown_schema_version_is_rejected(self):
        self.data["schemaVersion"] = 1
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("schemaVersion must be 2" in error for error in errors))

    def test_unknown_app_field_is_rejected(self):
        self.data["software"][0]["releaseNotes"] = "typo field"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("unknown field(s): releaseNotes" in error for error in errors))

    def test_wrong_field_types_report_errors_without_crashing(self):
        app = self.data["software"][0]
        app["summary"] = 123
        app["status"] = ["released"]
        app["type"] = {"desktop": True}
        app["updatedAt"] = None
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("'summary' is missing or has the wrong type" in error for error in errors))
        self.assertTrue(any("'status' is missing or has the wrong type" in error for error in errors))
        self.assertTrue(any("'type' is missing or has the wrong type" in error for error in errors))
        self.assertTrue(any("'updatedAt' is missing or has the wrong type" in error for error in errors))

    def test_unknown_catalog_field_is_rejected(self):
        self.data["catalog"]["pagSize"] = 12
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("Unknown catalog metadata field(s): pagSize" in error for error in errors))

    def test_path_that_escapes_through_symlink_is_rejected(self):
        outside = Path(self.temp.name).parent / "outside-preview.svg"
        outside.write_text("<svg/>", encoding="utf-8")
        link = self.root / "assets" / "images" / "external.svg"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            outside.unlink(missing_ok=True)
            self.skipTest("Symlink creation is unavailable on this platform")
        self.data["software"][0]["previewImage"] = "/assets/images/external.svg"
        errors = validate_data(self.data, self.root)
        self.assertTrue(any("resolves outside the website root" in error for error in errors))
        link.unlink(missing_ok=True)
        outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
