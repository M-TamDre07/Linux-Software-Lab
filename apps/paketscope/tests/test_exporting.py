from paketscope.exporting import csv_safe_record, csv_safe_value, write_private_file


def test_formula_like_cells_are_neutralized():
    for value in ("=1+1", "+SUM(A1:A2)", "-cmd", "@SUM(A1)", "  =1+1", "\t=1+1"):
        assert csv_safe_value(value).startswith("'")


def test_normal_values_are_not_modified():
    assert csv_safe_value("Firefox") == "Firefox"
    assert csv_safe_value("1.2.3") == "1.2.3"
    assert csv_safe_record({"name": "Firefox", "version": "1.2"}) == {
        "name": "Firefox",
        "version": "1.2",
    }


import os
import stat
import pytest


@pytest.mark.skipif(os.name != "posix", reason="Owner-only file mode is POSIX-specific.")
def test_private_file_is_written_with_owner_only_permissions(tmp_path):
    destination = tmp_path / "inventory.csv"
    destination.write_text("previous public content", encoding="utf-8")
    destination.chmod(0o644)

    write_private_file(destination, b"private inventory")

    assert destination.read_bytes() == b"private inventory"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".inventory.csv.*.tmp")) == []
