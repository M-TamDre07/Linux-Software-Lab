"""Controlled APT package search and transaction helpers.

All operations are explicit, limited to a validated package identifier, and
previewed before a privileged transaction. This module never invokes a shell.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .commands import CommandResult, CommandTimedOut, CommandUnavailable, run_command


APT_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?$")
SEARCH_QUERY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _+.-]{0,79}$")
ACTIONS = frozenset({"install", "remove", "purge"})


class PackageOperationError(RuntimeError):
    """A package operation could not be safely prepared or completed."""


@dataclass(frozen=True, slots=True)
class AptSearchResult:
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class AptTransactionPreview:
    action: str
    package_name: str
    install: tuple[str, ...]
    remove: tuple[str, ...]
    purge: tuple[str, ...]
    output: str


def validate_apt_package_name(package_name: str) -> str:
    """Validate a package identifier before including it in an APT argv."""
    if not isinstance(package_name, str) or not APT_PACKAGE_RE.fullmatch(package_name):
        raise PackageOperationError("Nama paket APT tidak valid; tidak ada perintah yang dijalankan.")
    return package_name


def _matches_requested_package(requested: str, actual: str) -> bool:
    """Match unqualified Debian names against the architecture-qualified APT output."""
    if requested == actual:
        return True
    return ":" not in requested and actual.split(":", 1)[0] == requested


PROTECTED_PACKAGE_NAMES = frozenset({
    "apt", "base-files", "base-passwd", "bash", "coreutils", "dpkg",
    "init", "init-system-helpers", "libc6", "polkit", "python3",
    "python3-minimal", "sudo", "systemd", "systemd-sysv",
})


def _parse_control_fields(output: str) -> dict[str, str]:
    """Parse the field subset used by dpkg-query -s."""
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith((" ", "\\t")):
            continue
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def _ensure_removal_is_safe(package_name: str) -> None:
    """Fail closed if local dpkg metadata marks the target as system-critical."""
    base_name = package_name.split(":", 1)[0]
    if base_name in PROTECTED_PACKAGE_NAMES:
        raise PackageOperationError(
            f"Paket '{base_name}' dilindungi karena merupakan komponen dasar sistem."
        )
    try:
        result = run_command(["dpkg-query", "-s", package_name], timeout=15.0)
    except (CommandUnavailable, CommandTimedOut) as exc:
        raise PackageOperationError(
            "Tidak dapat memverifikasi prioritas paket; penghapusan dibatalkan demi keamanan."
        ) from exc
    if result.returncode != 0:
        raise PackageOperationError(
            "Metadata dpkg target tidak dapat diverifikasi; penghapusan dibatalkan."
        )
    fields = _parse_control_fields(result.stdout)
    if fields.get("Status", "").casefold() != "install ok installed":
        raise PackageOperationError("Paket bukan lagi paket terpasang; pindai ulang inventaris.")
    priority = fields.get("Priority", "").casefold()
    if not priority:
        raise PackageOperationError(
            "Prioritas paket tidak diketahui; penghapusan dibatalkan demi keamanan."
        )
    if fields.get("Essential", "").casefold() == "yes" or fields.get("Protected", "").casefold() == "yes":
        raise PackageOperationError(
            "Paket ditandai Essential/Protected oleh metadata sistem dan tidak dapat dihapus melalui PaketScope."
        )
    if priority in {"required", "important"}:
        raise PackageOperationError(
            f"Paket memiliki prioritas sistem '{priority}' dan dilindungi dari remove/purge melalui PaketScope."
        )


def search_apt_packages(query: str, limit: int = 60) -> tuple[AptSearchResult, ...]:
    """Search the local APT package index; no network refresh is triggered."""
    if not isinstance(query, str):
        raise PackageOperationError("Kata pencarian tidak valid.")
    query = query.strip()
    if not SEARCH_QUERY_RE.fullmatch(query):
        raise PackageOperationError(
            "Gunakan 1–80 karakter berupa huruf, angka, spasi, titik, garis bawah, +, atau -."
        )
    escaped_query = re.sub(r"([.+])", r"\\\1", query)
    try:
        result = run_command(
            ["apt-cache", "search", "--names-only", escaped_query],
            timeout=30.0,
        )
    except (CommandUnavailable, CommandTimedOut) as exc:
        raise PackageOperationError(str(exc)) from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise PackageOperationError(
            "Pencarian APT gagal: " + (detail[-1][:200] if detail else "apt-cache mengembalikan galat.")
        )

    matches: list[AptSearchResult] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        name, separator, description = line.partition(" - ")
        name = name.strip()
        if not separator or not APT_PACKAGE_RE.fullmatch(name) or name in seen:
            continue
        seen.add(name)
        matches.append(AptSearchResult(name=name, description=description.strip() or "Tanpa deskripsi"))
        if len(matches) >= max(1, min(int(limit), 100)):
            break
    return tuple(matches)


def preview_apt_action(action: str, package_name: str) -> AptTransactionPreview:
    """Ask APT to simulate an operation and summarize package changes."""
    if action not in ACTIONS:
        raise PackageOperationError("Jenis operasi paket tidak didukung.")
    package_name = validate_apt_package_name(package_name)
    argv = [
        "apt-get", "--simulate", "-o", "Dpkg::Use-Pty=0",
        "--no-install-recommends",
    ]
    if action == "install":
        # Do not let an install request silently remove unrelated packages.
        argv.append("--no-remove")
    argv.extend([action, package_name])
    try:
        result = run_command(argv, timeout=45.0)
    except (CommandUnavailable, CommandTimedOut) as exc:
        raise PackageOperationError(str(exc)) from exc
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        detail = output.splitlines()
        raise PackageOperationError(
            "APT tidak dapat menyiapkan simulasi: "
            + (detail[-1][:220] if detail else "perintah simulasi gagal.")
        )

    install = tuple(dict.fromkeys(re.findall(r"^Inst\s+([^\s(]+)", result.stdout, re.MULTILINE)))
    remove = tuple(dict.fromkeys(re.findall(r"^Remv\s+([^\s(]+)", result.stdout, re.MULTILINE)))
    purge = tuple(dict.fromkeys(re.findall(r"^Purg\s+([^\s(]+)", result.stdout, re.MULTILINE)))
    if action == "install" and (remove or purge):
        raise PackageOperationError("Simulasi pemasangan mencoba menghapus paket lain; operasi ditolak.")
    if action == "install" and not any(_matches_requested_package(package_name, item) for item in install):
        raise PackageOperationError(
            "APT tidak merencanakan pemasangan untuk paket itu. Paket mungkin sudah terpasang "
            "atau tidak tersedia pada indeks lokal."
        )
    if action in {"remove", "purge"}:
        changed_packages = tuple(dict.fromkeys(remove + purge))
        if not any(_matches_requested_package(package_name, item) for item in changed_packages):
            raise PackageOperationError("APT tidak merencanakan penghapusan paket yang dipilih.")
        other_packages = tuple(
            item for item in changed_packages
            if not _matches_requested_package(package_name, item)
        )
        if other_packages:
            sample = ", ".join(other_packages[:5])
            raise PackageOperationError(
                "Transaksi remove/purge berisiko ikut menghapus paket lain; ditolak secara otomatis. "
                f"Contoh paket lain: {sample}."
            )
        _ensure_removal_is_safe(package_name)
    if not (install or remove or purge):
        raise PackageOperationError("Simulasi APT tidak menunjukkan perubahan; operasi dibatalkan.")

    return AptTransactionPreview(
        action=action,
        package_name=package_name,
        install=install,
        remove=remove,
        purge=purge,
        output=output,
    )


def apply_apt_action(
    action: str,
    package_name: str,
    approved_preview: AptTransactionPreview | None = None,
) -> CommandResult:
    """Execute a fresh, still-matching transaction through Polkit.

    Re-simulation closes the gap between the plan displayed in the UI and the
    moment privilege is requested. If the plan differs, the operation must be
    reviewed and confirmed again.
    """
    if action not in ACTIONS:
        raise PackageOperationError("Jenis operasi paket tidak didukung.")
    package_name = validate_apt_package_name(package_name)
    current_preview = preview_apt_action(action, package_name)
    if approved_preview is not None:
        if (
            approved_preview.action != action
            or approved_preview.package_name != package_name
            or approved_preview.install != current_preview.install
            or approved_preview.remove != current_preview.remove
            or approved_preview.purge != current_preview.purge
        ):
            raise PackageOperationError(
                "Rencana APT berubah sejak ditinjau. Tidak ada perubahan dilakukan; "
                "pindai ulang dan tinjau rencana terbaru."
            )
    argv = [
        "pkexec", "/usr/bin/env", "DEBIAN_FRONTEND=noninteractive",
        "/usr/bin/apt-get", "--assume-yes", "-o", "Dpkg::Use-Pty=0",
        "--no-install-recommends",
    ]
    if action == "install":
        argv.append("--no-remove")
    argv.extend([action, package_name])
    try:
        result = run_command(argv, timeout=900.0)
    except (CommandUnavailable, CommandTimedOut) as exc:
        raise PackageOperationError(str(exc)) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        if result.returncode in {126, 127}:
            message = "Autentikasi dibatalkan atau pkexec tidak dapat menjalankan APT."
        else:
            message = detail[-1][:240] if detail else f"APT gagal dengan kode {result.returncode}."
        raise PackageOperationError(message)
    return result
