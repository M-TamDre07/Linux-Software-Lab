"""Extension contract for local package-inventory providers.

Providers are explicitly registered by the application or developer. PaketScope
does not import arbitrary third-party plugins automatically, because such code
would run with the same account privileges as the desktop application.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import InstalledApplication


@dataclass(frozen=True, slots=True)
class ProviderResult:
    applications: tuple[InstalledApplication, ...]
    diagnostics: tuple[str, ...] = ()


class InventoryProvider(Protocol):
    """Read-only inventory adapter contract for a package manager or app source."""

    provider_id: str
    display_name: str

    def collect(self) -> ProviderResult:
        """Return normalized inventory and diagnostics without modifying the host."""
        ...
