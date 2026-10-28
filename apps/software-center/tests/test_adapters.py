import unittest

from lsl_center.adapters import (
    adapter_for_family,
    enabled_adapter_for_family,
    registered_adapters,
)


class AdapterRegistryTests(unittest.TestCase):
    def test_debian_adapter_is_the_only_enabled_native_installer(self):
        enabled = [adapter.family for adapter in registered_adapters() if adapter.enabled]
        self.assertEqual(enabled, ["debian-family"])
        self.assertEqual(enabled_adapter_for_family("debian-family").command, "apt-get")

    def test_arch_is_detected_but_installation_stays_disabled(self):
        adapter = adapter_for_family("arch-family")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.command, "pacman")
        self.assertFalse(adapter.enabled)
        self.assertEqual(adapter.status, "detected-only")
        self.assertIsNone(enabled_adapter_for_family("arch-family"))

    def test_fedora_is_detected_but_installation_stays_disabled(self):
        adapter = adapter_for_family("fedora-family")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.command, "dnf")
        self.assertFalse(adapter.enabled)
        self.assertIsNone(enabled_adapter_for_family("fedora-family"))

    def test_unknown_family_has_no_adapter(self):
        self.assertIsNone(adapter_for_family("ign-26"))
        self.assertIsNone(enabled_adapter_for_family("ign-26"))

    def test_registered_families_are_deterministic(self):
        self.assertEqual(
            [adapter.family for adapter in registered_adapters()],
            ["arch-family", "debian-family", "fedora-family", "suse-family"],
        )


if __name__ == "__main__":
    unittest.main()
