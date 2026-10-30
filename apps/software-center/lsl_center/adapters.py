"""Declarative package-manager adapter registry for the desktop launcher.

Only adapters with enabled=True may be used for installation. Registering a family
or recognizing its package manager is not proof that native installation is supported.
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


_ADAPTERS = {
    "debian-family": PackageManagerAdapter(
        family="debian-family",
        command="apt-get",
        artifact_formats=("deb",),
        enabled=True,
        strategy="apt-simulate-confirm-polkit",
        status="implemented",
        reason="APT simulation, removal guard, explicit confirmation, and Polkit authorization are implemented.",
    ),
    "arch-family": PackageManagerAdapter(
        family="arch-family",
        command="pacman",
        artifact_formats=("pkg.tar.zst",),
        enabled=False,
        strategy="disabled",
        status="detected-only",
        reason="Arch package installation is disabled until isolated build/install/upgrade/uninstall tests pass.",
    ),
    "fedora-family": PackageManagerAdapter(
        family="fedora-family",
        command="dnf",
        artifact_formats=("rpm",),
        enabled=False,
        strategy="disabled",
        status="detected-only",
        reason="RPM installation is disabled until Fedora/RPM transaction and lifecycle tests pass.",
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
    """Return a known adapter descriptor; a descriptor may intentionally be disabled."""
    return _ADAPTERS.get(family.strip().casefold())


def registered_adapters() -> tuple[PackageManagerAdapter, ...]:
    """Return descriptors in deterministic family order for diagnostics and tests."""
    return tuple(_ADAPTERS[key] for key in sorted(_ADAPTERS))


def enabled_adapter_for_family(family: str) -> PackageManagerAdapter | None:
    """Return an adapter only when its installation path is explicitly enabled."""
    adapter = adapter_for_family(family)
    return adapter if adapter is not None and adapter.enabled else None
