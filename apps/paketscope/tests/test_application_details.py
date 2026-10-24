from paketscope.application_details import (
    inspect_application,
    parse_apt_policy_origins,
    parse_control_fields,
)
from paketscope.commands import CommandResult
from paketscope.domain import InstalledApplication


def command_result(argv, stdout="", stderr="", returncode=0):
    return CommandResult(tuple(argv), returncode, stdout, stderr)


def test_parse_control_fields_preserves_long_description_and_metadata():
    fields = parse_control_fields(
        "Package: example-editor\n"
        "Status: install ok installed\n"
        "Priority: optional\n"
        "Description: A simple editor\n"
        " Supports editing text.\n"
        " .\n"
        " Includes syntax highlighting.\n"
    )

    assert fields["Package"] == "example-editor"
    assert fields["Status"] == "install ok installed"
    assert fields["Description"] == "A simple editor\nSupports editing text.\n\nIncludes syntax highlighting."


def test_apt_policy_origin_only_reports_repository_for_installed_version():
    policy = (
        "example-editor:\n"
        "  Installed: 1.0\n"
        "  Candidate: 2.0\n"
        "  Version table:\n"
        "     2.0 500\n"
        "        500 https://repo.example.invalid stable/main amd64 Packages\n"
        " *** 1.0 100\n"
        "        100 /var/lib/dpkg/status\n"
        "        100 https://old.example.invalid stable/main amd64 Packages\n"
    )

    assert parse_apt_policy_origins(policy, "1.0") == (
        "https://old.example.invalid stable/main amd64 Packages",
    )


def test_apt_details_displays_package_description_and_current_repo_origin(monkeypatch):
    control = (
        "Package: example-editor\n"
        "Status: install ok installed\n"
        "Version: 1.0\n"
        "Section: editors\n"
        "Priority: optional\n"
        "Essential: no\n"
        "Architecture: amd64\n"
        "Maintainer: Example Maintainer\n"
        "Homepage: https://example.invalid\n"
        "Description: A local text editor\n"
        " Supports plain text editing and source files.\n"
    )
    policy = (
        "example-editor:\n"
        "  Installed: 1.0\n"
        "  Candidate: 1.0\n"
        "  Version table:\n"
        " *** 1.0 500\n"
        "        500 https://repo.example.invalid stable/main amd64 Packages\n"
        "        100 /var/lib/dpkg/status\n"
    )
    calls = []

    def fake_run(argv, timeout):
        calls.append(tuple(argv))
        if argv[:2] == ["dpkg-query", "-s"]:
            return command_result(argv, control)
        if argv[:2] == ["apt-cache", "policy"]:
            return command_result(argv, policy)
        if argv[:2] == ["dpkg-query", "-L"]:
            return command_result(argv, "")
        raise AssertionError(f"Unexpected command: {argv}")

    monkeypatch.setattr("paketscope.application_details.run_command", fake_run)
    app = InstalledApplication(
        name="example-editor",
        version="1.0",
        source="APT / dpkg",
        identifier="example-editor",
    )

    details = inspect_application(app)
    rendered = details.to_text()

    assert details.manager == "APT / dpkg"
    assert details.package_kind == "Aplikasi / utilitas"
    assert details.origin == "https://repo.example.invalid stable/main amd64 Packages"
    assert "A local text editor" in details.description
    assert "ini bukan bukti historis" in details.origin_note
    assert "FUNGSI / DESKRIPSI MENURUT METADATA SUMBER" in rendered
    assert "Repositori yang saat ini menyediakan versi terpasang" in rendered
    assert any(call[:2] == ("apt-cache", "policy") for call in calls)


def test_apt_details_rejects_untrusted_package_identifier_before_commands(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No commands should run for an invalid package ID.")

    monkeypatch.setattr("paketscope.application_details.run_command", fail_if_called)
    app = InstalledApplication(
        name="bad",
        version="1",
        source="APT / dpkg",
        identifier="example;touch-/tmp/file",
    )

    try:
        inspect_application(app)
    except ValueError as exc:
        assert "ID paket APT tidak valid" in str(exc)
    else:
        raise AssertionError("Invalid package identifier must be rejected.")


def test_flatpak_details_use_local_description_origin_and_permissions(monkeypatch):
    metadata = {
        "--show-ref": "app/org.example.Editor/x86_64/stable",
        "--show-origin": "flathub",
        "--show-location": "/var/lib/flatpak/app/org.example.Editor",
        "--show-commit": "abc123",
        "--show-permissions": "[Context]\nshared=network;ipc;\n",
        "--show-runtime": "org.freedesktop.Platform/x86_64/24.08",
    }
    monkeypatch.setattr(
        "paketscope.application_details._flatpak_value",
        lambda app_id, option: metadata.get(option, ""),
    )
    app = InstalledApplication(
        name="Example Editor",
        version="1.4",
        source="Flatpak",
        identifier="org.example.Editor",
        branch="stable",
        origin="flathub",
        description="A graphical text editor.",
    )

    details = inspect_application(app)

    assert details.name == "Example Editor"
    assert details.package_kind == "Aplikasi Flatpak"
    assert details.origin == "flathub"
    assert details.architecture == "x86_64"
    assert details.runtime == "org.freedesktop.Platform/x86_64/24.08"
    assert "A graphical text editor." in details.to_text()
    assert "shared=network;ipc;" in details.permissions


def test_flatpak_details_reject_invalid_application_id(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No Flatpak command should run for an invalid ID.")

    monkeypatch.setattr("paketscope.application_details.run_command", fail_if_called)
    app = InstalledApplication("Bad app", "1", "Flatpak", "org.example/../../etc")
    try:
        inspect_application(app)
    except ValueError as exc:
        assert "ID aplikasi Flatpak tidak valid" in str(exc)
    else:
        raise AssertionError("Invalid Flatpak identifier must be rejected.")
