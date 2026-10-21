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
    if action == "install" and package_name not in install:
        raise PackageOperationError(
            "APT tidak merencanakan pemasangan untuk paket itu. Paket mungkin sudah terpasang "
            "atau tidak tersedia pada indeks lokal."
        )
    if action in {"remove", "purge"} and package_name not in set(remove + purge):
        raise PackageOperationError("APT tidak merencanakan penghapusan paket yang dipilih.")
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


def apply_apt_action(action: str, package_name: str) -> CommandResult:
    """Execute an action only after explicit GUI confirmation.

    pkexec provides the desktop's polkit authentication prompt. The application
    itself is never run as root and does not use sudo or a shell.
    """
    if action not in ACTIONS:
        raise PackageOperationError("Jenis operasi paket tidak didukung.")
    package_name = validate_apt_package_name(package_name)
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
