#!/usr/bin/env python3
"""Validate immutable per-version Sorot release manifests and SHA-256 files."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

RELEASES_DIR = Path(__file__).resolve().parent / "releases"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA256_LINE_PATTERN = re.compile(r"^([0-9a-f]{64})  ([^/\\\\]+)$")
ALLOWED_STATUS = {"testing", "released", "archived"}
ALLOWED_CHANNELS = {"alpha", "beta", "rc", "stable", "development"}


class ReleaseValidationError(ValueError):
    """A release directory is incomplete or internally inconsistent."""


def _read_checksum_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ReleaseValidationError(f"Missing checksum file: {path.name}")
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        match = SHA256_LINE_PATTERN.fullmatch(line)
        if match is None:
            raise ReleaseValidationError(f"{path.name}:{line_number}: invalid SHA-256 line")
        digest, filename = match.groups()
        if filename in entries:
            raise ReleaseValidationError(f"{path.name}:{line_number}: duplicate filename {filename}")
        entries[filename] = digest
    if not entries:
        raise ReleaseValidationError(f"{path.name} contains no checksums")
    return entries


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_release(directory: Path) -> dict[str, Any]:
    version = directory.name
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ReleaseValidationError(f"Invalid release directory name: {version}")

    manifest_path = directory / "release.json"
    if not manifest_path.is_file():
        raise ReleaseValidationError(f"{version}: missing release.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"{version}: cannot read release.json: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ReleaseValidationError(f"{version}: manifest root must be an object")
    if manifest.get("schema_version") != 1:
        raise ReleaseValidationError(f"{version}: unsupported schema_version")
    if manifest.get("product") != "Sorot":
        raise ReleaseValidationError(f"{version}: product must be Sorot")
    if manifest.get("version") != version:
        raise ReleaseValidationError(f"{version}: manifest version does not match folder")
    if manifest.get("status") not in ALLOWED_STATUS:
        raise ReleaseValidationError(f"{version}: status must be one of {sorted(ALLOWED_STATUS)}")
    if manifest.get("channel") not in ALLOWED_CHANNELS:
        raise ReleaseValidationError(f"{version}: channel must be one of {sorted(ALLOWED_CHANNELS)}")

    checksum_name = manifest.get("checksum_file")
    if checksum_name != "SHA256SUMS":
        raise ReleaseValidationError(f"{version}: checksum_file must be SHA256SUMS")
    checksums = _read_checksum_file(directory / checksum_name)

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReleaseValidationError(f"{version}: artifacts must be a non-empty list")

    declared: dict[str, str] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ReleaseValidationError(f"{version}: each artifact entry must be an object")
        filename = artifact.get("file")
        expected_digest = artifact.get("sha256")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            raise ReleaseValidationError(f"{version}: artifact filename must be a simple filename")
        if filename in declared:
            raise ReleaseValidationError(f"{version}: duplicate artifact {filename}")
        if not isinstance(expected_digest, str) or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
            raise ReleaseValidationError(f"{version}: {filename} has invalid sha256 metadata")
        if not isinstance(artifact.get("kind"), str) or not isinstance(artifact.get("format"), str):
            raise ReleaseValidationError(f"{version}: {filename} must declare kind and format")

        artifact_path = directory / filename
        if not artifact_path.is_file():
            raise ReleaseValidationError(f"{version}: missing artifact {filename}")
        actual_digest = _sha256(artifact_path)
        if actual_digest != expected_digest:
            raise ReleaseValidationError(f"{version}: release.json checksum mismatch for {filename}")
        if checksums.get(filename) != actual_digest:
            raise ReleaseValidationError(f"{version}: SHA256SUMS mismatch for {filename}")
        declared[filename] = actual_digest

    if set(checksums) != set(declared):
        missing = sorted(set(declared) - set(checksums))
        unexpected = sorted(set(checksums) - set(declared))
        raise ReleaseValidationError(
            f"{version}: manifest/checksum file entries differ; missing={missing}, unexpected={unexpected}"
        )

    return {"version": version, "count": len(declared), "channel": manifest["channel"], "status": manifest["status"]}


def main() -> int:
    if not RELEASES_DIR.is_dir():
        print(f"Release directory not found: {RELEASES_DIR}", file=sys.stderr)
        return 2
    versions = sorted(
        (path for path in RELEASES_DIR.iterdir() if path.is_dir() and VERSION_PATTERN.fullmatch(path.name)),
        key=lambda path: path.name,
    )
    if not versions:
        print("No versioned Sorot release directories found.", file=sys.stderr)
        return 1
    try:
        results = [validate_release(directory) for directory in versions]
    except (OSError, ReleaseValidationError) as exc:
        print(f"Sorot release validation failed: {exc}", file=sys.stderr)
        return 1
    for result in results:
        print(
            f"Validated Sorot {result['version']}: {result['count']} artifact(s), "
            f"channel={result['channel']}, status={result['status']}"
        )
    print(f"Validated {len(results)} Sorot version director(y/ies).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
