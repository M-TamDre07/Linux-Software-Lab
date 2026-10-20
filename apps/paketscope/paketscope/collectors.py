"""Read-only collectors for APT/dpkg and Flatpak."""
from __future__ import annotations

from .commands import CommandTimedOut, CommandUnavailable, run_command
from .domain import InventorySnapshot, parse_dpkg_output, parse_flatpak_output


def collect_inventory() -> InventorySnapshot:
    applications = []
    diagnostics = []

    dpkg_format = "$" + "{binary:Package}" + "\t" + "$" + "{Version}" + "\t" + "$" + "{db:Status-Status}" + "\n"
    try:
        result = run_command(["dpkg-query", "-W", "-f=" + dpkg_format])
        if result.returncode == 0:
            applications.extend(parse_dpkg_output(result.stdout))
        else:
            diagnostics.append("Inventaris APT tidak tersedia: dpkg-query mengembalikan kode " + str(result.returncode) + ".")
    except (CommandUnavailable, CommandTimedOut) as exc:
        diagnostics.append(str(exc))

    try:
        result = run_command([
            "flatpak", "list", "--app",
            "--columns=application,name,version,branch,origin",
        ], timeout=25.0)
        if result.returncode == 0:
            applications.extend(parse_flatpak_output(result.stdout))
        else:
            details = result.stderr.strip().splitlines()
            diagnostics.append("Inventaris Flatpak tidak tersedia: " + (details[-1][:180] if details else "perintah gagal."))
    except (CommandUnavailable, CommandTimedOut) as exc:
        diagnostics.append(str(exc))

    if not applications and not diagnostics:
        diagnostics.append("Tidak ada aplikasi yang ditemukan oleh sumber paket yang didukung.")
    return InventorySnapshot.create(applications, diagnostics)
