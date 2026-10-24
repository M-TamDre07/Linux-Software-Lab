"""Main desktop window and event coordination."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QModelIndex, Qt, QThreadPool, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..domain import InstalledApplication, InventorySnapshot
from ..services import PaketScopeService
from ..application_details import ApplicationDetails, inspect_application
from .models import InventoryModel, InventoryProxy
from .workers import Worker
from .data_actions import DataActionsMixin
from .inventory_actions import InventoryActionsMixin
from .package_actions import PackageManagementActionsMixin
from .inspection_dialog import InspectionDialog
from .application_details_dialog import ApplicationDetailsDialog


class MainWindow(QMainWindow, PackageManagementActionsMixin, InventoryActionsMixin, DataActionsMixin):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PaketScope 3")
        self.setMinimumSize(780, 580)
        self.resize(1140, 760)
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "paketscope.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.pool = QThreadPool.globalInstance()
        self.services = PaketScopeService()
        self.worker: Worker | None = None
        self.pending_handler: Callable[[object], None] | None = None
        self.inspection_dialog: InspectionDialog | None = None
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
        self.details_button = QPushButton("Detail & asal…")
        self.details_button.setObjectName("secondary")
        self.details_button.setToolTip(
            "Lihat deskripsi resmi, jenis paket, asal repositori yang diketahui, dan metadata aplikasi terpilih."
        )
        self.details_button.setEnabled(False)
        self.details_button.clicked.connect(self.show_selected_application_details)
        management_row.addWidget(self.details_button)
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
        self.inspection_button = QPushButton("Eksplorasi Sistem & Kode…")
        self.inspection_button.setObjectName("secondary")
        self.inspection_button.setToolTip("Inspeksi sistem read-only dan analisis statis folder/file kode lokal.")
        self.inspection_button.clicked.connect(self.open_inspection_lab)
        management_row.addWidget(self.inspection_button)
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
            self.details_button, self.inspection_button,
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

    @Slot()
    def show_selected_application_details(self) -> None:
        selected = self._selected_application()
        if selected is None:
            QMessageBox.information(
                self, "Detail aplikasi", "Pilih satu aplikasi atau paket dari tabel terlebih dahulu."
            )
            return
        self._start_task(
            f"Membaca metadata lokal untuk {selected.identifier}…",
            lambda: inspect_application(selected),
            self._application_details_ready,
        )

    def _application_details_ready(self, value: object) -> None:
        if not isinstance(value, ApplicationDetails):
            QMessageBox.warning(
                self, "Detail aplikasi", "Pemeriksa tidak mengembalikan detail aplikasi yang valid."
            )
            return
        dialog = ApplicationDetailsDialog(value, self)
        dialog.exec()

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
        self.details_button.setEnabled(
            not getattr(self, "_busy", False) and selected is not None
        )


    @Slot()
    def open_inspection_lab(self) -> None:
        """Open the local, read-only system and code inspection tools."""
        if self.inspection_dialog is None or not self.inspection_dialog.isVisible():
            self.inspection_dialog = InspectionDialog(self)
        self.inspection_dialog.show()
        self.inspection_dialog.raise_()
        self.inspection_dialog.activateWindow()
