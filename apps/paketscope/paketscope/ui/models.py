"""Qt table models for the installed-application inventory."""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt

from ..domain import InstalledApplication


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
