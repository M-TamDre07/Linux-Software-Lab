"""Shared local/remote catalogue reader with strict release metadata validation."""

from __future__ import annotations

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
        parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.username is None
        and parsed.password is None
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

    @property
    def data_dir(self) -> Path:
        if self._explicit_data_dir is not None:
            return self._explicit_data_dir
        cached_catalog = self.cache_dir / "catalog.json"
        cached_downloads = self.cache_dir / "sorot-downloads.json"
        if cached_catalog.is_file() and cached_downloads.is_file():
            return self.cache_dir
        return bundled_data_dir()

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

        return CatalogSnapshot(
            applications=tuple(applications),
            updated_at=catalog_data["catalog"]["updatedAt"],
            data_source="cache" if data_dir == self.cache_dir else "bundled",
        )

    def refresh(self) -> CatalogSnapshot:
        """Fetch the two public JSON documents, validate them together, and replace cache atomically."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="lsl-refresh-", dir=self.cache_dir) as tmp:
            temp_dir = Path(tmp)
            (temp_dir / "catalog.json").write_bytes(_fetch_metadata(CATALOG_URL))
            (temp_dir / "sorot-downloads.json").write_bytes(_fetch_metadata(DOWNLOADS_URL))
            CatalogService(data_dir=temp_dir).load()
            os.replace(temp_dir / "catalog.json", self.cache_dir / "catalog.json")
            os.replace(temp_dir / "sorot-downloads.json", self.cache_dir / "sorot-downloads.json")
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
            if final_url.scheme != "https" or final_url.hostname != "raw.githubusercontent.com":
                raise CatalogError("Metadata download redirected to an untrusted host.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_METADATA_BYTES:
                raise CatalogError("Metadata response is too large.")
            body = response.read(MAX_METADATA_BYTES + 1)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise CatalogError(f"Could not refresh catalog metadata: {exc}") from exc
    if len(body) > MAX_METADATA_BYTES:
        raise CatalogError("Metadata response is too large.")
    return body
