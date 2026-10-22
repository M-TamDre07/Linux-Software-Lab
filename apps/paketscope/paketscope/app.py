"""Application entry point for PaketScope."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import __version__
from .ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PaketScope")
    app.setApplicationVersion(__version__)
    icon_path = Path(__file__).resolve().parent / "assets" / "paketscope.svg"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyle("Fusion")

    from .ui.theme import APP_QSS
    app.setStyleSheet(APP_QSS)

    window = MainWindow()
    window.show()
    QTimer.singleShot(100, window.refresh_inventory)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
