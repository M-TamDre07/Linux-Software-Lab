from paketscope.domain import parse_dpkg_output, parse_flatpak_output, InventorySnapshot


def test_parse_dpkg_only_keeps_installed_rows():
    output = (
        "bash\t5.2.15\tinstalled\n"
        "broken\t1.0\tconfig-files\n"
        "\t1.0\tinstalled\n"
        "python3\t3.11.2\tinstalled\n"
        "malformed row\n"
    )
    rows = parse_dpkg_output(output)
    assert [row.identifier for row in rows] == ["bash", "python3"]
    assert all(row.source == "APT / dpkg" for row in rows)


def test_parse_flatpak_rows_and_missing_version():
    output = (
        "org.example.Editor\tExample Editor\t1.2\tstable\tflathub\n"
        "org.example.Player\tPlayer\t\tstable\tflathub\n"
        "bad\ttoo\tshort\n"
    )
    rows = parse_flatpak_output(output)
    assert len(rows) == 2
    assert rows[0].name == "Example Editor"
    assert rows[1].version == "—"
    assert rows[0].origin == "flathub"


def test_snapshot_sorts_consistently_and_records_diagnostics():
    snapshot = InventorySnapshot.create(
        parse_dpkg_output("zeta\t1\tinstalled\nAlpha\t2\tinstalled\n"),
        ["flatpak is not installed"],
    )
    assert [row.name for row in snapshot.applications] == ["Alpha", "zeta"]
    assert snapshot.diagnostics == ("flatpak is not installed",)
    assert snapshot.collected_at.endswith("+00:00")


def test_parse_dpkg_keeps_package_classification_and_architecture():
    output = (
        "libc6:amd64\\t2.36\\tinstalled\\tlibs\\trequired\\tyes\\tamd64\\n"
        "sample-app\\t1.0\\tinstalled\\tutils\\toptional\\tno\\tall\\n"
    )
    rows = parse_dpkg_output(output)

    assert rows[0].identifier == "libc6:amd64"
    assert rows[0].section == "libs"
    assert rows[0].priority == "required"
    assert rows[0].essential is True
    assert rows[0].architecture == "amd64"
    assert rows[1].essential is False


def test_parse_flatpak_extended_metadata_and_skip_header_row():
    output = (
        "Application ID\\tName\\tVersion\\tBranch\\tOrigin\\tDescription\\n"
        "org.example.Editor\\tExample Editor\\t1.2\\tstable\\tflathub\\tA local text editor\\n"
    )
    rows = parse_flatpak_output(output)

    assert len(rows) == 1
    assert rows[0].name == "Example Editor"
    assert rows[0].origin == "flathub"
    assert rows[0].description == "A local text editor"
