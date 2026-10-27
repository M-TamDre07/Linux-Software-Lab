from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.scaffold_app import ScaffoldError, scaffold_application, validate_slug
from scripts.validate_app_manifest import validate_manifest, validate_manifest_file


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "application"


class ApplicationScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.apps_dir = Path(self.temp.name) / "apps"
        self.apps_dir.mkdir()
        self.catalog_path = ROOT / "public" / "data" / "software.json"
        self.catalog_before = self.catalog_path.read_bytes()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_slug_validation_rejects_paths_and_shell_or_sql_payloads(self) -> None:
        valid = ("sample-tool", "a1", "tool-2026")
        for slug in valid:
            with self.subTest(slug=slug):
                self.assertEqual(validate_slug(slug), slug)

        invalid = (
            "../secrets", "/tmp/demo", "Not-Lowercase", "two--hyphens",
            "-leading", "trailing-", "space tool", "tool;drop-table",
            "tool'--", "tool$(id)", "", "a" * 65,
        )
        for slug in invalid:
            with self.subTest(slug=slug):
                with self.assertRaises(ScaffoldError):
                    validate_slug(slug)

    def test_scaffold_contains_standard_layout_and_replaces_tokens(self) -> None:
        app_name = 'Demo `[Lab]` & Tools'
        description = "A [safe] app scaffold for local testing."
        target = scaffold_application(
            "demo-tool",
            app_name,
            description,
            apps_dir=self.apps_dir,
            template_dir=TEMPLATE,
            today=date(2026, 10, 27),
        )

        self.assertEqual(target, self.apps_dir / "demo-tool")
        required = (
            "README.md",
            "application.json",
            "application.schema.json",
            "CHANGELOG.md",
            "LICENSE-REQUIRED.md",
            ".gitignore",
            "src/README.md",
            "tests/unit/README.md",
            "tests/integration/README.md",
            "tests/security/README.md",
            "docs/ARCHITECTURE.md",
            "docs/DEVELOPMENT.md",
            "docs/SECURITY.md",
            "docs/RELEASES.md",
            "assets/icons/README.md",
            "assets/screenshots/README.md",
            "assets/fixtures/README.md",
            "packaging/README.md",
            "packaging/debian/README.md",
            "packaging/rpm/README.md",
            "packaging/arch/README.md",
            "packaging/flatpak/README.md",
            "packaging/appimage/README.md",
            "releases/README.md",
            "ci/README.md",
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((target / relative).is_file())

        all_text = []
        for path in target.rglob("*"):
            if path.is_file():
                all_text.append(path.read_text(encoding="utf-8"))
        merged = "\n".join(all_text)
        self.assertNotRegex(merged, r"\{\{[A-Z][A-Z0-9_]*\}\}")
        self.assertIn(r"Demo \`\[Lab\]\` & Tools", (target / "README.md").read_text(encoding="utf-8"))
        self.assertIn("2026-10-27", (target / "CHANGELOG.md").read_text(encoding="utf-8"))
        metadata = json.loads((target / "application.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["id"], "demo-tool")
        self.assertEqual(metadata["slug"], "demo-tool")
        self.assertEqual(metadata["name"], app_name)
        self.assertEqual(metadata["description"], description)
        self.assertEqual(metadata["lifecycle"], "planned")
        self.assertEqual(metadata["integrity"]["publisher_signature"], "not-implemented")
        schema = json.loads((target / "application.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(metadata), [])
        self.assertEqual(validate_manifest_file(target / "application.json"), [])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertIn("lifecycle", schema["required"])
        self.assertTrue((target / "LICENSE-REQUIRED.md").is_file())
        self.assertFalse(any(path.suffix.lower() in {".deb", ".rpm", ".flatpak", ".appimage"} for path in target.rglob("*")))

    def test_manifest_validator_rejects_unknown_fields_and_fake_release_state(self) -> None:
        baseline = json.loads((TEMPLATE / "application.json").read_text(encoding="utf-8"))
        baseline["id"] = "unsafe slug"
        self.assertTrue(validate_manifest(baseline))

        baseline = json.loads((TEMPLATE / "application.json").read_text(encoding="utf-8"))
        baseline["unexpected"] = "should be rejected"
        self.assertTrue(any("Field tidak dikenal" in error for error in validate_manifest(baseline)))

        baseline = json.loads((TEMPLATE / "application.json").read_text(encoding="utf-8"))
        baseline["lifecycle"] = "released"
        baseline["distribution"]["enabled_formats"] = ["deb"]
        baseline["distribution"]["release_manifest"] = "releases/1.0.0/release.json"
        baseline["integrity"]["sha256_checksums"] = "published"
        self.assertTrue(any("Manifest rilis yang dirujuk tidak ditemukan" in error for error in validate_manifest(baseline, base_dir=self.apps_dir)))

    def test_default_manifest_validator_checks_template_without_writing_sample_values(self) -> None:
        before = (TEMPLATE / "application.json").read_bytes()
        self.assertEqual(validate_manifest_file(TEMPLATE / "application.json", template=True), [])
        self.assertEqual((TEMPLATE / "application.json").read_bytes(), before)

    def test_scaffold_never_overwrites_existing_application(self) -> None:
        target = self.apps_dir / "existing-app"
        target.mkdir()
        sentinel = target / "README.md"
        sentinel.write_text("maintainer data", encoding="utf-8")

        with self.assertRaisesRegex(ScaffoldError, "sudah ada"):
            scaffold_application(
                "existing-app",
                "Existing",
                "Keep all existing files unchanged.",
                apps_dir=self.apps_dir,
                template_dir=TEMPLATE,
            )

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "maintainer data")
        self.assertEqual(list(self.apps_dir.iterdir()), [target])

    def test_invalid_human_fields_and_missing_template_fail_without_partial_target(self) -> None:
        invalid_fields = (
            ("bad-name", "Demo\nName", "Description"),
            ("bad-description", "Demo", "line one\nline two"),
            ("control", "Demo\x00Name", "Description"),
            ("too-long", "D" * 101, "Description"),
        )
        for slug, name, description in invalid_fields:
            with self.subTest(slug=slug):
                with self.assertRaises(ScaffoldError):
                    scaffold_application(
                        slug,
                        name,
                        description,
                        apps_dir=self.apps_dir,
                        template_dir=TEMPLATE,
                    )
        with self.assertRaises(ScaffoldError):
            scaffold_application(
                "missing-template",
                "Demo",
                "Description",
                apps_dir=self.apps_dir,
                template_dir=self.apps_dir / "not-a-template",
            )
        self.assertEqual(list(self.apps_dir.iterdir()), [])

    def test_scaffold_rejects_symlinked_template_files_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template = Path(temp_dir) / "template"
            shutil.copytree(TEMPLATE, template)
            outside = Path(temp_dir) / "outside.txt"
            outside.write_text("outside template root", encoding="utf-8")
            link = template / "src" / "linked-file.txt"
            try:
                link.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Symlinks are unavailable in this test environment: {exc}")

            with self.assertRaisesRegex(ScaffoldError, "symlink"):
                scaffold_application(
                    "symlink-check",
                    "Symlink Check",
                    "Reject untrusted symlinks in the application template.",
                    apps_dir=self.apps_dir,
                    template_dir=template,
                )

            self.assertFalse((self.apps_dir / "symlink-check").exists())
            self.assertEqual(list(self.apps_dir.iterdir()), [])

    def test_scaffold_does_not_mutate_canonical_catalogue(self) -> None:
        scaffold_application(
            "isolated-demo",
            "Isolated Demo",
            "Test the boundary between apps and the website catalogue.",
            apps_dir=self.apps_dir,
            template_dir=TEMPLATE,
        )
        self.assertEqual(self.catalog_path.read_bytes(), self.catalog_before)
        self.assertFalse((ROOT / "public" / "software" / "isolated-demo.html").exists())


if __name__ == "__main__":
    unittest.main()
