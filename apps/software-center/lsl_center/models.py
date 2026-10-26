"""Typed domain models for the launcher and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SystemProfile:
    distro_id: str
    pretty_name: str
    version_id: str
    family: str
    architecture: str
    package_manager: str | None
    package_manager_path: str | None
    pkexec_path: str | None
    flatpak_path: str | None

    @property
    def is_linux(self) -> bool:
        # An unknown family can still be a Linux distro; installation then fails closed.
        return self.distro_id not in {"", "unknown"}


@dataclass(frozen=True, slots=True)
class Artifact:
    product_id: str
    product_name: str
    version: str
    channel: str
    release_status: str
    file: str
    kind: str
    format: str
    architecture: str
    sha256: str
    url: str
    manifest_url: str
    checksums_url: str

    @property
    def is_source_archive(self) -> bool:
        return self.kind == "source-archive"

    @property
    def is_native_package(self) -> bool:
        return self.kind in {"debian-package", "rpm-package", "arch-package", "native-package"}


@dataclass(frozen=True, slots=True)
class PlannedTarget:
    distribution_id: str
    version: str
    note: str


@dataclass(frozen=True, slots=True)
class Application:
    id: str
    name: str
    version: str
    summary: str
    description: str
    category: str
    status: str
    app_type: str
    platforms: tuple[str, ...]
    tags: tuple[str, ...]
    keywords: tuple[str, ...]
    features: tuple[str, ...]
    source_url: str
    release_url: str
    icon_path: Path | None
    artifacts: tuple[Artifact, ...]
    planned_targets: tuple[PlannedTarget, ...] = ()

    @classmethod
    def from_catalog_record(
        cls,
        record: dict[str, Any],
        artifacts: tuple[Artifact, ...],
        icon_path: Path | None,
        planned_targets: tuple[PlannedTarget, ...] = (),
    ) -> Application:
        return cls(
            id=record["id"],
            name=record["name"],
            version=record["version"],
            summary=record["summary"],
            description=record["description"],
            category=record["category"],
            status=record["status"],
            app_type=record["type"],
            platforms=tuple(record.get("platforms", [])),
            tags=tuple(record.get("tags", [])),
            keywords=tuple(record.get("keywords", [])),
            features=tuple(record.get("features", [])),
            source_url=record.get("sourceUrl", ""),
            release_url=record.get("releaseUrl", ""),
            icon_path=icon_path,
            artifacts=artifacts,
            planned_targets=planned_targets,
        )


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    applications: tuple[Application, ...]
    updated_at: str
    data_source: str

    def find(self, application_id: str) -> Application | None:
        normalized = application_id.strip().casefold()
        return next(
            (app for app in self.applications if app.id.casefold() == normalized),
            None,
        )


@dataclass(frozen=True, slots=True)
class InstallPreview:
    package_path: Path
    command: tuple[str, ...]
    output: str
    package_manager: str
    removal_detected: bool


@dataclass(frozen=True, slots=True)
class InstallResult:
    package_path: Path
    return_code: int
    output: str

    @property
    def success(self) -> bool:
        return self.return_code == 0
