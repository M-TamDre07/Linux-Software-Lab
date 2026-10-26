import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "schemas" / "distribution-manifest.schema.json"
ARCHITECTURE_PATH = ROOT / "docs" / "LAUNCHER_AND_DISTRIBUTION_ARCHITECTURE.md"
README_PATH = ROOT / "docs" / "ADDING_SOFTWARE.md"
SOROT_MANIFEST = ROOT / "apps" / "sorot" / "releases" / "0.5.0" / "release.json"


class DistributionArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
        self.artifact_rule = self.schema["$defs"]["artifact"]
        self.properties = self.artifact_rule["properties"]

    def test_schema_accepts_current_sorot_archive_without_mutating_it(self):
        release = json.loads(SOROT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(release["schema_version"], 1)
        self.assertEqual(release["product"], "Sorot")
        self.assertIn(release["status"], self.schema["properties"]["status"]["enum"])
        allowed_kinds = set(self.properties["kind"]["enum"])
        allowed_formats = set(self.properties["format"]["enum"])
        allowed_architectures = set(self.properties["architecture"]["enum"])

        for artifact in release["artifacts"]:
            with self.subTest(file=artifact["file"]):
                self.assertIn(artifact["kind"], allowed_kinds)
                self.assertIn(artifact["format"], allowed_formats)
                self.assertRegex(artifact["sha256"], r"^[a-f0-9]{64}$")
                self.assertEqual(len(artifact["sha256"]), 64)
                if "architecture" in artifact:
                    self.assertIn(artifact["architecture"], allowed_architectures)

    def test_installer_commands_cannot_be_supplied_by_catalogue_metadata(self):
        self.assertNotIn("install_command", self.properties)
        self.assertNotIn("shell_command", self.properties)
        self.assertIn("installer derives package-manager invocations", self.schema["description"])
        self.assertIn("Never allow a catalog field to supply an arbitrary shell command", self.architecture)
        self.assertIn("argument arrays", self.architecture)

    def test_supported_package_families_and_flatpak_are_distinguished(self):
        formats = set(self.properties["format"]["enum"])
        self.assertTrue({"deb", "rpm", "pkg.tar.zst", "flatpak", "flatpakref", "AppImage", "tar.gz", "zip"} <= formats)
        self.assertIn("Flatpak tetap menjadi salah satu format", self.architecture)
        self.assertIn("native packages plus optional Flatpak delivery", self.architecture)
        index = json.loads((ROOT / "apps" / "sorot" / "releases" / "index.json").read_text(encoding="utf-8"))
        arch_target = next(x for x in index["planned_targets"] if x["distribution"] == "Arch Linux")
        self.assertEqual(arch_target["status"], "planned")
        self.assertEqual(arch_target["version"], "0.6.0")

    def test_shared_guide_is_linked_from_add_software_checklist(self):
        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn("LAUNCHER_AND_DISTRIBUTION_ARCHITECTURE.md", readme)
        self.assertIn("PRODUCT_UI_STANDARD.md", readme)
        self.assertIn("schemas/distribution-manifest.schema.json", readme)

    def test_architecture_keeps_gui_and_cli_on_the_same_service_contract(self):
        self.assertIn("GUI and CLI must call the same metadata", self.architecture)
        self.assertIn("same registry, manifest schema, distro detection", self.architecture)
        self.assertIn("The final product name can be selected separately", self.architecture)
        self.assertIn("The launcher itself must be packaged and tested", self.architecture)


if __name__ == "__main__":
    unittest.main()
