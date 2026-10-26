from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from lsl_center.catalog import (
    CatalogError,
    CatalogService,
    validate_catalog_payload,
    validate_download_payload,
)
from lsl_center.distro import (
    architecture_matches,
    canonical_architecture,
    detect_system_profile,
)
from lsl_center.installer import (
    InstallError,
    _removal_detected,
    build_install_command,
    validate_artifact_for_download,
    validate_release_metadata,
)
from lsl_center.models import SystemProfile
from lsl_center.cli import main
from lsl_center.selection import select_artifact, source_artifacts


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = APP_ROOT / "lsl_center" / "data"


def debian_profile() -> SystemProfile:
    return SystemProfile(
        distro_id="ubuntu",
        pretty_name="Ubuntu 24.04 LTS",
        version_id="24.04",
        family="debian-family",
        architecture="x86_64",
        package_manager="apt-get",
        package_manager_path="/usr/bin/apt-get",
        pkexec_path="/usr/bin/pkexec",
        flatpak_path=None,
    )


def arch_profile() -> SystemProfile:
    return SystemProfile(
        distro_id="endeavouros",
        pretty_name="EndeavourOS",
        version_id="",
        family="arch-family",
        architecture="x86_64",
        package_manager="pacman",
        package_manager_path="/usr/bin/pacman",
        pkexec_path="/usr/bin/pkexec",
        flatpak_path="/usr/bin/flatpak",
    )


class DistributionDetectionTests(unittest.TestCase):
    def test_detects_debian_family_from_os_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os_release = Path(temp) / "os-release"
            os_release.write_text(
                'NAME="Ubuntu"\nID=ubuntu\nID_LIKE="debian"\nPRETTY_NAME="Ubuntu 24.04 LTS"\nVERSION_ID="24.04"\n',
                encoding="utf-8",
            )
            profile = detect_system_profile(
                os_release,
                machine="x86_64",
                which=lambda command: f"/usr/bin/{command}",
            )
        self.assertEqual(profile.family, "debian-family")
        self.assertEqual(profile.distro_id, "ubuntu")
        self.assertEqual(profile.version_id, "24.04")
        self.assertEqual(profile.package_manager, "apt-get")

    def test_detects_arch_derivative_and_manager(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os_release = Path(temp) / "os-release"
            os_release.write_text(
                'NAME="EndeavourOS"\nID=endeavouros\nID_LIKE="arch"\n',
                encoding="utf-8",
            )
            profile = detect_system_profile(
                os_release,
                machine="amd64",
                which=lambda command: f"/usr/bin/{command}",
            )
        self.assertEqual(profile.family, "arch-family")
        self.assertEqual(profile.package_manager, "pacman")
        self.assertEqual(profile.architecture, "x86_64")

    def test_architecture_aliases_match_without_accepting_other_architectures(self) -> None:
        self.assertEqual(canonical_architecture("amd64"), "x86_64")
        self.assertEqual(canonical_architecture("arm64"), "aarch64")
        self.assertTrue(architecture_matches("all", "x86_64"))
        self.assertTrue(architecture_matches("amd64", "x86_64"))
        self.assertTrue(architecture_matches("aarch64", "arm64"))
        self.assertFalse(architecture_matches("aarch64", "x86_64"))


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CatalogService(data_dir=DATA_DIR)
        self.snapshot = self.service.load()

    def test_offline_catalog_loads_both_current_apps(self) -> None:
        self.assertEqual({app.id for app in self.snapshot.applications}, {"paketscope", "sorot"})
        self.assertEqual(self.snapshot.data_source, "bundled")
        self.assertTrue(self.snapshot.updated_at)

    def test_only_sorot_has_real_archived_downloads(self) -> None:
        sorot = self.snapshot.find("sorot")
        paketscope = self.snapshot.find("paketscope")
        self.assertIsNotNone(sorot)
        self.assertIsNotNone(paketscope)
        assert sorot is not None and paketscope is not None
        self.assertEqual(
            {(artifact.version, artifact.format) for artifact in sorot.artifacts},
            {("0.5.0", "deb"), ("0.5.0", "tar.gz"), ("0.5.0", "zip")},
        )
        self.assertEqual(paketscope.artifacts, ())

    def test_catalogue_and_download_data_are_valid(self) -> None:
        catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
        downloads = json.loads((DATA_DIR / "sorot-downloads.json").read_text(encoding="utf-8"))
        validate_catalog_payload(catalog)
        validate_download_payload(downloads)

    def test_invalid_catalog_duplicate_id_is_rejected(self) -> None:
        catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
        catalog["software"].append(dict(catalog["software"][0]))
        with self.assertRaises(CatalogError):
            validate_catalog_payload(catalog)

    def test_invalid_download_url_is_rejected(self) -> None:
        data = json.loads((DATA_DIR / "sorot-downloads.json").read_text(encoding="utf-8"))
        data["versions"][0]["artifacts"][0]["url"] = "https://example.invalid/sorot.deb"
        with self.assertRaises(CatalogError):
            validate_download_payload(data)

    def test_refresh_writes_cache_only_after_both_documents_validate(self) -> None:
        catalog_bytes = (DATA_DIR / "catalog.json").read_bytes()
        downloads_bytes = (DATA_DIR / "sorot-downloads.json").read_bytes()
        def fetch(url: str) -> bytes:
            return catalog_bytes if url.endswith("software.json") else downloads_bytes

        with tempfile.TemporaryDirectory() as temp:
            service = CatalogService(cache_dir=Path(temp) / "cache")
            with patch("lsl_center.catalog._fetch_metadata", side_effect=fetch):
                refreshed = service.refresh()
            self.assertEqual(refreshed.data_source, "cache")
            self.assertEqual(len(refreshed.applications), 2)
            self.assertTrue((Path(temp) / "cache" / "catalog.json").is_file())
            self.assertTrue((Path(temp) / "cache" / "sorot-downloads.json").is_file())
            self.assertIsNotNone(refreshed.find("sorot").icon_path)


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = CatalogService(data_dir=DATA_DIR).load()
        self.sorot = self.snapshot.find("sorot")
        self.paketscope = self.snapshot.find("paketscope")
        assert self.sorot is not None and self.paketscope is not None

    def test_debian_profile_selects_the_real_deb_for_install(self) -> None:
        artifact = select_artifact(self.sorot, debian_profile(), install_only=True)
        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertEqual(artifact.format, "deb")
        self.assertEqual(artifact.version, "0.5.0")

    def test_arch_profile_never_falls_back_to_deb(self) -> None:
        self.assertIsNone(select_artifact(self.sorot, arch_profile(), install_only=True))
        self.assertIsNone(
            select_artifact(self.sorot, arch_profile(), requested_format="deb")
        )

    def test_paketscope_is_not_advertised_as_installable_without_artifact(self) -> None:
        self.assertIsNone(select_artifact(self.paketscope, debian_profile(), install_only=True))
        self.assertIsNone(select_artifact(self.paketscope, debian_profile()))

    def test_source_archives_are_separate_from_native_install_artifacts(self) -> None:
        archives = source_artifacts(self.sorot)
        self.assertEqual({item.format for item in archives}, {"tar.gz", "zip"})
        self.assertTrue(all(item.is_source_archive for item in archives))
        self.assertIsNone(select_artifact(self.sorot, arch_profile(), install_only=True))


class InstallerIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        snapshot = CatalogService(data_dir=DATA_DIR).load()
        self.sorot = snapshot.find("sorot")
        assert self.sorot is not None
        self.artifact = next(item for item in self.sorot.artifacts if item.format == "deb")
        self.manifest_path = (
            REPO_ROOT / "apps" / "sorot" / "releases" / self.artifact.version / "release.json"
        )
        self.checksums_path = (
            REPO_ROOT / "apps" / "sorot" / "releases" / self.artifact.version / "SHA256SUMS"
        )

    def test_current_artifact_matches_release_manifest_and_checksums(self) -> None:
        validated = validate_release_metadata(
            self.artifact,
            self.manifest_path.read_bytes(),
            self.checksums_path.read_bytes(),
        )
        self.assertEqual(validated["version"], "0.5.0")

    def test_metadata_digest_tampering_is_rejected(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaises(InstallError):
            validate_release_metadata(
                self.artifact,
                json.dumps(manifest).encode("utf-8"),
                self.checksums_path.read_bytes(),
            )

    def test_foreign_download_host_is_rejected(self) -> None:
        hostile = replace(self.artifact, url="https://example.invalid/other.deb")
        with self.assertRaises(InstallError):
            validate_artifact_for_download(hostile)

    def test_package_command_is_an_argument_list_and_forbids_removals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / self.artifact.file
            package.write_bytes(b"test-only placeholder; never executed")
            with patch("lsl_center.installer.os.geteuid", return_value=1000):
                from lsl_center.installer import build_install_command
                command = build_install_command(self.artifact, package, debian_profile())
        self.assertEqual(command[0], "/usr/bin/pkexec")
        self.assertIn("--no-remove", command)
        self.assertIn("--no-install-recommends", command)
        self.assertIn("--yes", command)
        self.assertNotIn("shell", command)
        self.assertNotIn("autoremove", command)

    def test_removal_detection_is_conservative(self) -> None:
        self.assertTrue(_removal_detected("Remv example-pkg [1.0]"))
        self.assertTrue(_removal_detected("The following packages will be REMOVED: libx"))
        self.assertFalse(_removal_detected("Inst sorot (0.5.0 local-deb [all])"))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CatalogService(data_dir=DATA_DIR)

    def test_json_list_command_is_machine_readable(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["list", "--json"], service=self.service, profile=arch_profile())
        self.assertEqual(code, 0)
        records = json.loads(output.getvalue())
        self.assertEqual({record["id"] for record in records}, {"paketscope", "sorot"})
        sorot = next(record for record in records if record["id"] == "sorot")
        self.assertEqual(sorot["available_artifacts"], [])

    def test_install_command_on_arch_fails_closed_without_network(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["install", "sorot"], service=self.service, profile=arch_profile())
        self.assertEqual(code, 3)
        self.assertIn("Belum ada paket native", output.getvalue())

    def test_info_command_does_not_claim_paketscope_has_a_release_package(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["info", "paketscope"], service=self.service, profile=debian_profile())
        self.assertEqual(code, 0)
        self.assertIn("Belum ada paket/arsip rilis", output.getvalue())


if __name__ == "__main__":
    unittest.main()
