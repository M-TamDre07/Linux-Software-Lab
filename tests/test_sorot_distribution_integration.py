import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOROT_ROOT = ROOT / "apps" / "sorot"
RELEASES = SOROT_ROOT / "releases"


class SorotDistributionIntegrationTests(unittest.TestCase):
    def test_release_index_matches_version_manifests_and_real_files(self):
        index = json.loads((RELEASES / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["product"], "Sorot")
        self.assertTrue(index["versions"])

        indexed_versions = [item["version"] for item in index["versions"]]
        self.assertEqual(len(indexed_versions), len(set(indexed_versions)))

        for entry in index["versions"]:
            version = entry["version"]
            release_dir = RELEASES / version
            manifest = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], version)
            self.assertEqual(manifest["product"], "Sorot")
            self.assertEqual(manifest["status"], entry["status"])
            self.assertEqual(manifest["channel"], entry["channel"])

            artifact_formats = []
            checksums = {}
            for line in (release_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
                if line.strip():
                    digest, filename = line.split("  ", 1)
                    checksums[filename] = digest

            for artifact in manifest["artifacts"]:
                artifact_formats.append(artifact["format"])
                path = release_dir / artifact["file"]
                self.assertTrue(path.is_file(), f"Missing real artifact: {path}")
                actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(actual_sha, artifact["sha256"], artifact["file"])
                self.assertEqual(actual_sha, checksums.get(artifact["file"]), artifact["file"])

            self.assertEqual(set(artifact_formats), set(entry["formats"]))
            self.assertEqual(set(checksums), {artifact["file"] for artifact in manifest["artifacts"]})

    def test_website_distribution_index_points_to_immutable_release_manifests(self):
        data = json.loads((PUBLIC / "data" / "distribution-index.json").read_text(encoding="utf-8"))
        index = json.loads((RELEASES / "index.json").read_text(encoding="utf-8"))
        website_product = next(item for item in data["products"] if item["id"] == "sorot")
        website_manifests = {item["version"]: item["url"] for item in website_product["manifests"]}
        indexed_versions = {item["version"] for item in index["versions"]}
        self.assertEqual(set(website_manifests), indexed_versions)

        for version, url in website_manifests.items():
            expected_suffix = f"/apps/sorot/releases/{version}/release.json"
            self.assertTrue(url.endswith(expected_suffix))
            manifest_path = RELEASES / version / "release.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], version)
            self.assertEqual(manifest["product"], "Sorot")
            self.assertEqual(manifest["status"], next(item for item in index["versions"] if item["version"] == version)["status"])


    def test_arch_is_marked_planned_until_a_real_package_exists(self):
        index = json.loads((RELEASES / "index.json").read_text(encoding="utf-8"))
        web_data = json.loads((PUBLIC / "data" / "distribution-index.json").read_text(encoding="utf-8"))
        arch = next(item for item in web_data["distributions"] if item["id"] == "arch")
        self.assertEqual(arch["package_format"], "pkg.tar.zst")
        sorot = next(item for item in web_data["products"] if item["id"] == "sorot")
        planned = next(item for item in sorot["planned_targets"] if item["distribution_id"] == "arch")
        self.assertEqual(planned["version"], index["planned_targets"][0]["version"])
        self.assertEqual(planned["status"], "planned")

        all_formats = {
            artifact["format"]
            for item in index["versions"]
            for artifact in json.loads((RELEASES / item["version"] / "release.json").read_text(encoding="utf-8"))["artifacts"]
        }
        self.assertNotIn("pkg.tar.zst", all_formats)
        legacy_planned = next(item for item in index["planned_targets"] if item["distribution"] == "Arch Linux")
        self.assertEqual(legacy_planned["version"], index["planned_targets"][0]["version"])
        self.assertEqual(legacy_planned["status"], "planned")

    def test_public_distribution_index_is_generated_from_the_release_index(self):
        script = ROOT / "scripts" / "sync_distribution_index.py"
        self.assertTrue(script.is_file())
        result = subprocess.run(
            ["python", str(script), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


    def test_sorot_page_has_distribution_selector_and_terminal_helper(self):
        page = (PUBLIC / "software" / "sorot.html").read_text(encoding="utf-8")
        script = (PUBLIC / "assets" / "js" / "sorot-downloads.js").read_text(encoding="utf-8")
        self.assertIn('id="sorotDistro"', page)
        self.assertIn('data-download-data="/data/distribution-index.json"', page)
        self.assertIn('/assets/js/sorot-downloads.js', page)
        distribution_index = json.loads((PUBLIC / "data" / "distribution-index.json").read_text(encoding="utf-8"))
        self.assertIn("browser", distribution_index["detection_policy"])
        self.assertIn("distribution-index.json", script)
        self.assertIn("apps/sorot/releases/index.json", script)
        self.assertIn("python-wheel", script)
        self.assertIn("trustedManifestURL", script)
        self.assertNotIn("sorot-downloads.json", page + script)
        self.assertIn("availability", script)
        # Every visible install CTA must go through the distro-aware selector.
        self.assertIn('href="#downloads">Pilih format yang sesuai dengan distro', page)
        self.assertNotIn(
            'href="https://raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main/apps/sorot/releases/0.5.0/sorot_0.5.0_all.deb">Unduh Sorot',
            page,
        )
        self.assertIn('id="downloads" data-download-data="/data/distribution-index.json"', page)
        self.assertIn("BUKAN", (PUBLIC / "assets" / "images" / "sorot-preview.svg").read_text(encoding="utf-8"))

    def test_terminal_helper_checks_os_release_manifest_and_checksum(self):
        helper = SOROT_ROOT / "install.sh"
        source = helper.read_text(encoding="utf-8")
        self.assertIn("/etc/os-release", source)
        self.assertIn("release.json", source)
        self.assertIn("sha256sum", source)
        self.assertIn("pacman -U", source)
        self.assertIn('"x86_64": {"x86_64", "amd64"}', source)
        self.assertIn("No .pkg.tar.zst artifact is published", source)
        if shutil.which("bash"):
            syntax = subprocess.run(["bash", "-n", str(helper)], capture_output=True, text=True, check=False)
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            help_result = subprocess.run(["bash", str(helper), "--help"], capture_output=True, text=True, check=False)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("--detect", help_result.stdout)
            self.assertIn("--list", help_result.stdout)
        if shutil.which("node"):
            js_check = subprocess.run(
                ["node", "--check", str(PUBLIC / "assets" / "js" / "sorot-downloads.js")],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(js_check.returncode, 0, js_check.stderr)

    def test_product_catalogue_uses_the_shared_card_renderer_and_styles(self):
        catalogue = (PUBLIC / "software" / "index.html").read_text(encoding="utf-8")
        renderer = (PUBLIC / "assets" / "js" / "site.js").read_text(encoding="utf-8")
        styles = (PUBLIC / "assets" / "css" / "experience.css").read_text(encoding="utf-8")
        standard = (ROOT / "docs" / "PRODUCT_UI_STANDARD.md").read_text(encoding="utf-8")
        self.assertIn('id="softwareGrid"', catalogue)
        self.assertIn("const cardMarkup = (app, index) =>", renderer)
        self.assertIn("class=\"software-card\"", renderer)
        self.assertIn(".software-card", styles)
        self.assertIn(".software-preview", styles)
        self.assertIn("cardMarkup()", standard)

        self.assertIn("PRODUCT_UI_STANDARD.md", (ROOT / "docs" / "ADDING_SOFTWARE.md").read_text(encoding="utf-8"))
        detail_pages = sorted(path for path in (PUBLIC / "software").glob("*.html") if path.name != "index.html")
        self.assertTrue(detail_pages, "At least one product detail page must exist.")
        for path in detail_pages:
            with self.subTest(page=path.name):
                page = path.read_text(encoding="utf-8")
                self.assertIn('/assets/css/experience.css', page)
                self.assertIn('class="container detail-layout"', page)
                self.assertIn('class="detail-art"', page)

    def test_paketscope_terminal_guidance_distinguishes_source_mode_from_release(self):
        page = (PUBLIC / "software" / "paketscope.html").read_text(encoding="utf-8")
        readme = (ROOT / "apps" / "paketscope" / "README.md").read_text(encoding="utf-8")
        self.assertIn("python -m paketscope", page)
        self.assertIn("bukan instalasi rilis publik", page.lower())
        self.assertIn("python -m pip install -e", readme)
        self.assertIn("does not currently publish a versioned", readme)


if __name__ == "__main__":
    unittest.main()
