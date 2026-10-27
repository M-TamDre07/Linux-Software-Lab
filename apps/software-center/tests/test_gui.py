from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lsl_center.catalog import CatalogService
from lsl_center.gui import MainWindow
from lsl_center.models import SystemProfile
from lsl_center.selection import source_artifacts

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "lsl_center" / "data"


def profile(family: str) -> SystemProfile:
    if family == "debian-family":
        return SystemProfile(
            distro_id="ubuntu",
            pretty_name="Ubuntu test fixture",
            version_id="24.04",
            family=family,
            architecture="x86_64",
            package_manager="apt-get",
            package_manager_path="/usr/bin/apt-get",
            pkexec_path="/usr/bin/pkexec",
            flatpak_path=None,
        )
    return SystemProfile(
        distro_id="endeavouros",
        pretty_name="Arch-derived test fixture",
        version_id="",
        family="arch-family",
        architecture="x86_64",
        package_manager="pacman",
        package_manager_path="/usr/bin/pacman",
        pkexec_path="/usr/bin/pkexec",
        flatpak_path="/usr/bin/flatpak",
    )


class LauncherGuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_catalogue_renders_products_and_keeps_arch_fail_closed(self) -> None:
        window = MainWindow(
            service=CatalogService(data_dir=DATA_DIR),
            profile=profile("arch-family"),
        )
        self.assertEqual(window.app_list.count(), 2)
        sorot_row = next(
            index
            for index in range(window.app_list.count())
            if window.app_list.item(index).data(Qt.ItemDataRole.UserRole) == "sorot"
        )
        window.app_list.setCurrentRow(sorot_row)
        self.assertEqual(window.current_application.id, "sorot")
        self.assertFalse(window.install_button.isEnabled())
        self.assertIn("Belum tersedia", window.install_button.text())
        sorot = window.current_application
        self.assertEqual(window.source_combo.count(), len(source_artifacts(sorot)))
        self.assertTrue(window.source_button.isEnabled())
        self.assertTrue(window.website_button.isEnabled())
        self.assertTrue(window.manifest_button.isEnabled())
        window.close()

    def test_launcher_portal_shortcut_opens_canonical_website(self) -> None:
        window = MainWindow(
            service=CatalogService(data_dir=DATA_DIR),
            profile=profile("debian-family"),
        )
        self.assertTrue(window.portal_button.isEnabled())
        with patch("lsl_center.gui.QDesktopServices.openUrl", return_value=True) as open_url:
            window.portal_button.click()
        opened_url = open_url.call_args.args[0]
        self.assertEqual(opened_url.toString(), "https://linux-software-lab.vercel.app/launcher/")
        self.assertIn("Portal web dibuka", window.status_message.text())
        window.close()

    def test_debian_catalogue_shows_testing_install_action_with_explicit_status(self) -> None:
        window = MainWindow(
            service=CatalogService(data_dir=DATA_DIR),
            profile=profile("debian-family"),
        )
        sorot_row = next(
            index
            for index in range(window.app_list.count())
            if window.app_list.item(index).data(Qt.ItemDataRole.UserRole) == "sorot"
        )
        window.app_list.setCurrentRow(sorot_row)
        self.assertTrue(window.install_button.isEnabled())
        self.assertIn("Beta", window.install_button.text())
        self.assertIn("TESTING", window.product_status.text())
        self.assertIn("SHA-256", window.compatibility_label.text())
        window.close()


if __name__ == "__main__":
    unittest.main()
