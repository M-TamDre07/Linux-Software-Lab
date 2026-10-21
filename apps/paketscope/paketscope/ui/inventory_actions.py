"""Inventory refresh, update checks, and diagnostic UI handlers."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMessageBox

from ..domain import InstalledApplication, InventorySnapshot
from ..updates import UpdateCheckResult


class InventoryActionsMixin:
    """UI handlers for local inventory and update status."""

    @Slot()
    def refresh_inventory(self) -> None:
        self._start_task("Membaca inventaris lokal…", self.services.scan_inventory, self._inventory_ready)

    def _inventory_ready(self, value: object) -> None:
        if not isinstance(value, InventorySnapshot):
            self.status_label.setText("Hasil inventaris tidak valid.")
            return
        self.snapshot = value
        self.inventory_model.set_applications(value.applications)
        apt_count = sum(1 for app in value.applications if app.source == "APT / dpkg")
        flatpak_count = sum(1 for app in value.applications if app.source == "Flatpak")
        self.total_value.setText(f"{len(value.applications):,}")
        self.apt_value.setText(f"{apt_count:,}")
        self.flatpak_value.setText(f"{flatpak_count:,}")
        self.diagnostics_button.setEnabled(bool(value.diagnostics))
        self.status_label.setText(
            f"Diperbarui {datetime.now().strftime('%H:%M:%S')}  ·  {self.proxy.rowCount():,} baris cocok"
        )
        if value.diagnostics:
            self.status_label.setText(self.status_label.text() + f"  ·  {len(value.diagnostics)} catatan diagnostik")

    @Slot()
    def check_for_updates(self) -> None:
        def show(value: object) -> None:
            if not isinstance(value, UpdateCheckResult):
                return
            lines = [
                f"Pembaruan APT (berdasarkan metadata lokal): {len(value.apt_updates)}",
                f"Pembaruan Flatpak (memeriksa remote yang dikonfigurasi): {len(value.flatpak_updates)}",
                "",
                "Tidak ada paket yang dipasang, diperbarui, atau dihapus.",
            ]
            if value.apt_updates:
                lines.extend(["", "APT: " + ", ".join(value.apt_updates[:20])])
            if value.flatpak_updates:
                lines.extend(["", "Flatpak: " + ", ".join(value.flatpak_updates[:20])])
            if value.diagnostics:
                lines.extend(["", "Catatan:", *value.diagnostics])
            QMessageBox.information(self, "Hasil pemeriksaan pembaruan", "\n".join(lines))
            self.status_label.setText(
                f"Pembaruan ditemukan — APT {len(value.apt_updates)} · Flatpak {len(value.flatpak_updates)}"
            )

        self._start_task("Memeriksa pembaruan; Flatpak dapat mengakses remote…", self.services.check_updates, show)

    @Slot()
    def show_diagnostics(self) -> None:
        details = "\n".join("• " + item for item in self.snapshot.diagnostics)
        QMessageBox.information(self, "Diagnostik inventaris", details or "Tidak ada catatan diagnostik.")

    def _visible_applications(self) -> list[InstalledApplication]:
        rows = []
        for proxy_row in range(self.proxy.rowCount()):
            source_row = self.proxy.mapToSource(self.proxy.index(proxy_row, 0)).row()
            rows.append(self.inventory_model.applications[source_row])
        return rows
