from __future__ import annotations

import hashlib
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
    validate_distribution_index,
)
from lsl_center.cli import main
from lsl_center.distro import (
    architecture_matches,
    artifact_compatibility,
    canonical_architecture,
    detect_system_profile,
)
from lsl_center.installer import (
    InstallError,
    _removal_detected,
    _same_preview_plan,
    validate_artifact_for_download,
    validate_release_metadata,
)
from lsl_center.integrations import LOCAL_INTEGRATIONS, executable_for, integration_for
from lsl_center.models import InstallPreview, SystemProfile
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


def bundled_manifest_for_url(url: str, *_args: object, **_kwargs: object) -> bytes:
    """Return the local immutable manifest matching the version in a trusted test URL."""
    version = url.rstrip("/").rsplit("/", 2)[-2]
    manifest_path = DATA_DIR / "manifests" / "sorot" / version / "release.json"
    return manifest_path.read_bytes()


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

    def test_missing_os_release_still_recognises_linux_but_disables_unknown_family_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = detect_system_profile(
                Path(temp) / "missing-os-release",
                machine="x86_64",
                which=lambda _command: None,
                os_name="Linux",
            )
        self.assertTrue(profile.is_linux)
        self.assertEqual(profile.family, "unknown")
        self.assertEqual(profile.distro_id, "unknown")
        self.assertEqual(profile.pretty_name, "Linux (distribution unknown)")
        self.assertIsNone(profile.package_manager_path)

        app = CatalogService(data_dir=DATA_DIR).load().find("sorot")
        assert app is not None
        artifact = next(item for item in app.artifacts if item.format == "deb")
        compatible, message = artifact_compatibility(artifact, profile)
        self.assertFalse(compatible)
        self.assertIn("Debian/Ubuntu", message)

    def test_non_linux_host_is_not_misidentified_as_linux_from_os_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os_release = Path(temp) / "os-release"
            os_release.write_text('ID=ubuntu\\nPRETTY_NAME="Ubuntu fixture"\\n', encoding="utf-8")
            profile = detect_system_profile(
                os_release,
                machine="x86_64",
                which=lambda _command: "/usr/bin/fake",
                os_name="Windows",
            )
        self.assertFalse(profile.is_linux)
        self.assertEqual(profile.family, "unknown")
        self.assertEqual(profile.pretty_name, "Windows (distribution detection unavailable)")

        app = CatalogService(data_dir=DATA_DIR).load().find("sorot")
        assert app is not None
        artifact = next(item for item in app.artifacts if item.format == "deb")
        compatible, message = artifact_compatibility(artifact, profile)
        self.assertFalse(compatible)
        self.assertIn("hanya mendukung sistem Linux", message)

    def test_distribution_family_hints_cover_fedora_and_suse_without_guessing_unknowns(self) -> None:
        fixtures = (
            ('ID=fedora\nPRETTY_NAME="Fedora Linux"\n', "fedora-family"),
            ('ID=opensuse-tumbleweed\nPRETTY_NAME="openSUSE Tumbleweed"\n', "suse-family"),
            ('ID=customlinux\nID_LIKE="debian"\nPRETTY_NAME="Custom Linux"\n', "debian-family"),
            ('ID=customlinux\nPRETTY_NAME="Custom Linux"\n', "unknown"),
        )
        for content, expected in fixtures:
            with self.subTest(expected=expected, content=content):
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / "os-release"
                    path.write_text(content, encoding="utf-8")
                    profile = detect_system_profile(path, machine="x86_64", which=lambda _name: None, os_name="Linux")
                self.assertEqual(profile.family, expected)
                self.assertTrue(profile.is_linux)

    def test_architecture_aliases_match_without_accepting_other_architectures(self) -> None:
        self.assertEqual(canonical_architecture("amd64"), "x86_64")
        self.assertEqual(canonical_architecture("arm64"), "aarch64")
        self.assertTrue(architecture_matches("all", "x86_64"))
        self.assertTrue(architecture_matches("amd64", "x86_64"))
        self.assertTrue(architecture_matches("aarch64", "arm64"))
        self.assertFalse(architecture_matches("aarch64", "x86_64"))


class LocalIntegrationRegistryTests(unittest.TestCase):
    def test_existing_apps_use_reviewed_fixed_executable_candidates(self) -> None:
        self.assertEqual(
            LOCAL_INTEGRATIONS,
            (("paketscope", ("paketscope",)), ("sorot", ("sorot",))),
        )
        self.assertEqual(integration_for("paketscope"), ("paketscope", ("paketscope",)))
        self.assertEqual(integration_for("sorot"), ("sorot", ("sorot",)))

    def test_known_app_resolves_only_its_registered_executable(self) -> None:
        looked_up: list[str] = []

        def lookup(command: str) -> str | None:
            looked_up.append(command)
            return f"/usr/bin/{command}" if command == "sorot" else None

        self.assertEqual(executable_for("sorot", which=lookup), "/usr/bin/sorot")
        self.assertEqual(looked_up, ["sorot"])
        self.assertIsNotNone(integration_for("SOROT"))

    def test_unknown_catalog_item_cannot_choose_an_arbitrary_command(self) -> None:
        looked_up: list[str] = []

        def lookup(command: str) -> str:
            looked_up.append(command)
            return f"/usr/bin/{command}"

        self.assertIsNone(executable_for("unregistered-app", which=lookup))
        self.assertEqual(looked_up, [])

    def test_malformed_ids_fail_closed(self) -> None:
        for application_id in ("../apt", "sudo apt", "sorot;sh", ""):
            with self.subTest(application_id=application_id):
                self.assertIsNone(integration_for(application_id))
                self.assertIsNone(executable_for(application_id, which=lambda _name: "/bin/true"))


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CatalogService(data_dir=DATA_DIR)
        self.snapshot = self.service.load()

    def test_offline_catalog_loads_products_from_the_bundled_snapshot(self) -> None:
        self.assertEqual({app.id for app in self.snapshot.applications}, {"paketscope", "sorot"})
        self.assertEqual(self.snapshot.data_source, "bundled")
        self.assertTrue(self.snapshot.updated_at)

    def test_only_manifest_indexed_sorot_artifacts_are_available(self) -> None:
        sorot = self.snapshot.find("sorot")
        paketscope = self.snapshot.find("paketscope")
        self.assertIsNotNone(sorot)
        self.assertIsNotNone(paketscope)
        assert sorot is not None and paketscope is not None
        release_index = json.loads(
            (REPO_ROOT / "apps" / "sorot" / "releases" / "index.json").read_text(encoding="utf-8")
        )
        expected_artifacts = {
            (version["version"], artifact["format"])
            for version in release_index["versions"]
            for artifact in json.loads(
                (REPO_ROOT / "apps" / "sorot" / "releases" / version["version"] / "release.json")
                .read_text(encoding="utf-8")
            )["artifacts"]
        }
        self.assertEqual(
            {(artifact.version, artifact.format) for artifact in sorot.artifacts},
            expected_artifacts,
        )
        self.assertEqual(paketscope.artifacts, ())
        self.assertTrue(any(
            target.distribution_id == "arch" and target.version == release_index["planned_targets"][0]["version"]
            for target in sorot.planned_targets
        ))

    def test_catalog_index_and_release_manifest_are_valid(self) -> None:
        catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
        index = json.loads((DATA_DIR / "distribution-index.json").read_text(encoding="utf-8"))
        validate_catalog_payload(catalog)
        validate_distribution_index(index)
        # CatalogService.load also parses and validates every referenced release manifest.
        release_index = json.loads(
            (REPO_ROOT / "apps" / "sorot" / "releases" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            len(self.snapshot.find("sorot").artifacts),
            sum(len(item["formats"]) for item in release_index["versions"]),
        )

    def test_each_app_record_contains_a_safe_website_detail_route(self) -> None:
        for app in self.snapshot.applications:
            self.assertRegex(app.detail_url, r"^/software/[a-z0-9-]+\.html$")
            self.assertNotIn("..", app.detail_url.split("/"))

    def test_bundled_metadata_and_assets_match_the_public_website_sources(self) -> None:
        self.assertEqual(
            (DATA_DIR / "catalog.json").read_bytes(),
            (REPO_ROOT / "public" / "data" / "software.json").read_bytes(),
        )
        self.assertEqual(
            (DATA_DIR / "distribution-index.json").read_bytes(),
            (REPO_ROOT / "public" / "data" / "distribution-index.json").read_bytes(),
        )
        for app_id in ("paketscope", "sorot"):
            self.assertEqual(
                (DATA_DIR / "assets" / f"{app_id}-icon.svg").read_bytes(),
                (REPO_ROOT / "public" / "assets" / "images" / f"{app_id}-icon.svg").read_bytes(),
            )
        bundled_manifest = DATA_DIR / "manifests" / "sorot" / "0.5.0" / "release.json"
        release_manifest = REPO_ROOT / "apps" / "sorot" / "releases" / "0.5.0" / "release.json"
        self.assertEqual(bundled_manifest.read_bytes(), release_manifest.read_bytes())

    def test_invalid_catalog_duplicate_id_is_rejected(self) -> None:
        catalog = json.loads((DATA_DIR / "catalog.json").read_text(encoding="utf-8"))
        catalog["software"].append(dict(catalog["software"][0]))
        with self.assertRaises(CatalogError):
            validate_catalog_payload(catalog)

    def test_distribution_index_rejects_a_foreign_manifest_url(self) -> None:
        data = json.loads((DATA_DIR / "distribution-index.json").read_text(encoding="utf-8"))
        data["products"][1]["manifests"][0]["url"] = "https://example.invalid/sorot/release.json"
        with self.assertRaises(CatalogError):
            validate_distribution_index(data)

    def test_refresh_activates_one_complete_snapshot(self) -> None:
        catalog_bytes = (DATA_DIR / "catalog.json").read_bytes()
        index_bytes = (DATA_DIR / "distribution-index.json").read_bytes()

        def fetch_metadata(url: str) -> bytes:
            if url.endswith("software.json"):
                return catalog_bytes
            if url.endswith("distribution-index.json"):
                return index_bytes
            raise AssertionError(f"Unexpected metadata URL: {url}")

        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            service = CatalogService(cache_dir=cache)
            with (
                patch("lsl_center.catalog._fetch_metadata", side_effect=fetch_metadata),
                patch("lsl_center.catalog._fetch_manifest", side_effect=bundled_manifest_for_url),
            ):
                refreshed = service.refresh()

            pointer = json.loads((cache / "active.json").read_text(encoding="utf-8"))
            snapshot_dir = cache / "snapshots" / pointer["snapshot"]
            manifest_path = snapshot_dir / "manifests" / "sorot" / "0.5.0" / "release.json"
            self.assertEqual(refreshed.data_source, "cache")
            self.assertEqual(len(refreshed.applications), 2)
            self.assertTrue((snapshot_dir / "catalog.json").is_file())
            self.assertTrue((snapshot_dir / "distribution-index.json").is_file())
            self.assertTrue(manifest_path.is_file())
            self.assertEqual(
                hashlib.sha256((snapshot_dir / "catalog.json").read_bytes()).hexdigest(),
                pointer["catalog_sha256"],
            )
            self.assertEqual(
                hashlib.sha256((snapshot_dir / "distribution-index.json").read_bytes()).hexdigest(),
                pointer["index_sha256"],
            )
            manifest_key = next(iter(pointer["manifest_sha256s"]))
            self.assertEqual(
                hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                pointer["manifest_sha256s"][manifest_key],
            )
            self.assertFalse((cache / "catalog.json").exists())
            self.assertFalse((cache / "distribution-index.json").exists())
            sorot = refreshed.find("sorot")
            self.assertIsNotNone(sorot)
            assert sorot is not None
            self.assertIsNotNone(sorot.icon_path)

    def test_failed_refresh_preserves_the_previous_active_snapshot(self) -> None:
        catalog_bytes = (DATA_DIR / "catalog.json").read_bytes()
        index_bytes = (DATA_DIR / "distribution-index.json").read_bytes()

        def valid_fetch(url: str) -> bytes:
            if url.endswith("software.json"):
                return catalog_bytes
            if url.endswith("distribution-index.json"):
                return index_bytes
            raise AssertionError(f"Unexpected metadata URL: {url}")

        def invalid_fetch(url: str) -> bytes:
            if url.endswith("software.json"):
                return catalog_bytes
            return b'{"schema_version": 0}'

        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            service = CatalogService(cache_dir=cache)
            with (
                patch("lsl_center.catalog._fetch_metadata", side_effect=valid_fetch),
                patch("lsl_center.catalog._fetch_manifest", side_effect=bundled_manifest_for_url),
            ):
                service.refresh()
            active_before = (cache / "active.json").read_bytes()

            with (
                patch("lsl_center.catalog._fetch_metadata", side_effect=invalid_fetch),
                self.assertRaises(CatalogError),
            ):
                service.refresh()

            self.assertEqual((cache / "active.json").read_bytes(), active_before)
            snapshot = CatalogService(cache_dir=cache).load()
            self.assertEqual(snapshot.data_source, "cache")
            self.assertEqual(len(snapshot.applications), 2)

    def test_corrupt_cache_snapshot_falls_back_to_the_bundled_catalog(self) -> None:
        catalog_bytes = (DATA_DIR / "catalog.json").read_bytes()
        index_bytes = (DATA_DIR / "distribution-index.json").read_bytes()

        def fetch(url: str) -> bytes:
            return catalog_bytes if url.endswith("software.json") else index_bytes

        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache"
            with (
                patch("lsl_center.catalog._fetch_metadata", side_effect=fetch),
                patch("lsl_center.catalog._fetch_manifest", side_effect=bundled_manifest_for_url),
            ):
                CatalogService(cache_dir=cache).refresh()
            pointer = json.loads((cache / "active.json").read_text(encoding="utf-8"))
            snapshot_dir = cache / "snapshots" / pointer["snapshot"]
            manifest_path = snapshot_dir / "manifests" / "sorot" / "0.5.0" / "release.json"
            manifest_path.write_text("{}", encoding="utf-8")

            fallback = CatalogService(cache_dir=cache).load()
            self.assertEqual(fallback.data_source, "bundled fallback (cache invalid)")
            self.assertEqual({app.id for app in fallback.applications}, {"paketscope", "sorot"})
            self.assertIsNotNone(fallback.find("sorot").icon_path)


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
        release_index = json.loads(
            (REPO_ROOT / "apps" / "sorot" / "releases" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(artifact.version, release_index["versions"][-1]["version"])

    def test_arch_profile_never_falls_back_to_deb(self) -> None:
        self.assertIsNone(select_artifact(self.sorot, arch_profile(), install_only=True))
        self.assertIsNone(
            select_artifact(self.sorot, arch_profile(), requested_format="deb")
        )

    def test_paketscope_is_not_advertised_as_installable_without_artifact(self) -> None:
        self.assertIsNone(select_artifact(self.paketscope, debian_profile(), install_only=True))
        self.assertIsNone(select_artifact(self.paketscope, debian_profile()))

    def test_sorot_arch_target_is_data_driven_and_not_an_installable_package(self) -> None:
        sorot = self.snapshot.find("sorot")
        assert sorot is not None
        targets = getattr(sorot, "planned_targets", ())
        self.assertTrue(any(
            getattr(target, "distribution_id", None) == "arch"
            and getattr(target, "version", None) == json.loads(
                (REPO_ROOT / "apps" / "sorot" / "releases" / "index.json").read_text(encoding="utf-8")
            )["planned_targets"][0]["version"]
            for target in targets
        ))
        self.assertIsNone(select_artifact(sorot, arch_profile(), install_only=True))

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

    def test_release_redirect_policy_rejects_nonstandard_ports_and_credentials(self) -> None:
        from lsl_center.installer import _validate_trusted_release_url

        with self.assertRaises(InstallError):
            _validate_trusted_release_url(
                "https://raw.githubusercontent.com:8443/M-TamDre07/Linux-Software-Lab/main/apps/sorot/releases/0.5.0/sorot_0.5.0_all.deb",
                self.artifact,
                self.artifact.file,
            )
        with self.assertRaises(InstallError):
            _validate_trusted_release_url(
                "https://user@raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main/apps/sorot/releases/0.5.0/sorot_0.5.0_all.deb",
                self.artifact,
                self.artifact.file,
            )

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

    def test_install_requires_the_same_package_plan_that_was_shown(self) -> None:
        package_path = Path("/tmp/sorot_0.5.0_all.deb")
        expected = InstallPreview(
            package_path=package_path,
            command=("/usr/bin/apt-get", "-s", "install", str(package_path)),
            output=(
                "Reading package lists...\n"
                "Inst sorot (0.5.0 local-deb [all])\n"
                "Conf sorot (0.5.0 local-deb [all])"
            ),
            package_manager="apt-get",
            removal_detected=False,
        )
        same_plan_with_progress_messages = replace(
            expected,
            output=(
                "Reading package lists... Done\n"
                "Building dependency tree... Done\n"
                "Inst sorot (0.5.0 local-deb [all])\n"
                "Conf sorot (0.5.0 local-deb [all])"
            ),
        )
        changed_plan = replace(
            expected,
            output=(
                "Inst another-package (1.0 repository [all])\n"
                "Conf another-package (1.0 repository [all])"
            ),
        )
        self.assertTrue(_same_preview_plan(expected, same_plan_with_progress_messages))
        self.assertFalse(_same_preview_plan(expected, changed_plan))


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
        self.assertEqual(
            sorot["website_url"],
            "https://linux-software-lab.vercel.app/software/sorot.html",
        )
        self.assertEqual(
            sorot["source_url"],
            "https://github.com/M-TamDre07/Linux-Software-Lab/tree/main/apps/sorot",
        )

    def test_install_command_on_arch_fails_closed_without_network(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["install", "sorot"], service=self.service, profile=arch_profile())
        self.assertEqual(code, 3)
        self.assertIn("Belum ada paket native", output.getvalue())

    def test_ecosystem_command_json_reports_links_limits_and_local_source(self) -> None:
        output = StringIO()
        with (
            redirect_stdout(output),
            patch("lsl_center.catalog._fetch_metadata", side_effect=AssertionError("must not use network")),
        ):
            code = main(["ecosystem", "--json"], service=self.service, profile=arch_profile())
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["source_of_truth"]["repository"],
            "https://github.com/M-TamDre07/Linux-Software-Lab",
        )
        self.assertEqual(
            payload["source_of_truth"]["launcher_portal"],
            "https://linux-software-lab.vercel.app/launcher/",
        )
        self.assertEqual(payload["local_catalog"]["entry_count"], 2)
        self.assertEqual(payload["local_catalog"]["source"], "bundled")
        self.assertEqual(payload["data_services"]["supabase_role"], "read-only catalogue mirror")
        self.assertEqual(payload["data_services"]["runtime_status"], "not checked by this local diagnostic")
        self.assertEqual(payload["system"]["family"], "arch-family")
        self.assertFalse(payload["installation"]["enabled_for_detected_system"])
        self.assertFalse(payload["installation"]["arch_enabled"])
        self.assertFalse(payload["installation"]["signed_release_metadata_available"])
        self.assertEqual(payload["local_integrations"]["reviewed_allowlist"], ["paketscope", "sorot"])

    def test_ecosystem_command_human_output_explains_integration_boundaries(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["ecosystem"], service=self.service, profile=debian_profile())
        self.assertEqual(code, 0)
        self.assertIn("https://linux-software-lab.vercel.app/launcher/", output.getvalue())
        self.assertIn("SHA-256 bukan tanda tangan penerbit", output.getvalue())
        self.assertIn("Adapter lain", output.getvalue())
        self.assertIn("Supabase", output.getvalue())
        self.assertIn("tidak melakukan probe jaringan", output.getvalue())

    def test_cli_version_flag_exits_without_loading_catalogue(self) -> None:
        output = StringIO()
        with (
            redirect_stdout(output),
            patch("lsl_center.catalog.CatalogService.load", side_effect=AssertionError("must not load catalog")),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["--version"], service=self.service, profile=arch_profile())
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("lsl", output.getvalue())
        self.assertIn("0.1.0", output.getvalue())

    def test_info_command_does_not_claim_paketscope_has_a_release_package(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["info", "paketscope"], service=self.service, profile=debian_profile())
        self.assertEqual(code, 0)
        self.assertIn("Belum ada paket/arsip rilis", output.getvalue())
        self.assertIn(
            "https://linux-software-lab.vercel.app/software/paketscope.html",
            output.getvalue(),
        )
        self.assertIn(
            "https://github.com/M-TamDre07/Linux-Software-Lab/tree/main/apps/paketscope",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
