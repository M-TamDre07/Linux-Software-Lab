from __future__ import annotations

import unittest

from lsl_center.adapters import (
    adapter_for_family,
    enabled_adapter_for_family,
    registered_adapters,
)
from lsl_center.distro import artifact_compatibility
from lsl_center.models import Artifact, SystemProfile


def profile(family: str, manager: str | None, *, pkexec: str | None = "/usr/bin/pkexec") -> SystemProfile:
    return SystemProfile(
        distro_id=family,
        pretty_name=family,
        version_id="",
        family=family,
        architecture="x86_64",
        package_manager=manager,
        package_manager_path=f"/usr/bin/{manager}" if manager else None,
        pkexec_path=pkexec,
        flatpak_path=None,
    )


def artifact(fmt: str, kind: str, *, arch: str = "x86_64") -> Artifact:
    return Artifact(
        product_id="example-app",
        product_name="Example App",
        version="1.0.0",
        channel="stable",
        release_status="released",
        file=f"example-1.0.0.{fmt.replace('.', '-')}",
        kind=kind,
        format=fmt,
        architecture=arch,
        sha256="a" * 64,
        url="https://example.invalid/artifact",
        manifest_url="https://example.invalid/release.json",
        checksums_url="https://example.invalid/SHA256SUMS",
    )


class AdapterRegistryTests(unittest.TestCase):
    def test_registry_has_deterministic_family_order(self) -> None:
        families = tuple(item.family for item in registered_adapters())
        self.assertEqual(families, ("arch-family", "debian-family", "fedora-family", "suse-family"))

    def test_only_debian_adapter_is_enabled(self) -> None:
        self.assertEqual(enabled_adapter_for_family("debian-family").command, "apt-get")
        for family in ("arch-family", "fedora-family", "suse-family", "unknown"):
            with self.subTest(family=family):
                self.assertIsNone(enabled_adapter_for_family(family))

    def test_arch_and_fedora_are_detected_but_installation_stays_disabled(self) -> None:
        cases = (
            ("arch-family", "pacman", artifact("pkg.tar.zst", "arch-package"), "Arch installation remains disabled"),
            ("fedora-family", "dnf", artifact("rpm", "rpm-package"), "Fedora/RPM installation remains disabled"),
        )
        for family, manager, package, expected in cases:
            with self.subTest(family=family):
                allowed, reason = artifact_compatibility(package, profile(family, manager))
                self.assertFalse(allowed)
                self.assertIn(expected, reason)

    def test_debian_adapter_allows_matching_deb_only_with_polkit(self) -> None:
        allowed, reason = artifact_compatibility(
            artifact("deb", "debian-package"),
            profile("debian-family", "apt-get"),
        )
        self.assertTrue(allowed)
        self.assertIn("apt-get", reason)

        allowed, reason = artifact_compatibility(
            artifact("deb", "debian-package"),
            profile("debian-family", "apt-get", pkexec=None),
        )
        self.assertFalse(allowed)
        self.assertIn("Polkit", reason)

    def test_package_format_cannot_cross_distribution_adapter(self) -> None:
        allowed, reason = artifact_compatibility(
            artifact("rpm", "rpm-package"),
            profile("debian-family", "apt-get"),
        )
        self.assertFalse(allowed)
        self.assertIn("Format rpm", reason)

    def test_unknown_distribution_family_fails_closed(self) -> None:
        allowed, reason = artifact_compatibility(
            artifact("deb", "debian-package"),
            profile("unknown", None),
        )
        self.assertFalse(allowed)
        self.assertIn("Tidak ada adapter", reason)


if __name__ == "__main__":
    unittest.main()
