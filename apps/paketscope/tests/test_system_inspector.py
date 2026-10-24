import pytest

from paketscope import admin_helper
from paketscope.system_inspector import (
    run_privileged_metadata_inspection,
    run_privileged_text_file_read,
    validate_admin_payload,
    validate_admin_text_request,
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
    assert isinstance(result["mounts"], list)
    assert "services" in result
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
    assert "baca-file terpisah" in result["notice"]


def test_admin_payload_rejects_unknown_schema():
    with pytest.raises(RuntimeError, match="format"):
        validate_admin_payload({"schema_version": 2, "entries": []})


def test_admin_helper_does_not_accept_arbitrary_actions(capsys):
    result = admin_helper.main(["--read", "/etc/shadow"])
    assert result == 2
    assert "Supported actions" in capsys.readouterr().err


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


def test_admin_payload_rejects_traversal_paths():
    result = validate_admin_payload({
        "schema_version": 1,
        "entries": [
            {"path": "/etc/../root/.ssh/id_ed25519", "owner_uid": 0,
             "group_gid": 0, "size_bytes": 10},
        ],
        "diagnostics": [],
    })
    assert result["entries"] == []


def test_admin_helper_reads_only_bounded_utf8_text_from_allowlisted_roots():
    path = admin_helper._validate_text_file_path("/etc/passwd")
    assert str(path) == "/etc/passwd"
    result = admin_helper.read_text_file("/etc/passwd")
    assert result["scope"] == "selected-text-file-read-only"
    assert result["path"] == "/etc/passwd"
    assert isinstance(result["content"], str)
    assert "root:" in result["content"]
    assert result["size_bytes"] <= admin_helper.MAX_TEXT_FILE_BYTES


@pytest.mark.parametrize(
    "path",
    [
        "etc/passwd",
        "/etc/../etc/passwd",
        "/etc/shadow",
        "/etc/ssl/private/server.key",
        "/tmp/unrelated.conf",
        "/root/.ssh/id_ed25519",
    ],
)
def test_admin_helper_rejects_sensitive_or_out_of_allowlist_file_paths(path):
    with pytest.raises(ValueError):
        admin_helper._validate_text_file_path(path)


def test_client_side_system_text_file_validation_rejects_sensitive_paths():
    assert validate_admin_text_request("/etc/passwd") == "/etc/passwd"
    for path in (
        "etc/passwd",
        "/etc/../etc/passwd",
        "/etc/shadow",
        "/etc/ssh/ssh_host_ed25519_key",
        "/tmp/file.txt",
    ):
        with pytest.raises(ValueError):
            validate_admin_text_request(path)


def test_privileged_text_read_rejects_paths_before_polkit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "paketscope.system_inspector.TRUSTED_HELPER",
        tmp_path / "missing" / "admin_helper.py",
    )
    with pytest.raises(ValueError, match="di direktori sistem"):
        run_privileged_text_file_read("/tmp/secret.txt")
