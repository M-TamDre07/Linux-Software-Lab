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

    def test_website_download_data_matches_immutable_release_manifest(self):
        data = json.loads((PUBLIC / "data" / "sorot-downloads.json").read_text(encoding="utf-8"))
        index = json.loads((RELEASES / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["product"], "Sorot")
        website_versions = {item["version"]: item for item in data["versions"]}
        index_versions = {item["version"] for item in index["versions"]}
        self.assertEqual(set(website_versions), index_versions)

        for version, web_release in website_versions.items():
            manifest = json.loads((RELEASES / version / "release.json").read_text(encoding="utf-8"))
            self.assertEqual(web_release["status"], manifest["status"])
            self.assertEqual(web_release["channel"], manifest["channel"])
            web_artifacts = {item["file"]: item for item in web_release["artifacts"]}
            manifest_artifacts = {item["file"]: item for item in manifest["artifacts"]}
            self.assertEqual(set(web_artifacts), set(manifest_artifacts))
            for filename, manifest_artifact in manifest_artifacts.items():
                web_artifact = web_artifacts[filename]
                self.assertEqual(web_artifact["format"], manifest_artifact["format"])
                self.assertEqual(web_artifact["kind"], manifest_artifact["kind"])
                self.assertEqual(web_artifact["sha256"], manifest_artifact["sha256"])
                self.assertTrue(web_artifact["url"].endswith("/" + version + "/" + filename))

    def test_arch_is_marked_planned_until_a_real_package_exists(self):
        index = json.loads((RELEASES / "index.json").read_text(encoding="utf-8"))
        web_data = json.loads((PUBLIC / "data" / "sorot-downloads.json").read_text(encoding="utf-8"))
        arch = next(item for item in web_data["distributions"] if item["id"] == "arch")
        self.assertEqual(arch["status"], "planned")
        self.assertEqual(arch["targetVersion"], "0.6.0")
        self.assertEqual(arch["packageFormat"], "pkg.tar.zst")

        all_formats = {
            artifact["format"]
            for item in index["versions"]
            for artifact in json.loads((RELEASES / item["version"] / "release.json").read_text(encoding="utf-8"))["artifacts"]
        }
        self.assertNotIn("pkg.tar.zst", all_formats)
        planned = next(item for item in index["planned_targets"] if item["distribution"] == "Arch Linux")
        self.assertEqual(planned["version"], "0.6.0")
        self.assertEqual(planned["status"], "planned")

    def test_sorot_page_has_distribution_selector_and_terminal_helper(self):
        page = (PUBLIC / "software" / "sorot.html").read_text(encoding="utf-8")
        script = (PUBLIC / "assets" / "js" / "sorot-downloads.js").read_text(encoding="utf-8")
        self.assertIn('id="sorotDistro"', page)
        self.assertIn('data-download-data="/data/sorot-downloads.json"', page)
        self.assertIn('/assets/js/sorot-downloads.js', page)
        self.assertIn("Browsers do not reliably expose", json.dumps(json.loads((PUBLIC / "data" / "sorot-downloads.json").read_text(encoding="utf-8"))))
        self.assertIn("distro.status === 'available' && format === distro.packageFormat", script)
        self.assertIn("distro.status === 'available' && artifact.format === distro.packageFormat", script)
        self.assertIn("BUKAN", (PUBLIC / "assets" / "images" / "sorot-preview.svg").read_text(encoding="utf-8"))

    def test_terminal_helper_checks_os_release_manifest_and_checksum(self):
        helper = SOROT_ROOT / "install.sh"
        source = helper.read_text(encoding="utf-8")
        self.assertIn("/etc/os-release", source)
        self.assertIn("release.json", source)
        self.assertIn("sha256sum", source)
        self.assertIn("pacman -U", source)
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

        for filename in ("sorot.html", "paketscope.html"):
            page = (PUBLIC / "software" / filename).read_text(encoding="utf-8")
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
