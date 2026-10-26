"""Shared local/remote catalogue reader with strict release metadata validation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .models import Application, Artifact, CatalogSnapshot

OWNER = "M-TamDre07"
REPOSITORY = "Linux-Software-Lab"
RAW_ROOT = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/main"
CATALOG_URL = f"{RAW_ROOT}/public/data/software.json"
DOWNLOADS_URL = f"{RAW_ROOT}/public/data/sorot-downloads.json"
MAX_METADATA_BYTES = 5 * 1024 * 1024
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_STATUSES = {"released", "testing", "planned", "archived"}
ALLOWED_FORMATS = {
    "deb", "rpm", "pkg.tar.zst", "flatpak", "flatpakref",
    "AppImage", "tar.gz", "zip",
}
ALLOWED_KINDS = {
    "debian-package", "rpm-package", "arch-package", "native-package",
    "flatpak-bundle", "flatpak-ref", "appimage", "source-archive",
}


class CatalogError(ValueError):
    """Raised when catalog metadata is invalid or internally inconsistent."""


def bundled_data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return base / "linux-software-lab-center"


def _read_json(path: Path, maximum_bytes: int = MAX_METADATA_BYTES) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size > maximum_bytes:
            raise CatalogError(f"Metadata file is larger than {maximum_bytes} bytes: {path.name}")
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CatalogError(f"Cannot read metadata file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"Metadata root must be an object: {path.name}")
    return data


def _safe_https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and not parsed.fragment
    )


def _validate_artifact_url(
    url: Any,
    product_id: str,
    version: str,
    filename: str,
) -> str:
    if not _safe_https_url(url):
        raise CatalogError(f"Artifact URL is not a valid HTTPS URL: {filename}")
    parsed = urlsplit(url)
    expected_path = (
        f"/{OWNER}/{REPOSITORY}/main/apps/{product_id}/releases/{version}/{filename}"
    )
    if (
        parsed.hostname != "raw.githubusercontent.com"
        or parsed.port not in (None, 443)
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise CatalogError(
            f"Artifact URL must point to the trusted, versioned GitHub archive: {filename}"
        )
    return url


def validate_catalog_payload(data: dict[str, Any]) -> None:
    if data.get("schemaVersion") != 2:
        raise CatalogError("Catalog schemaVersion must be 2.")
    catalog_metadata = data.get("catalog")
    if not isinstance(catalog_metadata, dict):
        raise CatalogError("Catalog metadata block is missing.")
    updated_at = catalog_metadata.get("updatedAt")
    if not isinstance(updated_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated_at):
        raise CatalogError("Catalog updatedAt must use YYYY-MM-DD.")
    apps = data.get("software")
    if not isinstance(apps, list) or not apps:
        raise CatalogError("Catalog must contain a non-empty software list.")
    seen_ids: set[str] = set()
    for app in apps:
        if not isinstance(app, dict):
            raise CatalogError("Every catalog item must be an object.")
        app_id = app.get("id")
        if not isinstance(app_id, str) or not ID_PATTERN.fullmatch(app_id):
            raise CatalogError("Every app needs a valid lowercase id.")
        if app_id in seen_ids:
            raise CatalogError(f"Duplicate application id: {app_id}")
        seen_ids.add(app_id)
        for field in ("name", "version", "summary", "description", "category", "status", "type"):
            if not isinstance(app.get(field), str) or not app[field].strip():
                raise CatalogError(f"{app_id}: required field {field!r} is empty.")
        if app["status"] not in ALLOWED_STATUSES:
            raise CatalogError(f"{app_id}: unsupported status {app['status']!r}.")
        for field in ("platforms", "tags", "keywords", "features"):
            value = app.get(field, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise CatalogError(f"{app_id}: {field} must be a list of strings.")
        for field in ("sourceUrl", "releaseUrl"):
            value = app.get(field, "")
            if value and not _safe_https_url(value):
                raise CatalogError(f"{app_id}: {field} must be empty or a valid HTTPS URL.")


def validate_download_payload(data: dict[str, Any]) -> None:
    if data.get("schemaVersion") != 1 or data.get("product") != "Sorot":
        raise CatalogError("Sorot download metadata has an unsupported schema or product.")
    distributions = data.get("distributions")
    versions = data.get("versions")
    if not isinstance(distributions, list) or not isinstance(versions, list):
        raise CatalogError("Distribution and version lists are required.")
    seen_versions: set[str] = set()
    for release in versions:
        if not isinstance(release, dict):
            raise CatalogError("Every release must be an object.")
        version = release.get("version")
        if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
            raise CatalogError("Release version has an invalid format.")
        if version in seen_versions:
            raise CatalogError(f"Duplicate release version: {version}")
        seen_versions.add(version)
        if release.get("status") not in ALLOWED_STATUSES:
            raise CatalogError(f"{version}: unsupported release status.")
        if release.get("channel") not in {"stable", "beta", "alpha", "development"}:
            raise CatalogError(f"{version}: unsupported release channel.")
        artifacts = release.get("artifacts")
        if not isinstance(artifacts, list):
            raise CatalogError(f"{version}: artifacts must be a list.")
        seen_files: set[str] = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise CatalogError(f"{version}: every artifact must be an object.")
            filename = artifact.get("file")
            if (
                not isinstance(filename, str)
                or not filename
                or Path(filename).name != filename
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", filename)
            ):
                raise CatalogError(f"{version}: unsafe artifact filename.")
            if filename in seen_files:
                raise CatalogError(f"{version}: duplicate artifact filename {filename}.")
            seen_files.add(filename)
            if artifact.get("kind") not in ALLOWED_KINDS:
                raise CatalogError(f"{filename}: unsupported artifact kind.")
            if artifact.get("format") not in ALLOWED_FORMATS:
                raise CatalogError(f"{filename}: unsupported artifact format.")
            if not isinstance(artifact.get("sha256"), str) or not SHA256_PATTERN.fullmatch(
                artifact["sha256"]
            ):
                raise CatalogError(f"{filename}: invalid SHA-256 digest.")
            _validate_artifact_url(artifact.get("url"), "sorot", version, filename)


class CatalogService:
    """Load a bundled offline snapshot or a validated user-cache refresh."""

    def __init__(
        self,
        data_dir: Path | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._explicit_data_dir = data_dir
        self.cache_dir = cache_dir or default_cache_dir()
        self._cache_issue: str | None = None

    def _cached_snapshot_dir(self) -> Path | None:
        """Return the active immutable cache snapshot only when its hashes match the pointer."""
        pointer_path = self.cache_dir / "active.json"
        if not pointer_path.is_file():
            legacy_files = (
                self.cache_dir / "catalog.json",
                self.cache_dir / "sorot-downloads.json",
            )
            if any(path.exists() for path in legacy_files):
                self._cache_issue = "Legacy or incomplete cache ignored; using the bundled snapshot."
            return None

        try:
            pointer = _read_json(pointer_path, maximum_bytes=4096)
            snapshot_id = pointer.get("snapshot")
            if (
                pointer.get("schema_version") != 1
                or not isinstance(snapshot_id, str)
                or not re.fullmatch(r"[a-f0-9]{64}", snapshot_id)
            ):
                raise CatalogError("Cache pointer schema or snapshot ID is invalid.")

            cache_root = self.cache_dir.resolve()
            snapshots_root = (self.cache_dir / "snapshots").resolve()
            snapshots_root.relative_to(cache_root)
            snapshot_dir = (snapshots_root / snapshot_id).resolve()
            snapshot_dir.relative_to(snapshots_root)
            catalog_path = snapshot_dir / "catalog.json"
            downloads_path = snapshot_dir / "sorot-downloads.json"
            catalog_bytes = catalog_path.read_bytes()
            downloads_bytes = downloads_path.read_bytes()

            if len(catalog_bytes) > MAX_METADATA_BYTES or len(downloads_bytes) > MAX_METADATA_BYTES:
                raise CatalogError("Cached metadata exceeds the configured size limit.")
            actual_catalog_sha = hashlib.sha256(catalog_bytes).hexdigest()
            actual_downloads_sha = hashlib.sha256(downloads_bytes).hexdigest()
            actual_snapshot_id = hashlib.sha256(catalog_bytes + b"\\0" + downloads_bytes).hexdigest()
            if snapshot_id != actual_snapshot_id:
                raise CatalogError("Cache snapshot ID does not match its metadata contents.")
            if (
                pointer.get("catalog_sha256") != actual_catalog_sha
                or pointer.get("downloads_sha256") != actual_downloads_sha
            ):
                raise CatalogError("Cached metadata does not match its active snapshot pointer.")
            return snapshot_dir
        except (CatalogError, OSError, ValueError) as exc:
            self._cache_issue = f"Cache snapshot ignored ({exc}); using the bundled snapshot."
            return None

    @property
    def data_dir(self) -> Path:
        if self._explicit_data_dir is not None:
            return self._explicit_data_dir
        return self._cached_snapshot_dir() or bundled_data_dir()

    def load(self) -> CatalogSnapshot:
        data_dir = self.data_dir
        catalog_data = _read_json(data_dir / "catalog.json")
        download_data = _read_json(data_dir / "sorot-downloads.json")
        validate_catalog_payload(catalog_data)
        validate_download_payload(download_data)

        product_artifacts: dict[str, list[Artifact]] = {}
        for release in download_data["versions"]:
            for raw_artifact in release["artifacts"]:
                filename = raw_artifact["file"]
                url = _validate_artifact_url(
                    raw_artifact["url"],
                    "sorot",
                    release["version"],
                    filename,
                )
                directory_url = url.rsplit("/", 1)[0]
                artifact = Artifact(
                    product_id="sorot",
                    product_name="Sorot",
                    version=release["version"],
                    channel=release["channel"],
                    release_status=release["status"],
                    file=filename,
                    kind=raw_artifact["kind"],
                    format=raw_artifact["format"],
                    architecture=raw_artifact.get("architecture", "all"),
                    sha256=raw_artifact["sha256"],
                    url=url,
                    manifest_url=f"{directory_url}/release.json",
                    checksums_url=f"{directory_url}/SHA256SUMS",
                )
                product_artifacts.setdefault("sorot", []).append(artifact)

        assets_dir = data_dir / "assets"
        if not assets_dir.is_dir():
            assets_dir = bundled_data_dir() / "assets"
        applications: list[Application] = []
        for record in catalog_data["software"]:
            app_id = record["id"]
            icon_path = assets_dir / f"{app_id}-icon.svg"
            applications.append(
                Application.from_catalog_record(
                    record,
                    tuple(product_artifacts.get(app_id, [])),
                    icon_path if icon_path.is_file() else None,
                )
            )

        is_cache_snapshot = (
            self._explicit_data_dir is None and data_dir != bundled_data_dir()
        )
        data_source = "cache" if is_cache_snapshot else "bundled"
        if self._cache_issue and not is_cache_snapshot:
            data_source = "bundled fallback (cache invalid)"
        return CatalogSnapshot(
            applications=tuple(applications),
            updated_at=catalog_data["catalog"]["updatedAt"],
            data_source=data_source,
        )

    def refresh(self) -> CatalogSnapshot:
        """Validate a complete new snapshot, then atomically switch one active pointer."""
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        snapshots_dir = self.cache_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        stage_dir = Path(tempfile.mkdtemp(prefix=".staging-", dir=snapshots_dir))
        active_temp: Path | None = None
        try:
            catalog_bytes = _fetch_metadata(CATALOG_URL)
            downloads_bytes = _fetch_metadata(DOWNLOADS_URL)
            (stage_dir / "catalog.json").write_bytes(catalog_bytes)
            (stage_dir / "sorot-downloads.json").write_bytes(downloads_bytes)

            # Validate both metadata documents together before making them visible.
            CatalogService(data_dir=stage_dir).load()
            catalog_sha = hashlib.sha256(catalog_bytes).hexdigest()
            downloads_sha = hashlib.sha256(downloads_bytes).hexdigest()
            snapshot_id = hashlib.sha256(
                catalog_bytes + b"\0" + downloads_bytes
            ).hexdigest()
            snapshot_dir = snapshots_dir / snapshot_id

            existing_snapshot_valid = False
            if snapshot_dir.is_dir() and not snapshot_dir.is_symlink():
                try:
                    existing_catalog = (snapshot_dir / "catalog.json").read_bytes()
                    existing_downloads = (snapshot_dir / "sorot-downloads.json").read_bytes()
                    existing_snapshot_valid = (
                        hashlib.sha256(existing_catalog).hexdigest() == catalog_sha
                        and hashlib.sha256(existing_downloads).hexdigest() == downloads_sha
                    )
                except OSError:
                    existing_snapshot_valid = False

            if existing_snapshot_valid:
                shutil.rmtree(stage_dir, ignore_errors=True)
            else:
                if snapshot_dir.is_dir() and not snapshot_dir.is_symlink():
                    shutil.rmtree(snapshot_dir)
                elif snapshot_dir.exists() or snapshot_dir.is_symlink():
                    snapshot_dir.unlink(missing_ok=True)
                os.chmod(stage_dir, 0o700)
                os.replace(stage_dir, snapshot_dir)

            pointer = {
                "schema_version": 1,
                "snapshot": snapshot_id,
                "catalog_sha256": catalog_sha,
                "downloads_sha256": downloads_sha,
            }
            fd, active_temp_name = tempfile.mkstemp(
                prefix=".active-", suffix=".tmp", dir=self.cache_dir
            )
            active_temp = Path(active_temp_name)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(pointer, stream, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(active_temp, 0o600)
            os.replace(active_temp, self.cache_dir / "active.json")
            active_temp = None
        finally:
            if stage_dir.exists():
                shutil.rmtree(stage_dir, ignore_errors=True)
            if active_temp is not None:
                active_temp.unlink(missing_ok=True)

        return CatalogService(cache_dir=self.cache_dir).load()


def _fetch_metadata(url: str) -> bytes:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "raw.githubusercontent.com"
        or parsed.path not in {
            f"/{OWNER}/{REPOSITORY}/main/public/data/software.json",
            f"/{OWNER}/{REPOSITORY}/main/public/data/sorot-downloads.json",
        }
    ):
        raise CatalogError("Metadata URL is not in the fixed trusted-source allowlist.")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LinuxSoftwareLabCenter/0.1", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            final_url = urlsplit(response.geturl())
            if (
                final_url.scheme != "https"
                or final_url.hostname != "raw.githubusercontent.com"
                or final_url.port not in (None, 443)
                or final_url.path != parsed.path
                or final_url.query
                or final_url.fragment
            ):
                raise CatalogError("Metadata download redirected to an untrusted resource.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_METADATA_BYTES:
                raise CatalogError("Metadata response is too large.")
            body = response.read(MAX_METADATA_BYTES + 1)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise CatalogError(f"Could not refresh catalog metadata: {exc}") from exc
    if len(body) > MAX_METADATA_BYTES:
        raise CatalogError("Metadata response is too large.")
    return body
