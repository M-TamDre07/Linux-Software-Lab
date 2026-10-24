"""Pure data types and parsers used by the inventory collectors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True, slots=True)
class InstalledApplication:
    """Normalized inventory record; optional metadata stays source-attributed."""

    name: str
    version: str
    source: str
    identifier: str
    branch: str = ""
    origin: str = ""
    description: str = ""
    section: str = ""
    priority: str = ""
    essential: bool = False
    architecture: str = ""
    installation: str = ""

    def to_record(self) -> dict[str, str | bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    applications: tuple[InstalledApplication, ...]
    collected_at: str
    diagnostics: tuple[str, ...]

    @classmethod
    def create(
        cls,
        applications: Iterable[InstalledApplication],
        diagnostics: Iterable[str] = (),
    ) -> "InventorySnapshot":
        ordered = tuple(sorted(
            applications,
            key=lambda item: (item.name.casefold(), item.source.casefold(), item.identifier.casefold()),
        ))
        return cls(
            applications=ordered,
            collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            diagnostics=tuple(diagnostics),
        )


def parse_dpkg_output(output: str) -> list[InstalledApplication]:
    """Parse installed dpkg records and retain safe package-classification metadata.

    The original three-column format remains accepted for old fixtures and
    external adapters. Fields are tab-separated to preserve spaces in values.
    """
    result: list[InstalledApplication] = []
    for line in output.splitlines():
        columns = [part.strip() for part in line.split("\t")]
        if len(columns) < 3:
            continue
        identifier, version, status = columns[:3]
        if not identifier or status.casefold() != "installed":
            continue
        section = columns[3] if len(columns) > 3 else ""
        priority = columns[4] if len(columns) > 4 else ""
        essential = len(columns) > 5 and columns[5].casefold() == "yes"
        architecture = columns[6] if len(columns) > 6 else ""
        result.append(InstalledApplication(
            name=identifier,
            version=version or "—",
            source="APT / dpkg",
            identifier=identifier,
            section=section,
            priority=priority,
            essential=essential,
            architecture=architecture,
        ))
    return result


def parse_flatpak_output(output: str) -> list[InstalledApplication]:
    """Parse Flatpak's tab-separated columns; tolerate older, shorter output."""
    result: list[InstalledApplication] = []
    for line in output.splitlines():
        columns = [part.strip() for part in line.split("\t")]
        if len(columns) < 5:
            continue
        app_id, name, version, branch, origin = columns[:5]
        description = columns[5] if len(columns) > 5 else ""
        installation = columns[6] if len(columns) > 6 else ""
        architecture = columns[7] if len(columns) > 7 else ""
        if not app_id:
            continue
        result.append(InstalledApplication(
            name=name or app_id,
            version=version or "—",
            source="Flatpak",
            identifier=app_id,
            branch=branch,
            origin=origin,
            description=description,
            installation=installation,
            architecture=architecture,
        ))
    return result
