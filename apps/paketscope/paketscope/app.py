"""PaketScope Qt desktop UI."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QRunnable, QSortFilterProxyModel, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QTableView, QVBoxLayout, QWidget,
)

from . import __version__
from .domain import InstalledApplication, InventorySnapshot
from .services import PaketScopeService
from .updates import UpdateCheckResult


COLUMNS = ("Nama aplikasi / paket", "Versi", "Sumber", "ID paket", "Asal / cabang")
APP_QSS = """
QMainWindow, QWidget#root { background: #f4f6fa; color: #192230; }
QWidget { font-family: "Inter", "Segoe UI", "SF Pro Text", "Noto Sans", sans-serif; font-size: 13px; }
QFrame#topbar, QFrame#stat, QFrame#panel { background: #ffffff; border: 1px solid #e1e7f0; border-radius: 14px; }
QLabel#eyebrow, QLabel#mono { color: #667085; font-family: "Noto Sans Mono", monospace; font-size: 10px; letter-spacing: .6px; }
QLabel#title { color: #172033; font-size: 28px; font-weight: 700; letter-spacing: -.7px; }
QLabel#stat-value { color: #172033; font-size: 24px; font-weight: 700; }
QLabel#body-muted { color: #667085; }
QLineEdit, QComboBox { background: #ffffff; color: #192230; border: 1px solid #cfd7e5; border-radius: 9px; padding: 9px 11px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus, QTableView:focus { border: 1px solid #315df5; }
QPushButton { background: #315df5; color: #ffffff; border: 1px solid #315df5; border-radius: 9px; padding: 10px 13px; font-size: 12px; font-weight: 650; }
QPushButton:hover { background: #2448cf; border-color: #2448cf; }
QPushButton:pressed { background: #1d3cae; }
QPushButton:disabled { background: #d8deea; border-color: #d8deea; color: #7a8496; }
QPushButton#secondary { background: #ffffff; color: #273247; border-color: #d4dce8; }
QPushButton#secondary:hover { background: #f1f5fb; border-color: #b8c4d8; }
QTableView { background: #ffffff; alternate-background-color: #f7f9fc; color: #192230; border: 1px solid #e1e7f0; border-radius: 10px; gridline-color: #e8edf4; selection-background-color: #dce7ff; selection-color: #172033; outline: none; }
QHeaderView::section { background: #f3f6fb; color: #667085; border: none; border-bottom: 1px solid #e1e7f0; padding: 11px 9px; font-family: "Noto Sans Mono", monospace; font-size: 10px; font-weight: 650; }
QScrollBar:vertical { background: #f3f6fb; width: 10px; margin: 2px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #c0cadb; min-height: 25px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #9eacc3; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class InventoryModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.applications: list[InstalledApplication] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.applications)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.applications)):
            return None
        app = self.applications[index.row()]
        values = (app.name, app.version, app.source, app.identifier, " · ".join(part for part in (app.origin, app.branch) if part) or "—")
        if role == Qt.ItemDataRole.DisplayRole:
            return values[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{app.name}\nID: {app.identifier}\nSumber: {app.source}"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(COLUMNS):
            return COLUMNS[section]
        if orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        return None

    def set_applications(self, applications: tuple[InstalledApplication, ...]) -> None:
        self.beginResetModel()
        self.applications = list(applications)
        self.endResetModel()


class InventoryProxy(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.query = ""
        self.source_filter = "Semua sumber"
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_query(self, query: str) -> None:
        self.query = query.strip().casefold()
        self.invalidateFilter()

    def set_source_filter(self, source: str) -> None:
        self.source_filter = source
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        values = [str(model.index(source_row, col, source_parent).data() or "") for col in range(model.columnCount())]
        if self.source_filter != "Semua sumber":
            selected = "flatpak" if self.source_filter == "Flatpak" else "apt / dpkg"
            if selected not in values[2].casefold():
                return False
        return not self.query or any(self.query in value.casefold() for value in values)


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, function: Callable[[], object]) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            value = self.function()
        except Exception as exc:
            self.signals.error.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.result.emit(value)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PaketScope 3")
        self.setMinimumSize(780, 580)
        self.resize(1140, 760)
        icon_path = Path(__file__).parent / "assets" / "paketscope.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.pool = QThreadPool.globalInstance()
        self.services = PaketScopeService()
        self.worker: Worker | None = None
        self.pending_handler: Callable[[object], None] | None = None
        self.snapshot = InventorySnapshot.create(())
        self.inventory_model = InventoryModel()
        self.proxy = InventoryProxy(self)
        self.proxy.setSourceModel(self.inventory_model)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 15)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("topbar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 15, 18, 15)
        title_group = QVBoxLayout()
        eyebrow = QLabel("LINUX SOFTWARE LAB  /  INVENTORY")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("PaketScope")
        title.setObjectName("title")
        subtitle = QLabel("A clearer view of the software on your system.")
        subtitle.setObjectName("body-muted")
        title_group.addWidget(eyebrow)
        title_group.addWidget(title)
        title_group.addWidget(subtitle)
        header_layout.addLayout(title_group)
        header_layout.addStretch(1)
        self.version_label = QLabel("VERSION 3.0.0-DEV")
        self.version_label.setObjectName("mono")
        header_layout.addWidget(self.version_label, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(header)

        stats = QHBoxLayout()
        stats.setSpacing(1)
        self.total_value = self._add_stat(stats, "PACKAGES FOUND", "—")
        self.apt_value = self._add_stat(stats, "APT / DPKG", "—")
        self.flatpak_value = self._add_stat(stats, "FLATPAK", "—")
        layout.addLayout(stats)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cari nama, versi, sumber, atau ID paket…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Cari inventaris aplikasi")
        self.search.textChanged.connect(self.proxy.set_query)
        controls.addWidget(self.search, 1)
        self.source_filter = QComboBox()
        self.source_filter.addItems(["Semua sumber", "APT / dpkg", "Flatpak"])
        self.source_filter.setAccessibleName("Filter sumber paket")
        self.source_filter.currentTextChanged.connect(self.proxy.set_source_filter)
        controls.addWidget(self.source_filter)
        self.refresh_button = QPushButton("Pindai ulang")
        self.refresh_button.setToolTip("Baca inventaris lokal; tidak mengubah paket.")
        self.refresh_button.clicked.connect(self.refresh_inventory)
        controls.addWidget(self.refresh_button)
        self.updates_button = QPushButton("Periksa pembaruan")
        self.updates_button.setObjectName("secondary")
        self.updates_button.setToolTip("Memeriksa status pembaruan; tidak memasang atau mengubah paket.")
        self.updates_button.clicked.connect(self.check_for_updates)
        controls.addWidget(self.updates_button)
        layout.addLayout(controls)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setDefaultSectionSize(33)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 255)
        self.table.setColumnWidth(1, 135)
        self.table.setColumnWidth(2, 115)
        self.table.setColumnWidth(3, 255)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setAccessibleName("Tabel inventaris aplikasi dan paket")
        layout.addWidget(self.table, 1)

        action_row = QHBoxLayout()
        self.status_label = QLabel("Siap memindai inventaris lokal.")
        self.status_label.setObjectName("body-muted")
        action_row.addWidget(self.status_label, 1)
        self.diagnostics_button = QPushButton("Diagnostik")
        self.diagnostics_button.setObjectName("secondary")
        self.diagnostics_button.clicked.connect(self.show_diagnostics)
        self.diagnostics_button.setEnabled(False)
        action_row.addWidget(self.diagnostics_button)
        self.csv_button = QPushButton("Ekspor CSV terlihat")
        self.csv_button.setObjectName("secondary")
        self.csv_button.clicked.connect(self.export_csv)
        action_row.addWidget(self.csv_button)
        self.backup_button = QPushButton("Cadangan terenkripsi")
        self.backup_button.clicked.connect(self.export_encrypted_backup)
        action_row.addWidget(self.backup_button)
        self.decrypt_button = QPushButton("Dekripsi ke JSON")
        self.decrypt_button.setObjectName("secondary")
        self.decrypt_button.setToolTip("Dekripsi cadangan ke JSON teks biasa dengan persetujuan eksplisit.")
        self.decrypt_button.clicked.connect(self.decrypt_backup_to_json)
        action_row.addWidget(self.decrypt_button)
        layout.addLayout(action_row)

        privacy = QLabel("LOCAL-FIRST  ·  TANPA TELEMETRI  ·  TIDAK MEMERLUKAN ROOT  ·  TIDAK ADA AKSI INSTALL/REMOVE")
        privacy.setObjectName("mono")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

    def _add_stat(self, layout: QHBoxLayout, label_text: str, value_text: str) -> QLabel:
        card = QFrame()
        card.setObjectName("stat")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(15, 11, 15, 11)
        label = QLabel(label_text)
        label.setObjectName("eyebrow")
        value = QLabel(value_text)
        value.setObjectName("stat-value")
        inner.addWidget(label)
        inner.addWidget(value)
        layout.addWidget(card, 1)
        return value

    def _set_busy(self, busy: bool, message: str = "") -> None:
        for button in (self.refresh_button, self.updates_button, self.csv_button, self.backup_button, self.decrypt_button):
            button.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    def _start_task(self, message: str, function: Callable[[], object], on_result: Callable[[object], None]) -> None:
        if self.worker is not None:
            return
        self._set_busy(True, message)
        worker = Worker(function)
        self.worker = worker
        self.pending_handler = on_result
        # Explicit queued delivery keeps all widget updates on the GUI thread.
        worker.signals.result.connect(self._worker_result, Qt.ConnectionType.QueuedConnection)
        worker.signals.error.connect(self._worker_failed, Qt.ConnectionType.QueuedConnection)
        self.pool.start(worker)

    @Slot(object)
    def _worker_result(self, value: object) -> None:
        self.worker = None
        handler = self.pending_handler
        self.pending_handler = None
        self._set_busy(False)
        if handler is not None:
            handler(value)

    @Slot(str)
    def _worker_failed(self, error: str) -> None:
        self.worker = None
        self.pending_handler = None
        self._set_busy(False)
        self.status_label.setText("Operasi tidak selesai.")
        QMessageBox.warning(self, "PaketScope", error)

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
            from .updates import UpdateCheckResult
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
        except OSError as exc:
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
        except OSError as exc:
            QMessageBox.warning(self, "Simpan gagal", str(exc))
            return
        self.status_label.setText("Cadangan dibuka; JSON tanpa enkripsi disimpan secara eksplisit.")

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PaketScope")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, window.refresh_inventory)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
