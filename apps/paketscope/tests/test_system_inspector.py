import json

import pytest

from paketscope import admin_helper
from paketscope.system_inspector import (
    run_privileged_metadata_inspection,
    validate_admin_payload,
    collect_system_snapshot,
)


def test_system_snapshot_is_read_only_structured_data():
    result = collect_system_snapshot()

    assert result["schema_version"] == 1
    assert result["mode"] == "read-only / user"
    assert result["operating_system"]
    assert result["kernel"]["release"]
    assert "logical_processors" in result["cpu"]
    assert isinstance(result["disk_usage"], list)
    assert "tidak dikirim ke jaringan" in result["notice"]


def test_admin_payload_accepts_only_fixed_metadata_roots():
    result = validate_admin_payload({
        "schema_version": 1,
        "scope": "metadata-only",
        "entries": [
            {"path": "/etc/os-release", "type": "file", "mode": "-rw-r--r--",
             "owner_uid": 0, "group_gid": 0, "size_bytes": 100},
            {"path": "/root/.ssh/id_ed25519", "type": "file", "mode": "-rw-------",
             "owner_uid": 0, "group_gid": 0, "size_bytes": 100},
            {"path": "/etc/invalid", "type": "file", "owner_uid": "bad"},
        ],
        "diagnostics": [],
    })

    assert [item["path"] for item in result["entries"]] == ["/etc/os-release"]
    assert result["scope"] == "metadata-only"
    assert "private key" in result["notice"]


def test_admin_payload_rejects_unknown_schema():
    with pytest.raises(RuntimeError, match="format"):
        validate_admin_payload({"schema_version": 2, "entries": []})


def test_admin_helper_does_not_accept_arbitrary_actions(capsys):
    result = admin_helper.main(["--read", "/etc/shadow"])
    assert result == 2
    assert "fixed --metadata" in capsys.readouterr().err


def test_admin_helper_excludes_secret_locations_and_names():
    assert admin_helper._excluded(__import__("pathlib").Path("/etc/shadow"))
    assert admin_helper._excluded(__import__("pathlib").Path("/etc/ssl/private/server.key"))
    assert not admin_helper._excluded(__import__("pathlib").Path("/etc/os-release"))


def test_privileged_mode_requires_trusted_installed_helper(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "paketscope.system_inspector.TRUSTED_HELPER",
        tmp_path / "missing" / "admin_helper.py",
    )
    with pytest.raises(RuntimeError, match="paket Debian terpasang"):
        run_privileged_metadata_inspection()
