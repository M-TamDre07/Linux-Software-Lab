"""Local, read-only application identity and provenance details.

APT repository data describes where a version is available in the current local
index; it cannot prove the historical repository from which a package was
originally installed. Desktop entries are parsed as data and their Exec fields
are never launched.
"""
from __future__ import annotations

import configparser
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from .commands import CommandTimedOut, CommandUnavailable, run_command
from .domain import InstalledApplication
from .package_manager import APT_PACKAGE_RE

FLATPAK_ID_RE = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$")
MAX_DESKTOP_FILE_BYTES = 64 * 1024
MAX_LAUNCHERS = 12
MAX_DESCRIPTION_CHARS = 6000
PROTECTED_PRIORITIES = frozenset({"required", "important"})


@dataclass(frozen=True, slots=True)
class DesktopLauncher:
    path: str
    name: str = ""
    generic_name: str = ""
    comment: str = ""
    categories: str = ""
    keywords: str = ""


@dataclass(frozen=True, slots=True)
class ApplicationDetails:
    name: str
    identifier: str
    version: str
    manager: str
    package_kind: str
    origin: str
    origin_note: str
    description: str
    maintainer: str = ""
    homepage: str = ""
    section: str = ""
    priority: str = ""
    essential: str = ""
    architecture: str = ""
    installation: str = ""
    launchers: tuple[DesktopLauncher, ...] = ()
    runtime: str = ""
    commit: str = ""
    location: str = ""
    permissions: str = ""
    notes: tuple[str, ...] = ()

    def to_text(self) -> str:
        rows = [
            "IDENTITAS APLIKASI / PAKET",
            f"Nama: {self.name or 'Tidak tersedia'}",
            f"ID paket/aplikasi: {self.identifier}",
            f"Versi terpasang: {self.version or 'Tidak tersedia'}",
            f"Pengelola paket: {self.manager}",
            f"Jenis: {self.package_kind}",
            f"Asal yang diketahui: {self.origin or 'Tidak dapat ditentukan'}",
            f"Penjelasan asal: {self.origin_note}",
        ]
        if self.installation:
            rows.append(f"Lokasi instalasi: {self.installation}")
        if self.architecture:
            rows.append(f"Arsitektur: {self.architecture}")
        if self.section:
            rows.append(f"Section: {self.section}")
        if self.priority:
            rows.append(f"Prioritas paket: {self.priority}")
        if self.essential:
            rows.append(f"Essential: {self.essential}")
        if self.maintainer:
            rows.append(f"Maintainer: {self.maintainer}")
        if self.homepage:
            rows.append(f"Homepage metadata: {self.homepage}")
        if self.runtime:
            rows.append(f"Runtime Flatpak: {self.runtime}")
        if self.commit:
            rows.append(f"Commit terpasang: {self.commit}")
        if self.location:
            rows.append(f"Lokasi Flatpak: {self.location}")
        rows.extend(["", "FUNGSI / DESKRIPSI MENURUT METADATA SUMBER", self.description or (
            "Deskripsi fungsi tidak tersedia dalam metadata lokal yang dapat dibaca."
        )])
        if self.launchers:
            rows.extend(["", "ENTRI APLIKASI DESKTOP"])
            for launcher in self.launchers:
                rows.append(f"- Nama: {launcher.name or '(nama tidak ditetapkan)'}")
                if launcher.generic_name:
                    rows.append(f"  Jenis aplikasi: {launcher.generic_name}")
                if launcher.comment:
                    rows.append(f"  Keterangan: {launcher.comment}")
                if launcher.categories:
                    rows.append(f"  Kategori: {launcher.categories}")
                if launcher.keywords:
                    rows.append(f"  Kata kunci: {launcher.keywords}")
                rows.append(f"  File peluncur: {launcher.path}")
        elif self.manager == "APT / dpkg":
            rows.extend([
                "",
                "Tidak ditemukan file .desktop milik paket ini pada lokasi peluncur standar.",
                "Paket mungkin berupa pustaka, komponen sistem, layanan, atau alat baris perintah.",
            ])
        if self.permissions:
            rows.extend(["", "PERMISSION METADATA FLATPAK", self.permissions[:6000]])
            rows.append(
                "Catatan: permission yang dideklarasikan tidak selalu sama dengan izin efektif; "
                "konfigurasi dan override lokal dapat mengubahnya."
            )
        if self.notes:
            rows.extend(["", "CATATAN", *[f"- {note}" for note in self.notes]])
        rows.extend([
            "",
            "Sumber deskripsi ditampilkan apa adanya dari metadata lokal; PaketScope tidak "
            "menebak fungsi berdasarkan nama paket. File dan kode tidak dijalankan.",
        ])
        return "\n".join(rows)


def parse_control_fields(text: str) -> dict[str, str]:
    """Parse dpkg's control-format output, preserving continuation text."""
    fields: dict[str, str] = {}
    current_key = ""
    description_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and current_key:
            value = line[1:]
            if current_key == "Description":
                description_lines.append("" if value == "." else value)
            elif current_key in fields:
                fields[current_key] += "\n" + value
            continue
        key, separator, value = line.partition(":")
        if not separator:
            current_key = ""
            continue
        current_key = key.strip()
        value = value.strip()
        fields[current_key] = value
        if current_key == "Description":
            description_lines = [value]
    if description_lines:
        fields["Description"] = "\n".join(description_lines).strip()[:MAX_DESCRIPTION_CHARS]
    return fields


def parse_apt_policy_origins(output: str, installed_version: str) -> tuple[str, ...]:
    """Return repositories currently offering the exact installed version."""
    matches: list[str] = []
    current_version = ""
    in_installed_version = False
    version_header = re.compile(r"^\s*(?:\*{3}\s+)?(\S+)\s+(-?\d+)\s*$")
    source_line = re.compile(r"^\s+\d+\s+(.+?)\s*$")
    for line in output.splitlines():
        version_match = version_header.match(line)
        if version_match:
            current_version = version_match.group(1)
            in_installed_version = current_version == installed_version
            continue
        if not in_installed_version:
            continue
        source_match = source_line.match(line)
        if not source_match:
            continue
        source = source_match.group(1).strip()
        if source == "/var/lib/dpkg/status" or source.startswith("/var/lib/dpkg/status "):
            continue
        if source and source not in matches:
            matches.append(source[:400])
    return tuple(matches[:8])


def _read_desktop_launcher(path_text: str) -> DesktopLauncher | None:
    """Read only bounded .desktop metadata from standard system application dirs."""
    path = Path(path_text)
    allowed_roots = (Path("/usr/share/applications"), Path("/usr/local/share/applications"))
    if not path.is_absolute() or path.suffix.casefold() != ".desktop":
        return None
    if not any(path.is_relative_to(root) and path != root for root in allowed_roots):
        return None
    try:
        if path.is_symlink():
            return None
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_DESKTOP_FILE_BYTES:
            return None
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read_string(text)
        section = parser["Desktop Entry"]
    except (configparser.Error, KeyError):
        return None
    return DesktopLauncher(
        path=str(path),
        name=section.get("Name", "").strip()[:240],
        generic_name=section.get("GenericName", "").strip()[:240],
        comment=section.get("Comment", "").strip()[:500],
        categories=section.get("Categories", "").strip()[:300],
        keywords=section.get("Keywords", "").strip()[:500],
    )


def _apt_desktop_launchers(package_name: str) -> tuple[DesktopLauncher, ...]:
    try:
        result = run_command(["dpkg-query", "-L", package_name], timeout=20.0)
    except (CommandUnavailable, CommandTimedOut):
        return ()
    if result.returncode != 0:
        return ()
    launchers: list[DesktopLauncher] = []
    for line in result.stdout.splitlines():
        launcher_path = line.strip()
        if not launcher_path.endswith(".desktop"):
            continue
        launcher = _read_desktop_launcher(launcher_path)
        if launcher is not None:
            launchers.append(launcher)
            if len(launchers) >= MAX_LAUNCHERS:
                break
    return tuple(launchers)


def _apt_package_kind(fields: dict[str, str], launchers: tuple[DesktopLauncher, ...]) -> str:
    essential = fields.get("Essential", "").casefold() == "yes"
    priority = fields.get("Priority", "").casefold()
    section = fields.get("Section", "").casefold()
    if essential or priority in PROTECTED_PRIORITIES:
        return "Komponen sistem prioritas tinggi"
    if section.startswith("libs") or section == "libdevel":
        return "Pustaka / komponen runtime"
    if launchers:
        return "Aplikasi desktop (file .desktop ditemukan)"
    if section in {"admin", "base", "kernel", "sysutils"}:
        return "Utilitas atau komponen sistem"
    if section in {"web", "net", "graphics", "sound", "video", "games", "utils"}:
        return "Aplikasi / utilitas"
    return "Paket perangkat lunak (lihat deskripsi sumber)"


def _apt_details(application: InstalledApplication) -> ApplicationDetails:
    package = application.identifier
    if not APT_PACKAGE_RE.fullmatch(package):
        raise ValueError("ID paket APT tidak valid; detail tidak diambil.")
    try:
        result = run_command(["dpkg-query", "-s", package], timeout=15.0)
    except (CommandUnavailable, CommandTimedOut) as exc:
        raise RuntimeError(f"Metadata paket tidak dapat dibaca: {exc}") from exc
    if result.returncode != 0:
        raise RuntimeError("Paket tidak lagi tersedia pada database dpkg lokal; pindai ulang inventaris.")
    fields = parse_control_fields(result.stdout)
    if fields.get("Status", "").casefold() != "install ok installed":
        raise RuntimeError("Paket tidak lagi berstatus terpasang; pindai ulang inventaris.")

    installed_version = fields.get("Version", application.version)
    notes: list[str] = []
    try:
        policy = run_command(["apt-cache", "policy", package], timeout=20.0)
        origins = parse_apt_policy_origins(policy.stdout, installed_version) if policy.returncode == 0 else ()
    except (CommandUnavailable, CommandTimedOut):
        origins = ()
        notes.append("apt-cache tidak tersedia; repositori saat ini tidak dapat diverifikasi.")

    if origins:
        origin = " | ".join(origins)
        origin_note = (
            "Repositori yang saat ini menyediakan versi terpasang menurut indeks APT lokal. "
            "Ini bukan bukti historis repositori tempat paket pertama kali dipasang."
        )
    else:
        origin = "Tidak dapat ditentukan dari indeks APT lokal"
        origin_note = (
            "Database dpkg tidak menyimpan asal historis yang selalu dapat dibuktikan. "
            "Versi ini tidak cocok dengan repositori yang terlihat pada indeks lokal, atau metadata tidak tersedia."
        )

    launchers = _apt_desktop_launchers(package)
    if len(launchers) == MAX_LAUNCHERS:
        notes.append(f"Daftar file peluncur dibatasi sampai {MAX_LAUNCHERS} entri.")
    essential = fields.get("Essential", "")
    return ApplicationDetails(
        name=fields.get("Package", application.name) or application.name,
        identifier=package,
        version=installed_version,
        manager="APT / dpkg",
        package_kind=_apt_package_kind(fields, launchers),
        origin=origin,
        origin_note=origin_note,
        description=fields.get("Description", ""),
        maintainer=fields.get("Maintainer", ""),
        homepage=fields.get("Homepage", ""),
        section=fields.get("Section", ""),
        priority=fields.get("Priority", ""),
        essential=essential or "tidak dinyatakan",
        architecture=fields.get("Architecture", application.architecture),
        launchers=launchers,
        notes=tuple(notes),
    )


def _flatpak_value(application_id: str, option: str) -> str:
    try:
        result = run_command(["flatpak", "info", option, application_id], timeout=15.0)
    except (CommandUnavailable, CommandTimedOut):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()[:6000]


def _flatpak_details(application: InstalledApplication) -> ApplicationDetails:
    app_id = application.identifier
    if not FLATPAK_ID_RE.fullmatch(app_id):
        raise ValueError("ID aplikasi Flatpak tidak valid; detail tidak diambil.")
    ref = _flatpak_value(app_id, "--show-ref")
    origin = _flatpak_value(app_id, "--show-origin") or application.origin
    location = _flatpak_value(app_id, "--show-location")
    commit = _flatpak_value(app_id, "--show-commit")
    permissions = _flatpak_value(app_id, "--show-permissions")
    ref_parts = ref.split("/")
    architecture = ref_parts[2] if len(ref_parts) >= 4 else application.architecture
    branch = ref_parts[3] if len(ref_parts) >= 4 else application.branch
    notes: list[str] = []
    if not application.description:
        notes.append(
            "Deskripsi fungsi tidak tersedia dari kolom metadata Flatpak lokal; "
            "PaketScope tidak menyimpulkan fungsi hanya dari nama."
        )
    return ApplicationDetails(
        name=application.name,
        identifier=app_id,
        version=application.version,
        manager="Flatpak",
        package_kind="Aplikasi Flatpak",
        origin=origin or "Tidak dicatat pada metadata lokal",
        origin_note=(
            "Remote asal menurut metadata Flatpak lokal; ini lebih kuat daripada nama repositori "
            "APT, tetapi tidak membuktikan siapa yang membangun atau meninjau aplikasi."
        ),
        description=application.description,
        architecture=architecture,
        installation=application.installation,
        runtime=branch and application.branch or application.branch,
        commit=commit,
        location=location,
        permissions=permissions,
        notes=tuple(notes),
    )


def inspect_application(application: InstalledApplication) -> ApplicationDetails:
    """Inspect one inventoried item using source-specific, read-only metadata."""
    if application.source == "APT / dpkg":
        return _apt_details(application)
    if application.source == "Flatpak":
        return _flatpak_details(application)
    raise ValueError(
        f"Sumber '{application.source}' belum memiliki pemeriksa detail bawaan. "
        "Tambahkan adapter detail yang sesuai sebelum mengaktifkan fitur ini untuk sumber tersebut."
    )
