"""APT package search and guarded package-action handlers.

These methods are a mixin consumed by MainWindow. They coordinate UI prompts,
while package validation, simulation, and execution live in package_manager.py.
"""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QInputDialog, QMessageBox

from ..domain import InstalledApplication
from ..package_manager import (
    AptSearchResult,
    AptTransactionPreview,
    apply_apt_action,
    preview_apt_action,
    search_apt_packages,
)


class PackageManagementActionsMixin:
    """UI handlers for explicitly confirmed APT package operations."""

    @Slot()
    def install_apt_package(self) -> None:
        query, accepted = QInputDialog.getText(
            self,
            "Cari aplikasi APT",
            "Nama aplikasi atau kata pencarian (menggunakan indeks APT lokal):",
        )
        if not accepted:
            return
        if not query.strip():
            QMessageBox.information(self, "Cari aplikasi APT", "Masukkan nama atau kata pencarian terlebih dahulu.")
            return
        self._start_task(
            "Mencari paket pada indeks APT lokal…",
            lambda: search_apt_packages(query),
            self._apt_search_ready,
        )

    def _apt_search_ready(self, value: object) -> None:
        if not isinstance(value, tuple):
            QMessageBox.warning(self, "Pencarian APT", "Hasil pencarian tidak valid.")
            return
        results = [item for item in value if isinstance(item, AptSearchResult)]
        installed = {
            item.identifier.split(":", 1)[0]
            for item in self.snapshot.applications
            if item.source == "APT / dpkg"
        }
        available = [item for item in results if item.name.split(":", 1)[0] not in installed]
        if not available:
            QMessageBox.information(
                self,
                "Pencarian APT",
                "Tidak ada paket baru yang cocok pada indeks lokal. Coba kata lain atau perbarui indeks paket melalui alat sistem tepercaya terlebih dahulu.",
            )
            return
        labels = [f"{item.name} — {item.description}" for item in available]
        selected, accepted = QInputDialog.getItem(
            self,
            "Pilih paket untuk dipasang",
            "Pilih paket dari repositori APT yang sudah dikonfigurasi:",
            labels,
            0,
            False,
        )
        if not accepted:
            return
        chosen = available[labels.index(selected)]
        self._begin_apt_action("install", chosen.name, chosen.description)

    @Slot()
    def remove_selected_apt_package(self) -> None:
        self._remove_selected_apt_package("remove")

    @Slot()
    def purge_selected_apt_package(self) -> None:
        self._remove_selected_apt_package("purge")

    def _remove_selected_apt_package(self, action: str) -> None:
        selected = self._selected_application()
        if selected is None:
            QMessageBox.information(self, "Kelola aplikasi", "Pilih satu baris aplikasi terlebih dahulu.")
            return
        if selected.source != "APT / dpkg":
            QMessageBox.information(
                self,
                "Sumber paket belum didukung",
                "Aksi perubahan pada antarmuka ini saat ini hanya tersedia untuk paket APT/dpkg. "
                "Aplikasi Flatpak tetap dapat dilihat dan diperiksa pembaruannya, tetapi belum dapat diubah dari PaketScope.",
            )
            return
        self._begin_apt_action(action, selected.identifier, selected.name)

    def _begin_apt_action(self, action: str, package_name: str, display_name: str) -> None:
        self._start_task(
            f"Memeriksa rencana APT untuk {package_name}…",
            lambda: preview_apt_action(action, package_name),
            lambda value: self._confirm_apt_action(value, action, package_name, display_name),
        )

    def _confirm_apt_action(
        self,
        value: object,
        action: str,
        package_name: str,
        display_name: str,
    ) -> None:
        if not isinstance(value, AptTransactionPreview):
            QMessageBox.warning(self, "PaketScope", "Simulasi APT tidak menghasilkan rencana yang dapat diverifikasi.")
            return
        verb = {"install": "memasang", "remove": "menghapus", "purge": "melakukan purge pada"}[action]
        lines = [
            f"PaketScope akan meminta APT untuk {verb}: {display_name} ({package_name}).",
            "",
        ]
        if value.install:
            lines.append(f"Paket yang akan dipasang ({len(value.install)}):")
            lines.extend(f"  • {name}" for name in value.install[:24])
            if len(value.install) > 24:
                lines.append(f"  • dan {len(value.install) - 24} paket lainnya")
        removed = tuple(dict.fromkeys(value.remove + value.purge))
        if removed:
            lines.append(f"Paket yang akan dihapus ({len(removed)}):")
            lines.extend(f"  • {name}" for name in removed[:24])
            if len(removed) > 24:
                lines.append(f"  • dan {len(removed) - 24} paket lainnya")
        if action == "purge":
            lines.extend([
                "",
                "Purge menghapus paket dan konfigurasi sistem yang dikelola dpkg. Data pengguna "
                "di direktori home atau konfigurasi aplikasi di luar dpkg mungkin tetap ada.",
            ])
        elif action == "remove":
            lines.extend([
                "",
                "Penghapusan paket tidak otomatis menghapus dependensi yang sudah tidak dipakai "
                "atau semua data pengguna.",
            ])
        lines.extend([
            "",
            "Operasi baru berjalan setelah kamu menyetujui dialog ini dan autentikasi sistem. "
            "PaketScope tidak menjalankan autoremove dan tidak menjalankan upgrade massal.",
        ])
        answer = QMessageBox.question(
            self,
            "Tinjau perubahan paket",
            "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.status_label.setText("Operasi paket dibatalkan; sistem tidak diubah.")
            return
        self._start_task(
            "Menjalankan APT melalui autentikasi sistem…",
            lambda: apply_apt_action(action, package_name),
            lambda result: self._apt_action_completed(result, action, display_name),
        )

    def _apt_action_completed(self, value: object, action: str, display_name: str) -> None:
        verb = {"install": "Pemasangan", "remove": "Penghapusan", "purge": "Purge"}[action]
        QMessageBox.information(
            self,
            f"{verb} selesai",
            f"APT melaporkan operasi {verb.lower()} untuk {display_name} selesai. "
            "Inventaris akan dipindai ulang agar tampilan mengikuti kondisi sistem terbaru.",
        )
        self.refresh_inventory()
