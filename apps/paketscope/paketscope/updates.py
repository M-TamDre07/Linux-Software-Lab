"""User-triggered update checks; these functions never install anything."""
from __future__ import annotations

from dataclasses import dataclass

from .commands import CommandTimedOut, CommandUnavailable, run_command


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    apt_updates: tuple[str, ...]
    flatpak_updates: tuple[str, ...]
    diagnostics: tuple[str, ...]


def check_updates() -> UpdateCheckResult:
    apt_updates = []
    flatpak_updates = []
    diagnostics = []

    try:
        result = run_command(["apt", "list", "--upgradable"], timeout=20.0)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.casefold().startswith("listing...") and "/" in line:
                    apt_updates.append(line.split("/", 1)[0])
        else:
            diagnostics.append("Pemeriksaan APT gagal (kode " + str(result.returncode) + ").")
    except (CommandUnavailable, CommandTimedOut) as exc:
        diagnostics.append("APT: " + str(exc))

    try:
        # This may contact configured Flatpak remotes; only run after an explicit user action.
        result = run_command([
            "flatpak", "remote-ls", "--updates", "--app", "--columns=application,name",
        ], timeout=45.0)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                columns = line.split("\t")
                if columns and columns[0].strip():
                    flatpak_updates.append(columns[0].strip())
        else:
            details = result.stderr.strip().splitlines()
            diagnostics.append("Pemeriksaan Flatpak tidak selesai: " + (details[-1][:180] if details else "perintah gagal."))
    except (CommandUnavailable, CommandTimedOut) as exc:
        diagnostics.append("Flatpak: " + str(exc))

    return UpdateCheckResult(
        apt_updates=tuple(dict.fromkeys(apt_updates)),
        flatpak_updates=tuple(dict.fromkeys(flatpak_updates)),
        diagnostics=tuple(diagnostics),
    )
