"""Read-only UI for application identity, source, and purpose metadata."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from ..application_details import ApplicationDetails


class ApplicationDetailsDialog(QDialog):
    """Show source-attributed metadata without launching or modifying the app."""

    def __init__(self, details: ApplicationDetails, parent=None) -> None:
        super().__init__(parent)
        self.details = details
        self.setWindowTitle(f"PaketScope · Detail {details.name or details.identifier}")
        self.setMinimumSize(720, 520)
        self.resize(880, 680)

        root = QVBoxLayout(self)
        heading = QLabel(details.name or details.identifier)
        heading.setObjectName("title")
        root.addWidget(heading)

        subtitle = QLabel(
            f"{details.manager}  /  {details.package_kind}  /  {details.identifier}"
        )
        subtitle.setObjectName("body-muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.report.setPlainText(details.to_text())
        self.report.setAccessibleName("Rincian sumber, jenis, dan fungsi aplikasi")
        root.addWidget(self.report, 1)

        footer = QHBoxLayout()
        self.status = QLabel("Metadata lokal saja · tidak ada aplikasi yang dijalankan.")
        self.status.setObjectName("body-muted")
        footer.addWidget(self.status, 1)
        self.copy_button = QPushButton("Salin laporan")
        self.copy_button.setObjectName("secondary")
        self.copy_button.clicked.connect(self.copy_report)
        footer.addWidget(self.copy_button)
        self.close_button = QPushButton("Tutup")
        self.close_button.clicked.connect(self.accept)
        footer.addWidget(self.close_button)
        root.addLayout(footer)

    def copy_report(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            QMessageBox.information(self, "Salin laporan", "Clipboard tidak tersedia pada sesi desktop ini.")
            return
        clipboard.setText(self.report.toPlainText())
        self.status.setText("Rincian disalin ke clipboard.")
