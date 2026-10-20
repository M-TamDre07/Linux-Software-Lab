"""Pure data types and parsers used by the inventory collectors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True, slots=True)
class InstalledApplication:
    name: str
    version: str
    source: str
    identifier: str
    branch: str = ""
    origin: str = ""

    def to_record(self) -> dict[str, str]:
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
    """Parse dpkg-query output; only installed package records are kept."""
    result: list[InstalledApplication] = []
    for line in output.splitlines():
        columns = line.split("\t")
        if len(columns) < 3:
            continue
        identifier, version, status = (part.strip() for part in columns[:3])
        if not identifier or status.casefold() != "installed":
            continue
        result.append(InstalledApplication(
            name=identifier,
            version=version or "—",
            source="APT / dpkg",
            identifier=identifier,
        ))
    return result


def parse_flatpak_output(output: str) -> list[InstalledApplication]:
    """Parse Flatpak's tab-separated application columns."""
    result: list[InstalledApplication] = []
    for line in output.splitlines():
        columns = [part.strip() for part in line.split("\t")]
        if len(columns) < 5:
            continue
        app_id, name, version, branch, origin = columns[:5]
        if not app_id:
            continue
        result.append(InstalledApplication(
            name=name or app_id,
            version=version or "—",
            source="Flatpak",
            identifier=app_id,
            branch=branch,
            origin=origin,
        ))
    return result
