"""Declarative package-manager capability registry for Linux Software Lab Center.

A detected distribution is not automatically installable. Only adapters marked
enabled may be used for native installation; each enabled path still requires
its own package lifecycle tests before release.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackageManagerAdapter:
    family: str
    command: str
    artifact_formats: tuple[str, ...]
    enabled: bool
    strategy: str
    status: str
    reason: str


_ADAPTERS: dict[str, PackageManagerAdapter] = {
    "debian-family": PackageManagerAdapter(
        family="debian-family",
        command="apt-get",
        artifact_formats=("deb",),
        enabled=True,
        strategy="apt-simulate-confirm-polkit",
        status="implemented",
        reason=(
            "APT simulation, removal guard, explicit confirmation, and Polkit "
            "authorization are implemented."
        ),
    ),
    "arch-family": PackageManagerAdapter(
        family="arch-family",
        command="pacman",
        artifact_formats=("pkg.tar.zst",),
        enabled=False,
        strategy="disabled",
        status="detected-only",
        reason=(
            "Arch installation remains disabled until package validation and "
            "isolated install/upgrade/uninstall tests pass."
        ),
    ),
    "fedora-family": PackageManagerAdapter(
        family="fedora-family",
        command="dnf",
        artifact_formats=("rpm",),
        enabled=False,
        strategy="disabled",
        status="detected-only",
        reason=(
            "Fedora/RPM installation remains disabled until transaction handling "
            "and isolated package lifecycle tests pass."
        ),
    ),
    "suse-family": PackageManagerAdapter(
        family="suse-family",
        command="zypper",
        artifact_formats=("rpm",),
        enabled=False,
        strategy="disabled",
        status="detected-only",
        reason="SUSE installation is not validated by this launcher build.",
    ),
}


def adapter_for_family(family: str) -> PackageManagerAdapter | None:
    """Return the descriptor for a known family, including intentionally disabled ones."""
    return _ADAPTERS.get(family.strip().casefold())


def registered_adapters() -> tuple[PackageManagerAdapter, ...]:
    """Return adapter descriptors in deterministic order for diagnostics and tests."""
    return tuple(_ADAPTERS[key] for key in sorted(_ADAPTERS))


def enabled_adapter_for_family(family: str) -> PackageManagerAdapter | None:
    """Return an adapter only if native installation is explicitly enabled."""
    adapter = adapter_for_family(family)
    return adapter if adapter is not None and adapter.enabled else None
