"""Read-only package inventory adapters and explicit provider registry."""
from __future__ import annotations

from collections.abc import Iterable

from .commands import CommandTimedOut, CommandUnavailable, run_command
from .domain import InventorySnapshot, InstalledApplication, parse_dpkg_output, parse_flatpak_output
from .providers import InventoryProvider, ProviderResult


class AptDpkgProvider:
    """Inventory packages already registered in the local dpkg database."""

    provider_id = "apt-dpkg"
    display_name = "APT / dpkg"

    def collect(self) -> ProviderResult:
        dpkg_format = (
            "${binary:Package}\t${Version}\t${db:Status-Status}\t"
            "${Section}\t${Priority}\t${Essential}\t${Architecture}\n"
        )
        try:
            result = run_command(["dpkg-query", "-W", "-f=" + dpkg_format], timeout=25.0)
        except (CommandUnavailable, CommandTimedOut) as exc:
            return ProviderResult((), (f"APT/dpkg: {exc}",))
        if result.returncode != 0:
            return ProviderResult((), (
                "Inventaris APT tidak tersedia: dpkg-query mengembalikan kode "
                + str(result.returncode) + ".",
            ))
        return ProviderResult(tuple(parse_dpkg_output(result.stdout)))


class FlatpakProvider:
    """Inventory Flatpak applications without changing installations or remotes."""

    provider_id = "flatpak"
    display_name = "Flatpak"

    def collect(self) -> ProviderResult:
        extended = [
            "flatpak", "list", "--app",
            "--columns=application,name,description,version,branch,origin",
        ]
        try:
            result = run_command(extended, timeout=25.0)
        except (CommandUnavailable, CommandTimedOut) as exc:
            return ProviderResult((), (f"Flatpak: {exc}",))
        if result.returncode == 0:
            return ProviderResult(tuple(parse_flatpak_output(result.stdout)))

        # Older Flatpak releases may not expose every optional column. Fall
        # back to the long-standing inventory fields instead of hiding apps.
        try:
            fallback = run_command([
                "flatpak", "list", "--app",
                "--columns=application,name,version,branch,origin",
            ], timeout=25.0)
        except (CommandUnavailable, CommandTimedOut) as exc:
            return ProviderResult((), (f"Flatpak: {exc}",))
        if fallback.returncode == 0:
            return ProviderResult(tuple(parse_flatpak_output(fallback.stdout)), (
                "Flatpak description metadata is unavailable on this CLI version.",
            ))
        detail = fallback.stderr.strip().splitlines()
        return ProviderResult((), (
            "Inventaris Flatpak tidak tersedia: "
            + (detail[-1][:180] if detail else "perintah gagal."),
        ))


DEFAULT_PROVIDERS: tuple[InventoryProvider, ...] = (
    AptDpkgProvider(),
    FlatpakProvider(),
)


def collect_inventory(
    providers: Iterable[InventoryProvider] | None = None,
) -> InventorySnapshot:
    """Collect installed software from explicitly registered read-only adapters.

    Applications can pass their own provider objects for a custom source. No
    third-party modules are discovered or executed automatically.
    """
    applications: list[InstalledApplication] = []
    diagnostics: list[str] = []
    active_providers = tuple(DEFAULT_PROVIDERS if providers is None else providers)
    for provider in active_providers:
        try:
            result = provider.collect()
        except Exception as exc:  # A custom provider should not hide other sources.
            diagnostics.append(
                f"{getattr(provider, 'display_name', 'Custom provider')}: "
                f"adapter failed ({type(exc).__name__})."
            )
            continue
        applications.extend(result.applications)
        diagnostics.extend(result.diagnostics)
    if not applications and not diagnostics:
        diagnostics.append("Tidak ada aplikasi yang ditemukan oleh sumber paket yang didukung.")
    return InventorySnapshot.create(applications, diagnostics)
