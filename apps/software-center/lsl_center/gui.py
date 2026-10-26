"""PySide6 GUI for Linux Software Lab Center; all package logic stays in shared services."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QUrl, Signal, Slot
    from PySide6.QtGui import QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - depends on optional GUI extra
    raise RuntimeError(
        "GUI dependencies are missing. Install the [gui] extra: "
        "python -m pip install -e '.[gui]'"
    ) from exc

from .catalog import CatalogError, CatalogService
from .distro import artifact_compatibility, detect_system_profile, executable_for
from .installer import (
    download_artifact,
    install_verified_artifact,
    preview_installation,
)
from .models import (
    Application,
    Artifact,
    CatalogSnapshot,
    InstallPreview,
    InstallResult,
    SystemProfile,
)
from .selection import select_artifact, source_artifacts

STYLE = """
QMainWindow, QWidget#rootWidget { background: #11110f; color: #ece9e0; }
QWidget { color: #ece9e0; font-size: 12px; }
QFrame#header, QFrame#catalogPanel, QFrame#detailPanel, QFrame#actionPanel {
    background: #171715; border: 1px solid #33322c;
}
QLabel#eyebrow { color: #a6a194; font-size: 9px; font-weight: 600; }
QLabel#brandTitle { font-size: 17px; font-weight: 700; }
QLabel#productTitle { font-size: 29px; font-weight: 750; }
QLabel#muted, QLabel#systemLabel, QLabel#statusMessage { color: #aaa79c; }
QLineEdit, QComboBox {
    background: #11110f; border: 1px solid #4b4941; padding: 9px;
    selection-background-color: #ffb000; selection-color: #171715;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #ffb000; }
QListWidget {
    border: none; outline: none; background: transparent;
    alternate-background-color: #1d1c18;
}
QListWidget::item {
    border: 1px solid #34332d; background: #1b1a17;
    padding: 11px; margin: 4px 1px; min-height: 76px;
}
QListWidget::item:selected {
    border: 1px solid #ffb000; background: #26231a; color: #fff9e8;
}
QListWidget::item:hover { border: 1px solid #777164; }
QPushButton {
    background: #eae6dc; color: #171715; border: 1px solid #eae6dc;
    padding: 10px 13px; font-weight: 650;
}
QPushButton:hover { background: #ffb000; border-color: #ffb000; }
QPushButton:disabled {
    background: #24231f; color: #77746b; border-color: #34332d;
}
QPushButton#secondaryButton {
    background: transparent; color: #ece9e0; border: 1px solid #4b4941;
}
QPushButton#secondaryButton:hover { color: #171715; background: #ffb000; border-color: #ffb000; }
QScrollArea { border: none; background: transparent; }
QLabel#productSummary { font-size: 14px; font-weight: 600; }
QLabel#productDescription { color: #c2beb3; line-height: 1.5; }
QLabel#statusPill {
    border: 1px solid #5a5240; color: #ffcf5c;
    padding: 5px 8px; font-size: 10px; font-weight: 650;
}
QFrame#separator { background: #33322c; border: none; max-height: 1px; }
QLabel#featureItem { color: #d5d1c7; padding: 3px 0; }
"""


class TaskSignals(QObject):
    succeeded = Signal(str, object)
    failed = Signal(str, str)


class BackgroundTask(QRunnable):
    def __init__(self, key: str, operation: Callable[[], Any]) -> None:
        super().__init__()
        self.key = key
        self.operation = operation
        self.signals = TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self.key, self.operation())
        except Exception as exc:  # noqa: BLE001 - isolate arbitrary worker failures from the Qt event loop
            self.signals.failed.emit(self.key, str(exc))


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: CatalogService | None = None,
        profile: SystemProfile | None = None,
    ) -> None:
        super().__init__()
        self.service = service or CatalogService()
        self.profile = profile or detect_system_profile()
        self.snapshot: CatalogSnapshot = self.service.load()
        self.current_application: Application | None = None
        self._busy = False
        self._tasks: dict[str, BackgroundTask] = {}
        self._success_handlers: dict[str, Callable[[Any], None]] = {}
        self._error_handlers: dict[str, Callable[[str], None]] = {}
        self.thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("Linux Software Lab Center · Preview")
        self.setMinimumSize(920, 620)
        self.resize(1180, 760)
        icon = Path(__file__).resolve().parent / "data" / "assets" / "center-icon.svg"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        self._build_ui()
        self._populate_list()
        self._set_status(
            f"Katalog {self.snapshot.updated_at} · mode {self.snapshot.data_source} · "
            f"{self.profile.pretty_name} · {self.profile.architecture}"
        )
        if self.app_list.count():
            self.app_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("rootWidget")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 18, 20, 16)
        root_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 12, 15, 12)
        header_layout.setSpacing(12)
        brand_icon = QLabel()
        brand_icon.setFixedSize(38, 38)
        icon_path = Path(__file__).resolve().parent / "data" / "assets" / "center-icon.svg"
        if icon_path.is_file():
            brand_icon.setPixmap(QIcon(str(icon_path)).pixmap(38, 38))
        else:
            brand_icon.setText("LS")
        brand_copy = QVBoxLayout()
        title = QLabel("Linux Software Lab Center")
        title.setObjectName("brandTitle")
        eyebrow = QLabel("KATALOG APLIKASI · DESKTOP & TERMINAL")
        eyebrow.setObjectName("eyebrow")
        brand_copy.addWidget(title)
        brand_copy.addWidget(eyebrow)
        header_layout.addWidget(brand_icon)
        header_layout.addLayout(brand_copy)
        header_layout.addStretch(1)
        self.system_label = QLabel(
            f"{self.profile.pretty_name} · {self.profile.architecture}"
        )
        self.system_label.setObjectName("systemLabel")
        self.system_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.system_label.setWordWrap(True)
        header_layout.addWidget(self.system_label, 0)
        self.refresh_button = QPushButton("Perbarui katalog")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self._refresh_catalog)
        header_layout.addWidget(self.refresh_button)
        root_layout.addWidget(header)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(7)

        catalog_panel = QFrame()
        catalog_panel.setObjectName("catalogPanel")
        catalog_layout = QVBoxLayout(catalog_panel)
        catalog_layout.setContentsMargins(14, 15, 14, 12)
        catalog_layout.setSpacing(10)
        catalog_heading = QLabel("SEMUA APLIKASI")
        catalog_heading.setObjectName("eyebrow")
        self.count_label = QLabel(f"{len(self.snapshot.applications)} aplikasi")
        self.count_label.setObjectName("muted")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cari nama, kategori, atau fitur…")
        self.search.textChanged.connect(self._filter_list)
        self.app_list = QListWidget()
        self.app_list.setWordWrap(True)
        self.app_list.setSpacing(2)
        self.app_list.currentItemChanged.connect(self._selection_changed)
        catalog_layout.addWidget(catalog_heading)
        catalog_layout.addWidget(self.count_label)
        catalog_layout.addWidget(self.search)
        catalog_layout.addWidget(self.app_list, 1)
        split.addWidget(catalog_panel)

        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        details_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        details_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(22, 18, 18, 18)
        details_layout.setSpacing(13)

        identity = QHBoxLayout()
        identity.setSpacing(15)
        self.product_icon = QLabel()
        self.product_icon.setFixedSize(70, 70)
        self.product_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.product_icon.setStyleSheet(
            "background:#22211d; border:1px solid #454238; padding:7px;"
        )
        identity_copy = QVBoxLayout()
        self.product_category = QLabel()
        self.product_category.setObjectName("eyebrow")
        self.product_title = QLabel("Pilih aplikasi")
        self.product_title.setObjectName("productTitle")
        self.product_title.setWordWrap(True)
        self.product_status = QLabel()
        self.product_status.setObjectName("statusPill")
        self.product_status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        identity_copy.addWidget(self.product_category)
        identity_copy.addWidget(self.product_title)
        identity_copy.addWidget(self.product_status, 0, Qt.AlignmentFlag.AlignLeft)
        identity.addWidget(self.product_icon)
        identity.addLayout(identity_copy, 1)
        details_layout.addLayout(identity)

        self.product_summary = QLabel()
        self.product_summary.setObjectName("productSummary")
        self.product_summary.setWordWrap(True)
        self.product_description = QLabel()
        self.product_description.setObjectName("productDescription")
        self.product_description.setWordWrap(True)
        self.product_description.setTextFormat(Qt.TextFormat.PlainText)
        details_layout.addWidget(self.product_summary)
        details_layout.addWidget(self.product_description)

        self.version_label = QLabel()
        self.version_label.setObjectName("muted")
        self.version_label.setWordWrap(True)
        details_layout.addWidget(self.version_label)

        divider = QFrame()
        divider.setObjectName("separator")
        divider.setFixedHeight(1)
        details_layout.addWidget(divider)

        features_title = QLabel("FITUR UTAMA")
        features_title.setObjectName("eyebrow")
        details_layout.addWidget(features_title)
        self.features = QListWidget()
        self.features.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.features.setMaximumHeight(160)
        self.features.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        details_layout.addWidget(self.features)

        self.compatibility_label = QLabel()
        self.compatibility_label.setWordWrap(True)
        self.compatibility_label.setStyleSheet(
            "background:#201f1b; border-left:3px solid #ffb000; padding:12px; color:#d2cec3;"
        )
        details_layout.addWidget(self.compatibility_label)

        actions = QFrame()
        actions.setObjectName("actionPanel")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(14, 14, 14, 14)
        actions_layout.setSpacing(9)
        action_heading = QLabel("INSTALASI & OPSI LANJUTAN")
        action_heading.setObjectName("eyebrow")
        actions_layout.addWidget(action_heading)
        self.install_button = QPushButton("Belum tersedia")
        self.install_button.clicked.connect(self._start_install)
        actions_layout.addWidget(self.install_button)
        source_row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(150)
        self.download_button = QPushButton("Unduh source")
        self.download_button.setObjectName("secondaryButton")
        self.download_button.clicked.connect(self._download_source)
        source_row.addWidget(self.source_combo, 1)
        source_row.addWidget(self.download_button)
        actions_layout.addLayout(source_row)
        link_row = QHBoxLayout()
        self.open_button = QPushButton("Buka aplikasi")
        self.open_button.setObjectName("secondaryButton")
        self.open_button.clicked.connect(self._open_application)
        self.source_button = QPushButton("Lihat source")
        self.source_button.setObjectName("secondaryButton")
        self.source_button.clicked.connect(self._open_source)
        link_row.addWidget(self.open_button)
        link_row.addWidget(self.source_button)
        actions_layout.addLayout(link_row)
        details_layout.addWidget(actions)
        details_layout.addStretch(1)
        details_scroll.setWidget(details_widget)
        split.addWidget(details_scroll)
        split.setSizes([380, 750])
        root_layout.addWidget(split, 1)

        self.status_message = QLabel()
        self.status_message.setObjectName("statusMessage")
        self.status_message.setWordWrap(True)
        root_layout.addWidget(self.status_message)
        self.setCentralWidget(root)

    def _populate_list(self) -> None:
        current_id = self.current_application.id if self.current_application else None
        self.app_list.blockSignals(True)
        self.app_list.clear()
        query = self.search.text().strip().casefold()
        for app in self.snapshot.applications:
            haystack = " ".join(
                (app.name, app.summary, app.category, *app.tags, *app.keywords)
            ).casefold()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(
                f"{app.name}\n{app.summary}\n{app.category} · {app.status.upper()}"
            )
            item.setData(Qt.ItemDataRole.UserRole, app.id)
            item.setToolTip(app.summary)
            item.setSizeHint(QSize(315, 106))
            if app.icon_path and app.icon_path.is_file():
                item.setIcon(QIcon(str(app.icon_path)))
            self.app_list.addItem(item)
            if current_id == app.id:
                self.app_list.setCurrentItem(item)
        self.app_list.blockSignals(False)
        self.count_label.setText(f"{self.app_list.count()} dari {len(self.snapshot.applications)} aplikasi")
        if self.app_list.currentItem() is None and self.app_list.count():
            self.app_list.setCurrentRow(0)
        elif self.app_list.currentItem() is None:
            self.current_application = None
            self._clear_details()

    @Slot(str)
    def _filter_list(self, _query: str) -> None:
        self._populate_list()

    @Slot(object, object)
    def _selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        application_id = current.data(Qt.ItemDataRole.UserRole)
        app = self.snapshot.find(str(application_id))
        if app is None:
            return
        self.current_application = app
        self._render_details(app)

    def _render_details(self, app: Application) -> None:
        self.product_title.setText(app.name)
        self.product_category.setText(app.category.upper())
        self.product_status.setText(f"{app.status.upper()} · {app.app_type.upper()}")
        self.product_summary.setText(app.summary)
        self.product_description.setText(app.description)
        self.version_label.setText(
            f"Versi katalog: {app.version}\nPlatform tercatat: {'; '.join(app.platforms) or 'belum dicatat'}"
        )
        self.features.clear()
        for feature in app.features:
            item = QListWidgetItem(f"•  {feature}")
            self.features.addItem(item)
        if app.icon_path and app.icon_path.is_file():
            self.product_icon.setPixmap(QIcon(str(app.icon_path)).pixmap(62, 62))
        else:
            self.product_icon.clear()
            self.product_icon.setText(app.name[:1].upper())
        compatible = [
            artifact for artifact in app.artifacts
            if artifact.is_native_package and artifact_compatibility(artifact, self.profile)[0]
        ]
        if compatible:
            newest = compatible[-1]
            notice = (
                f"Format cocok: .{newest.format} · versi {newest.version} · "
                f"{newest.release_status.upper()}. "
                "Kompatibilitas package manager belum berarti semua distro/versi OS telah diuji."
            )
            if newest.release_status == "testing":
                notice += (
                    " Ini Beta/testing. Digest SHA-256 memeriksa kesamaan file terhadap metadata, "
                    "bukan tanda tangan penerbit."
                )
        elif app.artifacts:
            reasons = [
                artifact_compatibility(item, self.profile)[1]
                for item in app.artifacts
                if item.is_native_package
            ]
            notice = reasons[0] if reasons else "Hanya artefak source yang terdaftar; source bukan installer native."
        else:
            notice = "Belum ada paket rilis terdaftar untuk pemasangan satu-klik. Source tetap bisa ditinjau."
        if app.planned_targets:
            planned_lines = [
                f"Direncanakan · {target.distribution_id} · versi {target.version}: {target.note}"
                for target in app.planned_targets
            ]
            notice += "\\n\\n" + "\\n".join(planned_lines)
        self.compatibility_label.setText(notice)

        self.source_combo.clear()
        for artifact in source_artifacts(app):
            self.source_combo.addItem(
                f"{artifact.version} · .{artifact.format}",
                artifact,
            )
        if self.source_combo.count():
            self.source_combo.setCurrentIndex(self.source_combo.count() - 1)
        self.source_button.setEnabled(bool(app.source_url) and not self._busy)

        executable = executable_for(app.id)
        self.open_button.setVisible(bool(executable))
        self.open_button.setEnabled(bool(executable) and not self._busy)
        install_artifact = select_artifact(app, self.profile, install_only=True)
        self._install_artifact = install_artifact
        if install_artifact:
            self.install_button.setText(
                "Pasang versi Beta" if install_artifact.release_status == "testing" else "Pasang aplikasi"
            )
            self.install_button.setEnabled(not self._busy)
        else:
            has_package = any(item.is_native_package for item in app.artifacts)
            self.install_button.setText(
                "Belum tersedia untuk distro ini" if has_package else "Belum ada paket rilis"
            )
            self.install_button.setEnabled(False)
        self.download_button.setEnabled(bool(self.source_combo.count()) and not self._busy)

    def _clear_details(self) -> None:
        self.product_title.setText("Tidak ada hasil")
        self.product_category.clear()
        self.product_status.clear()
        self.product_summary.setText("Ubah kata pencarian untuk melihat aplikasi.")
        self.product_description.clear()
        self.version_label.clear()
        self.features.clear()
        self.compatibility_label.clear()
        self.install_button.setText("Belum tersedia")
        self.install_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.source_button.setEnabled(False)
        self.open_button.setVisible(False)
        self.source_combo.clear()

    def _set_status(self, message: str) -> None:
        self.status_message.setText(message)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        if message:
            self._set_status(message)
        self.refresh_button.setEnabled(not busy)
        self.search.setEnabled(not busy)
        self.app_list.setEnabled(not busy)
        if self.current_application:
            self._render_details(self.current_application)

    def _run_task(
        self,
        name: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if self._busy:
            return
        key = f"{name}-{uuid.uuid4().hex}"
        task = BackgroundTask(key, operation)
        self._tasks[key] = task
        self._success_handlers[key] = on_success
        self._error_handlers[key] = on_error or (lambda error: QMessageBox.warning(self, "Operasi gagal", error))
        task.signals.succeeded.connect(self._task_succeeded)
        task.signals.failed.connect(self._task_failed)
        self._set_busy(True, f"{name}: sedang diproses…")
        self.thread_pool.start(task)

    @Slot(str, object)
    def _task_succeeded(self, key: str, result: Any) -> None:
        callback = self._success_handlers.pop(key, None)
        self._error_handlers.pop(key, None)
        self._tasks.pop(key, None)
        self._set_busy(False)
        if callback:
            callback(result)

    @Slot(str, str)
    def _task_failed(self, key: str, error: str) -> None:
        callback = self._error_handlers.pop(key, None)
        self._success_handlers.pop(key, None)
        self._tasks.pop(key, None)
        self._set_busy(False, "Operasi gagal. Tidak ada klaim keberhasilan yang dibuat.")
        if callback:
            callback(error)

    def _refresh_catalog(self) -> None:
        def succeeded(snapshot: CatalogSnapshot) -> None:
            self.snapshot = snapshot
            self.current_application = None
            self._set_status(f"Katalog diperbarui · {snapshot.updated_at} · {len(snapshot.applications)} aplikasi")
            self._populate_list()

        self._run_task(
            "Perbarui katalog",
            self.service.refresh,
            succeeded,
            lambda error: QMessageBox.warning(
                self, "Katalog belum diperbarui",
                f"Metadata online tidak dapat diperbarui. Snapshot lokal tetap digunakan.\n\n{error}",
            ),
        )

    def _download_source(self) -> None:
        artifact = self.source_combo.currentData()
        if not isinstance(artifact, Artifact):
            return

        def succeeded(path: Path) -> None:
            box = QMessageBox(self)
            box.setWindowTitle("Source terverifikasi")
            box.setIcon(QMessageBox.Icon.Information)
            box.setText(f"{artifact.file} berhasil diunduh dan SHA-256 cocok.")
            box.setInformativeText(str(path))
            open_button = box.addButton("Buka folder", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.exec()
            if box.clickedButton() == open_button:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

        self._run_task(
            "Unduh dan verifikasi source",
            lambda: download_artifact(artifact),
            succeeded,
            lambda error: QMessageBox.warning(self, "Unduhan ditolak/gagal", error),
        )

    def _start_install(self) -> None:
        app = self.current_application
        artifact = getattr(self, "_install_artifact", None)
        if not app or not isinstance(artifact, Artifact):
            return
        warning = (
            f"{app.name} {artifact.version} berstatus {artifact.release_status.upper()}.\n\n"
            "Launcher akan membandingkan file dengan release.json dan SHA256SUMS sebelum "
            "menampilkan simulasi APT. Digest SHA-256 bukan tanda tangan penerbit. "
            "Pasang versi uji hanya jika kamu memahami risiko software Beta.\n\n"
            "Lanjutkan mengunduh dan memeriksa paket?"
        )
        choice = QMessageBox.warning(
            self,
            "Konfirmasi paket Beta",
            warning,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "Unduh dan verifikasi paket",
            lambda: download_artifact(artifact),
            lambda path: self._preview_and_confirm_install(artifact, path),
            lambda error: QMessageBox.warning(self, "Paket ditolak", error),
        )

    def _preview_and_confirm_install(self, artifact: Artifact, path: Path) -> None:
        def preview_ready(preview: InstallPreview) -> None:
            box = QMessageBox(self)
            box.setWindowTitle("Tinjau perubahan sistem")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(
                "APT sudah mensimulasikan transaksi tanpa mengubah sistem. "
                "Launcher juga menolak transaksi yang mengindikasikan penghapusan paket."
            )
            box.setInformativeText(
                f"Paket: {artifact.file}\nVersi: {artifact.version}\n"
                "Dependency dapat dipasang oleh APT. Tidak ada autoremove atau bulk upgrade."
            )
            box.setDetailedText(preview.output)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            box.setDefaultButton(QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("Minta otorisasi & pasang")
            box.button(QMessageBox.StandardButton.No).setText("Batal")
            if box.exec() != QMessageBox.StandardButton.Yes:
                self._set_status("Instalasi dibatalkan sebelum perubahan sistem.")
                return

            self._run_task(
                "Instalasi melalui Polkit",
                lambda: install_verified_artifact(
                    artifact,
                    path,
                    self.profile,
                    expected_preview=preview,
                ),
                self._installation_finished,
                lambda error: QMessageBox.warning(self, "Instalasi dihentikan", error),
            )

        self._run_task(
            "Simulasi transaksi APT",
            lambda: preview_installation(artifact, path, self.profile),
            preview_ready,
            lambda error: QMessageBox.warning(
                self, "Transaksi tidak aman/tidak tersedia",
                f"Launcher tidak melanjutkan instalasi.\n\n{error}",
            ),
        )

    def _installation_finished(self, result: InstallResult) -> None:
        if result.success:
            QMessageBox.information(
                self,
                "Package manager selesai",
                f"Perintah package manager selesai tanpa kode error.\n\n{result.output or result.package_path}",
            )
            self._set_status("Package manager selesai. Periksa aplikasi di menu desktop.")
        else:
            QMessageBox.warning(
                self,
                "Instalasi tidak berhasil",
                f"Package manager keluar dengan kode {result.return_code}.\n\n{result.output}",
            )
            self._set_status("Instalasi gagal; periksa pesan package manager di atas.")

    def _open_application(self) -> None:
        app = self.current_application
        executable = executable_for(app.id) if app else None
        if not executable:
            return
        from PySide6.QtCore import QProcess

        result = QProcess.startDetached(executable, [])
        started = result[0] if isinstance(result, tuple) else bool(result)
        if not started:
            QMessageBox.warning(self, "Tidak bisa membuka aplikasi", f"Gagal menjalankan {executable}.")

    def _open_source(self) -> None:
        app = self.current_application
        if not app or not app.source_url.startswith("https://"):
            return
        QDesktopServices.openUrl(QUrl(app.source_url))


def main() -> int:
    try:
        service = CatalogService()
        service.load()
    except CatalogError as exc:
        print(f"Launcher tidak bisa memuat katalog lokal: {exc}", file=sys.stderr)
        return 1

    application = QApplication(sys.argv)
    application.setApplicationName("Linux Software Lab Center")
    application.setOrganizationName("Linux Software Lab")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    try:
        window = MainWindow(service=service)
    except CatalogError as exc:
        QMessageBox.critical(None, "Katalog tidak valid", str(exc))
        return 1
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
