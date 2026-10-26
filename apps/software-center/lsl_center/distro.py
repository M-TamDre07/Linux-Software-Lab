"""Local Linux distribution and CPU architecture detection."""

from __future__ import annotations

import platform as platform_module
import shlex
import shutil
from collections.abc import Callable
from pathlib import Path

from .models import Artifact, SystemProfile

DEBIAN_IDS = {
    "debian", "ubuntu", "linuxmint", "pop", "pop_os", "elementary",
    "zorin", "kali", "raspbian", "deepin", "kdeneon",
}
ARCH_IDS = {"arch", "manjaro", "endeavouros", "artix", "cachyos", "garuda"}
FEDORA_IDS = {"fedora", "rhel", "centos", "rocky", "almalinux", "nobara"}
SUSE_IDS = {"opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles", "sled", "suse"}

ARCH_ALIASES = {
    "x86_64": {"x86_64", "amd64", "x64"},
    "aarch64": {"aarch64", "arm64"},
    "armv7l": {"armv7l", "armv7", "armhf"},
    "i686": {"i686", "i386", "x86"},
}


def canonical_architecture(machine: str | None = None) -> str:
    value = (machine or platform_module.machine() or "unknown").strip().casefold()
    for canonical, aliases in ARCH_ALIASES.items():
        if value in aliases:
            return canonical
    return value


def architecture_matches(artifact_architecture: str, system_architecture: str) -> bool:
    artifact_architecture = artifact_architecture.strip().casefold()
    system_architecture = canonical_architecture(system_architecture)
    if artifact_architecture in {"all", "any", "noarch"}:
        return True
    return system_architecture in ARCH_ALIASES.get(
        artifact_architecture, {artifact_architecture}
    ) or artifact_architecture in ARCH_ALIASES.get(system_architecture, {system_architecture})


def _read_os_release(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values

    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        try:
            parsed = shlex.split(raw_value, posix=True)
        except ValueError:
            continue
        values[key] = parsed[0] if parsed else ""
    return values


def _distribution_family(distro_id: str, id_like: str) -> str:
    ids_like = {part.casefold() for part in id_like.split()}
    if distro_id in DEBIAN_IDS or distro_id in {"ubuntu", "debian"}:
        return "debian-family"
    if distro_id in ARCH_IDS:
        return "arch-family"
    if distro_id in FEDORA_IDS:
        return "fedora-family"
    if distro_id in SUSE_IDS or distro_id.startswith("opensuse"):
        return "suse-family"
    if ids_like.intersection({"debian", "ubuntu"}):
        return "debian-family"
    if ids_like.intersection({"arch", "manjaro"}):
        return "arch-family"
    if ids_like.intersection({"fedora", "rhel", "centos"}):
        return "fedora-family"
    if ids_like.intersection({"suse", "opensuse", "sled", "sles"}):
        return "suse-family"
    return "unknown"


def detect_system_profile(
    os_release_path: Path = Path("/etc/os-release"),
    machine: str | None = None,
    which: Callable[[str], str | None] | None = None,
    os_name: str | None = None,
) -> SystemProfile:
    """Detect the host OS and architecture locally; distro files may be unavailable."""
    lookup = which or shutil.which
    detected_os = (os_name or platform_module.system() or "unknown").strip()
    values = _read_os_release(os_release_path)
    distro_id = values.get("ID", "unknown").casefold() or "unknown"
    id_like = values.get("ID_LIKE", "").casefold()
    family = _distribution_family(distro_id, id_like) if detected_os.casefold() == "linux" else "unknown"
    pretty_name = values.get("PRETTY_NAME", "").strip()
    if not pretty_name:
        if detected_os.casefold() == "linux" and distro_id not in {"", "unknown"}:
            pretty_name = distro_id
        elif detected_os.casefold() == "linux":
            pretty_name = "Linux (distribution unknown)"
        else:
            pretty_name = f"{detected_os or 'Operating system'} (distribution detection unavailable)"
    manager_name = {
        "debian-family": "apt-get",
        "arch-family": "pacman",
        "fedora-family": "dnf",
        "suse-family": "zypper",
    }.get(family)
    return SystemProfile(
        distro_id=distro_id,
        pretty_name=pretty_name,
        version_id=values.get("VERSION_ID", ""),
        family=family,
        architecture=canonical_architecture(machine),
        package_manager=manager_name,
        package_manager_path=lookup(manager_name) if manager_name else None,
        pkexec_path=lookup("pkexec"),
        flatpak_path=lookup("flatpak"),
        os_name=detected_os or "unknown",
    )


def artifact_compatibility(
    artifact: Artifact,
    profile: SystemProfile,
) -> tuple[bool, str]:
    """Return compatibility and a human-readable reason without installing anything."""
    if not profile.is_linux:
        return False, "Launcher ini hanya mendukung sistem Linux saat ini."
    if not architecture_matches(artifact.architecture, profile.architecture):
        return False, (
            f"Paket membutuhkan arsitektur {artifact.architecture}; "
            f"sistem ini terdeteksi {profile.architecture}."
        )
    if artifact.is_source_archive:
        return False, "Arsip source bisa diunduh, tetapi bukan paket instalasi native."
    if artifact.kind == "debian-package" or artifact.format == "deb":
        if profile.family != "debian-family":
            return False, "Paket .deb hanya ditawarkan untuk keluarga Debian/Ubuntu."
        if not profile.package_manager_path:
            return False, "Perintah apt-get tidak ditemukan pada sistem ini."
        if not profile.pkexec_path:
            return False, "pkexec/Polkit tidak tersedia untuk meminta otorisasi instalasi."
        return True, "Paket cocok dengan keluarga Debian/Ubuntu; status rilis tetap harus diperhatikan."
    if artifact.kind == "rpm-package" or artifact.format == "rpm":
        if profile.family not in {"fedora-family", "suse-family"}:
            return False, "Paket .rpm tidak cocok dengan keluarga distribusi ini."
        return False, "Adapter RPM belum diaktifkan dalam build launcher ini."
    if artifact.kind == "arch-package" or artifact.format == "pkg.tar.zst":
        if profile.family != "arch-family":
            return False, "Paket Arch hanya cocok untuk Arch Linux dan turunannya."
        return False, "Adapter Arch belum diaktifkan dalam build launcher ini."
    if artifact.format in {"flatpak", "flatpakref"}:
        if not profile.flatpak_path:
            return False, "Flatpak belum terpasang pada sistem ini."
        return False, "Instalasi Flatpak belum diaktifkan dalam build launcher ini."
    if artifact.format == "AppImage":
        return False, "Eksekusi AppImage belum diaktifkan dalam build launcher ini."
    return False, f"Format paket {artifact.format} belum didukung."


def executable_for(application_id: str, which: Callable[[str], str | None] | None = None) -> str | None:
    """Resolve a launch target from the reviewed local registry, not remote JSON."""
    from .integrations import executable_for as resolve_local_executable

    return resolve_local_executable(application_id, which=which)
