from PySide6.QtCore import Qt

from paketscope.domain import InstalledApplication
from paketscope.ui.models import InventoryModel, InventoryProxy


def application(name: str, source: str, identifier: str) -> InstalledApplication:
    return InstalledApplication(
        name=name,
        version="1.0",
        source=source,
        identifier=identifier,
    )


def test_inventory_model_exposes_consistent_rows_and_headers():
    model = InventoryModel()
    firefox = application("Firefox", "APT / dpkg", "firefox")
    flatpak_app = application("Music", "Flatpak", "org.example.Music")
    model.set_applications((firefox, flatpak_app))

    assert model.rowCount() == 2
    assert model.columnCount() == 5
    assert model.data(model.index(0, 0)) == "Firefox"
    assert model.data(model.index(0, 3)) == "firefox"
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Nama aplikasi / paket"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.ToolTipRole) == (
        "Firefox\\nID: firefox\\nSumber: APT / dpkg"
    )


def test_inventory_proxy_combines_text_and_source_filters():
    model = InventoryModel()
    model.set_applications((
        application("Firefox", "APT / dpkg", "firefox"),
        application("Music", "Flatpak", "org.example.Music"),
        application("Firefox Developer Edition", "Flatpak", "org.example.FirefoxDev"),
    ))
    proxy = InventoryProxy()
    proxy.setSourceModel(model)

    assert proxy.rowCount() == 3

    proxy.set_source_filter("Flatpak")
    assert proxy.rowCount() == 2

    proxy.set_query("developer")
    assert proxy.rowCount() == 1
    assert proxy.data(proxy.index(0, 0)) == "Firefox Developer Edition"

    proxy.set_query("not-installed")
    assert proxy.rowCount() == 0
