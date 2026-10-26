"""Centralized artifact-selection rules used by both GUI and CLI."""

from __future__ import annotations

import re

from .distro import artifact_compatibility
from .models import Application, Artifact, SystemProfile


def _version_key(value: str) -> tuple[int, int, int, int, str]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", value)
    if not match:
        return (0, 0, 0, 0, value)
    major, minor, patch, suffix = match.groups()
    # A release without a suffix sorts after a prerelease of the same numeric version.
    return (int(major), int(minor), int(patch), 1 if not suffix else 0, suffix)


def select_artifact(
    application: Application,
    profile: SystemProfile,
    *,
    version: str | None = None,
    requested_format: str | None = None,
    install_only: bool = False,
) -> Artifact | None:
    artifacts = [
        artifact
        for artifact in application.artifacts
        if artifact.release_status in {"testing", "released"}
        and (version is None or artifact.version == version)
    ]
    if requested_format:
        wanted = requested_format.strip().casefold().removeprefix(".")
        artifacts = [artifact for artifact in artifacts if artifact.format.casefold() == wanted]

    if install_only:
        compatible = [
            artifact
            for artifact in artifacts
            if artifact.is_native_package and artifact_compatibility(artifact, profile)[0]
        ]
        return max(compatible, key=lambda item: _version_key(item.version), default=None)

    if requested_format:
        matches = [
            artifact
            for artifact in artifacts
            if artifact.is_source_archive
            or (artifact.is_native_package and artifact_compatibility(artifact, profile)[0])
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: _version_key(item.version))

    compatible_packages = [
        artifact
        for artifact in artifacts
        if artifact.is_native_package and artifact_compatibility(artifact, profile)[0]
    ]
    if compatible_packages:
        return max(compatible_packages, key=lambda item: _version_key(item.version))
    source_archives = [item for item in artifacts if item.is_source_archive]
    if source_archives:
        zip_archive = [item for item in source_archives if item.format == "zip"]
        return max(zip_archive or source_archives, key=lambda item: _version_key(item.version))
    return None


def source_artifacts(application: Application, version: str | None = None) -> tuple[Artifact, ...]:
    candidates = [
        item for item in application.artifacts
        if item.is_source_archive and (version is None or item.version == version)
    ]
    return tuple(sorted(candidates, key=lambda item: (item.version, item.format)))
