import csv
import os
import stat

import pytest

from paketscope.domain import InstalledApplication
from paketscope.services import PaketScopeService


def example_application(name: str = "Firefox") -> InstalledApplication:
    return InstalledApplication(
        name=name,
        version="1.0",
        source="APT / dpkg",
        identifier="firefox",
    )


def test_csv_export_uses_safe_values_and_selected_rows(tmp_path):
    service = PaketScopeService()
    destination = tmp_path / "visible.csv"

    count = service.export_csv(
        [example_application("=1+1"), example_application("Firefox")],
        destination,
    )

    assert count == 2
    with destination.open(encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert records[0]["name"] == "'=1+1"
    assert records[1]["name"] == "Firefox"


def test_encrypted_backup_round_trip(tmp_path):
    service = PaketScopeService()
    destination = tmp_path / "inventory.psbackup"
    application = example_application()

    count = service.create_encrypted_backup(
        [application], destination, "a sufficiently long passphrase"
    )

    assert count == 1
    assert service.restore_backup(
        destination, "a sufficiently long passphrase"
    ) == [application.to_record()]


def test_backup_rejects_empty_inventory(tmp_path):
    service = PaketScopeService()
    with pytest.raises(ValueError, match="Pindai inventaris"):
        service.create_encrypted_backup([], tmp_path / "empty.psbackup", "a sufficiently long passphrase")


def test_restored_json_is_written_explicitly(tmp_path):
    service = PaketScopeService()
    destination = tmp_path / "restored.json"
    records = [{"name": "Firefox", "version": "1.0"}]

    assert service.export_restored_json(destination, records) == 1
    assert '"Firefox"' in destination.read_text(encoding="utf-8")
    if os.name == "posix":
        assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_empty_csv_export_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Tidak ada aplikasi"):
        PaketScopeService().export_csv([], tmp_path / "empty.csv")
