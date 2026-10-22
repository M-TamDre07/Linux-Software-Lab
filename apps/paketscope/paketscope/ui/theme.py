"""Locked visual system for the PaketScope desktop interface.

Keep this design aligned with docs/DESIGN_SYSTEM_LOCK.md. Functional or security
updates must not independently alter visual styling.
"""

COLUMNS = ("Nama aplikasi / paket", "Versi", "Sumber", "ID paket", "Asal / cabang")

APP_QSS = """
QMainWindow, QWidget#root {
    background: #f2f1ee;
    color: #171715;
}
QWidget {
    font-family: "Inter", "Noto Sans", sans-serif;
    font-size: 13px;
}
QFrame#topbar, QFrame#stat, QFrame#panel {
    background: #f8f7f4;
    border: 1px solid #d5d4ce;
    border-radius: 0;
}
QLabel#eyebrow, QLabel#mono {
    color: #686863;
    font-family: "Noto Sans Mono", monospace;
    font-size: 10px;
    letter-spacing: 1px;
}
QLabel#title {
    color: #171715;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -1px;
}
QLabel#stat-value {
    color: #171715;
    font-size: 24px;
    font-weight: 600;
}
QLabel#body-muted { color: #686863; }
QLineEdit, QComboBox {
    background: #f8f7f4;
    color: #171715;
    border: 1px solid #aaa9a2;
    border-radius: 0;
    padding: 9px 11px;
    min-height: 20px;
    selection-background-color: #d5d4ce;
}
QLineEdit:focus, QComboBox:focus, QTableView:focus {
    border: 1px solid #171715;
}
QPushButton {
    background: #171715;
    color: #f2f1ee;
    border: 1px solid #171715;
    border-radius: 0;
    padding: 10px 13px;
    font-family: "Noto Sans Mono", monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .5px;
}
QPushButton:hover { background: #41413d; border-color: #41413d; }
QPushButton:pressed { background: #686863; }
QPushButton:disabled {
    background: #e2e1dc;
    border-color: #d5d4ce;
    color: #92918b;
}
QPushButton#secondary {
    background: transparent;
    color: #171715;
    border-color: #aaa9a2;
}
QPushButton#secondary:hover {
    background: #e4e3de;
    border-color: #686863;
}
QTableView {
    background: #f8f7f4;
    alternate-background-color: #eae9e5;
    color: #171715;
    border: 1px solid #d5d4ce;
    border-radius: 0;
    gridline-color: #d5d4ce;
    selection-background-color: #d5d4ce;
    selection-color: #171715;
    outline: none;
}
QHeaderView::section {
    background: #eae9e5;
    color: #686863;
    border: none;
    border-bottom: 1px solid #d5d4ce;
    padding: 11px 9px;
    font-family: "Noto Sans Mono", monospace;
    font-size: 10px;
    font-weight: 700;
}
QScrollBar:vertical {
    background: #eae9e5;
    width: 9px;
    margin: 0;
    border-radius: 0;
}
QScrollBar::handle:vertical {
    background: #aaa9a2;
    min-height: 25px;
    border-radius: 0;
}
QScrollBar::handle:vertical:hover { background: #686863; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""