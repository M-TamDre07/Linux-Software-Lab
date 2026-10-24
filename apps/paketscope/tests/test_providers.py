from paketscope.domain import InstalledApplication
from paketscope.providers import ProviderResult
from paketscope.services import PaketScopeService


class InMemoryProvider:
    provider_id = "custom-demo"
    display_name = "Custom demo source"

    def collect(self):
        return ProviderResult((
            InstalledApplication(
                name="Example App",
                version="2.1",
                source="Custom demo source",
                identifier="custom.example.app",
                origin="local-demo-index",
                description="A test record emitted by an explicitly registered provider.",
            ),
        ))


class BrokenProvider:
    provider_id = "broken-demo"
    display_name = "Broken demo source"

    def collect(self):
        raise RuntimeError("private exception details should not be surfaced")


def test_service_accepts_an_explicit_custom_read_only_inventory_provider():
    service = PaketScopeService(inventory_providers=(InMemoryProvider(),))

    snapshot = service.scan_inventory()

    assert len(snapshot.applications) == 1
    app = snapshot.applications[0]
    assert app.source == "Custom demo source"
    assert app.origin == "local-demo-index"
    assert app.description.startswith("A test record")
    assert snapshot.diagnostics == ()


def test_failed_custom_provider_does_not_hide_other_registered_sources():
    service = PaketScopeService(
        inventory_providers=(BrokenProvider(), InMemoryProvider())
    )

    snapshot = service.scan_inventory()

    assert [app.source for app in snapshot.applications] == ["Custom demo source"]
    assert len(snapshot.diagnostics) == 1
    assert "Broken demo source" in snapshot.diagnostics[0]
    assert "private exception details" not in snapshot.diagnostics[0]
