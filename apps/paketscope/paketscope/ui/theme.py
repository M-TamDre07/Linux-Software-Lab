"""Visual constants for the PaketScope Qt interface."""

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
