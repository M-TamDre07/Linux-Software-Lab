"""Download, integrity verification, and narrowly scoped Debian installation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .distro import artifact_compatibility
from .models import Artifact, InstallPreview, InstallResult, SystemProfile

OWNER = "M-TamDre07"
REPOSITORY = "Linux-Software-Lab"
RAW_PATH_PREFIX = f"/{OWNER}/{REPOSITORY}/main/apps/"
MAX_ARTIFACT_BYTES = 1024 * 1024 * 1024
MAX_RELEASE_METADATA_BYTES = 2 * 1024 * 1024
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
PACKAGE_KINDS = {"debian-package", "rpm-package", "arch-package", "native-package"}


class InstallError(RuntimeError):
    """Raised when an artifact cannot safely be downloaded, verified, or installed."""


def _validate_trusted_release_url(url: str, artifact: Artifact, expected_leaf: str) -> None:
    parsed = urlsplit(url)
    expected_path = (
        f"{RAW_PATH_PREFIX}{artifact.product_id}/releases/{artifact.version}/{expected_leaf}"
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != "raw.githubusercontent.com"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise InstallError(f"Refusing a non-canonical release URL for {artifact.file}.")


def _fetch_limited(
    url: str,
    artifact: Artifact,
    expected_leaf: str,
    maximum_bytes: int,
) -> bytes:
    _validate_trusted_release_url(url, artifact, expected_leaf)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LinuxSoftwareLabCenter/0.1",
            "Accept": "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = urlsplit(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != "raw.githubusercontent.com":
                raise InstallError("The download redirected to an untrusted host.")
            final_path = (
                f"{RAW_PATH_PREFIX}{artifact.product_id}/releases/{artifact.version}/{expected_leaf}"
            )
            if (
                final_url.port not in (None, 443)
                or final_url.path != final_path
                or final_url.query
                or final_url.fragment
            ):
                raise InstallError("The download redirected away from the selected release artifact.")
            length = response.headers.get("Content-Length")
            if length and int(length) > maximum_bytes:
                raise InstallError(f"Download exceeds the {maximum_bytes}-byte size limit.")
            content = response.read(maximum_bytes + 1)
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError(f"Unable to download {expected_leaf}: {exc}") from exc
    if len(content) > maximum_bytes:
        raise InstallError(f"Download exceeds the {maximum_bytes}-byte size limit.")
    return content


def _parse_sha256sums(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InstallError("The release SHA256SUMS file is not valid UTF-8.") from exc
    entries: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([a-f0-9]{64})\s+[*]?([A-Za-z0-9][A-Za-z0-9._+-]*)", line.strip())
        if not match:
            raise InstallError("The release SHA256SUMS contains a malformed entry.")
        digest, filename = match.groups()
        if filename in entries:
            raise InstallError(f"The release SHA256SUMS repeats {filename}.")
        entries[filename] = digest
    return entries


def validate_release_metadata(
    artifact: Artifact,
    manifest_bytes: bytes,
    checksums_bytes: bytes,
) -> dict[str, Any]:
    """Ensure web metadata agrees with the version manifest and checksums before any download."""
    if len(manifest_bytes) > MAX_RELEASE_METADATA_BYTES:
        raise InstallError("Release manifest is too large.")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"Invalid release manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise InstallError("Release manifest root must be an object.")
    if (
        manifest.get("schema_version") != 1
        or str(manifest.get("product", "")).casefold() != artifact.product_id
        or manifest.get("version") != artifact.version
        or manifest.get("channel") != artifact.channel
        or manifest.get("status") != artifact.release_status
    ):
        raise InstallError("Release manifest does not match the selected product/version/channel.")
    raw_artifacts = manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise InstallError("Release manifest is missing its artifact list.")
    matching = [item for item in raw_artifacts if isinstance(item, dict) and item.get("file") == artifact.file]
    if len(matching) != 1:
        raise InstallError("The selected file must appear exactly once in its release manifest.")
    item = matching[0]
    expected_fields = {
        "sha256": artifact.sha256,
        "kind": artifact.kind,
        "format": artifact.format,
    }
    for field, expected in expected_fields.items():
        if item.get(field) != expected:
            raise InstallError(f"Release metadata mismatch for {artifact.file}: {field}.")
    if item.get("architecture", "all") != artifact.architecture:
        raise InstallError(f"Release metadata architecture mismatch for {artifact.file}.")
    if not SHA256_PATTERN.fullmatch(str(artifact.sha256)):
        raise InstallError("The selected artifact has an invalid SHA-256 digest.")
    checksums = _parse_sha256sums(checksums_bytes)
    if checksums.get(artifact.file) != artifact.sha256:
        raise InstallError("The selected artifact digest does not match release SHA256SUMS.")
    return manifest


def validate_artifact_for_download(artifact: Artifact) -> None:
    if not SAFE_FILENAME_PATTERN.fullmatch(artifact.file) or Path(artifact.file).name != artifact.file:
        raise InstallError("The artifact filename is unsafe.")
    if not SHA256_PATTERN.fullmatch(artifact.sha256):
        raise InstallError("The artifact SHA-256 digest is invalid.")
    _validate_trusted_release_url(artifact.url, artifact, artifact.file)
    _validate_trusted_release_url(artifact.manifest_url, artifact, "release.json")
    _validate_trusted_release_url(artifact.checksums_url, artifact, "SHA256SUMS")


def _load_and_validate_remote_release(artifact: Artifact) -> dict[str, Any]:
    manifest = _fetch_limited(
        artifact.manifest_url, artifact, "release.json", MAX_RELEASE_METADATA_BYTES
    )
    checksums = _fetch_limited(
        artifact.checksums_url, artifact, "SHA256SUMS", MAX_RELEASE_METADATA_BYTES
    )
    return validate_release_metadata(artifact, manifest, checksums)


def default_download_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return base / "linux-software-lab-center" / "downloads"


def download_artifact(
    artifact: Artifact,
    destination_root: Path | None = None,
) -> Path:
    """Download one allowlisted versioned file only after manifest/hash agreement."""
    validate_artifact_for_download(artifact)
    _load_and_validate_remote_release(artifact)

    target_root = destination_root or default_download_dir()
    target_dir = target_root / artifact.product_id / artifact.version
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / artifact.file

    request = urllib.request.Request(
        artifact.url,
        headers={"User-Agent": "LinuxSoftwareLabCenter/0.1", "Accept": "application/octet-stream"},
    )
    digest = hashlib.sha256()
    total = 0
    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = urlsplit(response.geturl())
            expected_url = urlsplit(artifact.url)
            if (
                final_url.scheme != "https"
                or final_url.hostname != expected_url.hostname
                or final_url.path != expected_url.path
                or final_url.query
                or final_url.fragment
            ):
                raise InstallError("The artifact download redirected to a different resource.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARTIFACT_BYTES:
                raise InstallError("The artifact exceeds the download size limit.")
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{artifact.file}.",
                suffix=".part",
                dir=target_dir,
                delete=False,
            ) as output:
                temp_path = Path(output.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ARTIFACT_BYTES:
                        raise InstallError("The artifact exceeds the download size limit.")
                    digest.update(chunk)
                    output.write(chunk)
        if digest.hexdigest() != artifact.sha256:
            raise InstallError(
                f"SHA-256 mismatch for {artifact.file}; the downloaded file was rejected."
            )
        if total == 0:
            raise InstallError("The downloaded artifact is empty.")
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, target)
        temp_path = None
        return target
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError(f"Download failed for {artifact.file}: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def verify_local_artifact(artifact: Artifact, path: Path) -> str:
    """Verify a saved file against the live version manifest and SHA256SUMS."""
    validate_artifact_for_download(artifact)
    _load_and_validate_remote_release(artifact)
    try:
        file_path = path.resolve(strict=True)
        if not file_path.is_file():
            raise InstallError("The selected path is not a regular file.")
        if file_path.stat().st_size > MAX_ARTIFACT_BYTES:
            raise InstallError("The selected file exceeds the maximum artifact size.")
        digest = hashlib.sha256()
        with file_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise InstallError(f"Unable to read the selected file: {exc}") from exc
    actual = digest.hexdigest()
    if actual != artifact.sha256:
        raise InstallError("The selected file does not match the published SHA-256 digest.")
    return actual


def can_install_with_current_adapter(artifact: Artifact, profile: SystemProfile) -> tuple[bool, str]:
    return artifact_compatibility(artifact, profile)


def _require_debian_installation(artifact: Artifact, profile: SystemProfile) -> tuple[str, str]:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise InstallError(
            "Jangan jalankan launcher sebagai root. Jalankan sebagai pengguna biasa agar Polkit dapat meminta otorisasi."
        )
    compatible, reason = artifact_compatibility(artifact, profile)
    if not compatible:
        raise InstallError(reason)
    if artifact.format != "deb" or profile.family != "debian-family":
        raise InstallError("Only verified Debian-package installation is enabled in this MVP.")
    if not profile.package_manager_path or not profile.pkexec_path:
        raise InstallError("apt-get and pkexec/Polkit are required for installation.")
    return profile.package_manager_path, profile.pkexec_path


def build_simulation_command(
    artifact: Artifact,
    package_path: Path,
    profile: SystemProfile,
) -> tuple[str, ...]:
    apt_get, _ = _require_debian_installation(artifact, profile)
    resolved = package_path.resolve(strict=True)
    if not resolved.is_file() or resolved.suffix != ".deb":
        raise InstallError("Install preview requires an existing local .deb file.")
    return (
        apt_get,
        "-s",
        "-o",
        "Dpkg::Use-Pty=0",
        "install",
        "--no-remove",
        "--no-install-recommends",
        str(resolved),
    )


def _removal_detected(output: str) -> bool:
    return bool(
        re.search(r"(?m)^\s*Remv\s+", output)
        or re.search(r"(?i)the following packages will be removed", output)
    )


def preview_installation(
    artifact: Artifact,
    package_path: Path,
    profile: SystemProfile,
    timeout_seconds: int = 120,
) -> InstallPreview:
    command = build_simulation_command(artifact, package_path, profile)
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"Could not simulate the APT transaction: {exc}") from exc
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise InstallError(
            "APT simulation failed; no installation was attempted.\n"
            + output[-6000:]
        )
    if _removal_detected(output):
        raise InstallError(
            "APT simulation indicates that packages may be removed. "
            "The launcher refuses this transaction.\n" + output[-6000:]
        )
    return InstallPreview(
        package_path=package_path.resolve(),
        command=command,
        output=output.strip() or "APT simulation completed without additional output.",
        package_manager="apt-get",
        removal_detected=False,
    )


def build_install_command(
    artifact: Artifact,
    package_path: Path,
    profile: SystemProfile,
) -> tuple[str, ...]:
    apt_get, pkexec = _require_debian_installation(artifact, profile)
    resolved = package_path.resolve(strict=True)
    if not resolved.is_file() or resolved.suffix != ".deb":
        raise InstallError("Installation requires an existing local .deb file.")
    return (
        pkexec,
        apt_get,
        "-o",
        "Dpkg::Use-Pty=0",
        "install",
        "--no-remove",
        "--no-install-recommends",
        "--yes",
        str(resolved),
    )


def _transaction_plan_signature(output: str) -> tuple[str, ...]:
    """Keep only package actions so non-deterministic apt progress messages do not matter."""
    return tuple(
        line.strip()
        for line in output.splitlines()
        if re.match(r"^(?:Inst|Remv|Conf)\\s+", line.strip())
    )


def _same_preview_plan(expected: InstallPreview, current: InstallPreview) -> bool:
    return (
        expected.package_path.resolve() == current.package_path.resolve()
        and expected.command == current.command
        and expected.package_manager == current.package_manager
        and expected.removal_detected == current.removal_detected
        and _transaction_plan_signature(expected.output)
        == _transaction_plan_signature(current.output)
    )


def install_verified_artifact(
    artifact: Artifact,
    package_path: Path,
    profile: SystemProfile,
    timeout_seconds: int = 1800,
    expected_preview: InstallPreview | None = None,
) -> InstallResult:
    """Execute only if the package still matches the displayed APT preview."""
    verify_local_artifact(artifact, package_path)
    current_preview = preview_installation(artifact, package_path, profile)
    if expected_preview is not None and not _same_preview_plan(expected_preview, current_preview):
        raise InstallError(
            "APT's package plan changed after confirmation. No installation was started; "
            "review a fresh transaction preview."
        )
    command = build_install_command(artifact, package_path, profile)
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"Installation process failed to start or timed out: {exc}") from exc
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    return InstallResult(package_path=package_path.resolve(), return_code=result.returncode, output=output)
