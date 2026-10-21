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
from .package_manager import (
    AptSearchResult,
    AptTransactionPreview,
    PackageOperationError,
    apply_apt_action,
    preview_apt_action,
    search_apt_packages,
)


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
        self.version_label = QLabel(f"VERSION {__version__.upper()}")
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

        management_row = QHBoxLayout()
        management_row.setSpacing(8)
        self.install_button = QPushButton("Cari & pasang APT…")
        self.install_button.setToolTip("Cari paket pada indeks APT lokal, tinjau simulasi, lalu konfirmasi sebelum pemasangan.")
        self.install_button.clicked.connect(self.install_apt_package)
        management_row.addWidget(self.install_button)
        self.remove_button = QPushButton("Hapus paket terpilih…")
        self.remove_button.setObjectName("secondary")
        self.remove_button.setToolTip("Hanya untuk aplikasi APT/dpkg. Simulasi dan konfirmasi selalu ditampilkan.")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_selected_apt_package)
        management_row.addWidget(self.remove_button)
        self.purge_button = QPushButton("Purge paket terpilih…")
        self.purge_button.setObjectName("secondary")
        self.purge_button.setToolTip("Menghapus paket dan konfigurasi sistem yang dikelola dpkg; data pengguna bisa tetap ada.")
        self.purge_button.setEnabled(False)
        self.purge_button.clicked.connect(self.purge_selected_apt_package)
        management_row.addWidget(self.purge_button)
        management_row.addStretch(1)
        layout.addLayout(management_row)
        self.table.selectionModel().currentRowChanged.connect(self._selection_changed)

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

        privacy = QLabel("LOCAL-FIRST  ·  TANPA TELEMETRI  ·  APT DENGAN KONFIRMASI SISTEM  ·  FLATPAK MASIH READ-ONLY")
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
        self._busy = busy
        for button in (
            self.refresh_button, self.updates_button, self.csv_button,
            self.backup_button, self.decrypt_button, self.install_button,
        ):
            button.setEnabled(not busy)
        self._selection_changed(QModelIndex(), QModelIndex())
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

    def _selected_application(self) -> InstalledApplication | None:
        current = self.table.currentIndex()
        if not current.isValid():
            return None
        source_index = self.proxy.mapToSource(current)
        if not source_index.isValid():
            return None
        row = source_index.row()
        if not (0 <= row < len(self.inventory_model.applications)):
            return None
        return self.inventory_model.applications[row]

    def _selection_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        selected = self._selected_application()
        can_change = (
            not getattr(self, "_busy", False)
            and selected is not None
            and selected.source == "APT / dpkg"
        )
        self.remove_button.setEnabled(bool(can_change))
        self.purge_button.setEnabled(bool(can_change))

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
