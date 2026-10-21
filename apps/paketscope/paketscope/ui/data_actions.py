"""User-triggered data export and encrypted-backup UI handlers."""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from ..domain import InstalledApplication


class DataActionsMixin:
    """UI handlers for exporting inventory and restoring backups."""

    @Slot()
    def export_csv(self) -> None:
        applications = self._visible_applications()
        if not applications:
            QMessageBox.information(self, "Ekspor CSV", "Tidak ada baris yang terlihat untuk diekspor.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Ekspor inventaris yang terlihat", "paketscope-inventory.csv", "CSV (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            count = self.services.export_csv(applications, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Ekspor gagal", str(exc))
            return
        self.status_label.setText(f"Ekspor CSV selesai · {count} baris")

    @Slot()
    def export_encrypted_backup(self) -> None:
        if not self.snapshot.applications:
            QMessageBox.information(self, "Cadangan terenkripsi", "Pindai inventaris terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan cadangan terenkripsi", "paketscope-backup.psbackup", "PaketScope backup (*.psbackup)"
        )
        if not path:
            return
        if not path.lower().endswith(".psbackup"):
            path += ".psbackup"
        password, ok = QInputDialog.getText(
            self, "Kata sandi cadangan", "Buat kata sandi minimal 12 karakter:", QLineEdit.EchoMode.Password
        )
        if not ok:
            return
        confirm, ok = QInputDialog.getText(
            self, "Konfirmasi kata sandi", "Masukkan kembali kata sandi:", QLineEdit.EchoMode.Password
        )
        if not ok:
            return
        if password != confirm:
            QMessageBox.warning(self, "Cadangan batal", "Kedua kata sandi tidak cocok.")
            return
        try:
            count = self.services.create_encrypted_backup(self.snapshot.applications, path, password)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Cadangan gagal", str(exc))
            return
        finally:
            password = ""
            confirm = ""
        QMessageBox.information(
            self, "Cadangan tersimpan",
            f"Cadangan {count} aplikasi berhasil dienkripsi dengan AES-GCM. Simpan kata sandi secara terpisah; kata sandi tidak disimpan oleh aplikasi."
        )
        self.status_label.setText("Cadangan terenkripsi berhasil dibuat.")

    @Slot()
    def decrypt_backup_to_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Buka cadangan PaketScope", "", "PaketScope backup (*.psbackup)"
        )
        if not path:
            return
        password, ok = QInputDialog.getText(
            self, "Kata sandi cadangan", "Masukkan kata sandi cadangan:", QLineEdit.EchoMode.Password
        )
        if not ok:
            return
        try:
            records = self.services.restore_backup(path, password)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Tidak dapat membuka cadangan", str(exc))
            return
        finally:
            password = ""
        confirm = QMessageBox.warning(
            self, "Simpan JSON tanpa enkripsi?",
            "File JSON hasil dekripsi berisi nama dan versi paket dalam bentuk teks biasa. Simpan hanya di lokasi tepercaya.",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Save:
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Simpan hasil dekripsi", "paketscope-inventory.json", "JSON (*.json)"
        )
        if not target:
            return
        try:
            self.services.export_restored_json(target, records)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Simpan gagal", str(exc))
            return
        self.status_label.setText("Cadangan dibuka; JSON tanpa enkripsi disimpan secara eksplisit.")
