"""Shared website/launcher catalogue, generic release-index loader, and atomic cache."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .models import Application, Artifact, CatalogSnapshot


OWNER = "M-TamDre07"
REPOSITORY = "Linux-Software-Lab"
RAW_ROOT = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/main"
CATALOG_URL = f"{RAW_ROOT}/public/data/software.json"
DISTRIBUTION_INDEX_URL = f"{RAW_ROOT}/public/data/distribution-index.json"
MAX_METADATA_BYTES = 5 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
FILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
ALLOWED_STATUSES = {"released", "testing", "planned", "archived"}
ALLOWED_CHANNELS = {"stable", "beta", "alpha", "development"}
ALLOWED_FORMATS = {
    "deb", "rpm", "pkg.tar.zst", "flatpak", "flatpakref", "AppImage", "tar.gz", "zip",
}
ALLOWED_KINDS = {
    "native-package", "debian-package", "rpm-package", "arch-package",
    "flatpak-bundle", "flatpak-ref", "appimage", "source-archive",
}
ALLOWED_ARCHITECTURES = {
    "all", "any", "noarch", "x86_64", "amd64", "aarch64", "arm64", "armv7l",
}
PACKAGE_KIND_FORMATS = {
    "debian-package": {"deb"},
    "rpm-package": {"rpm"},
    "arch-package": {"pkg.tar.zst"},
    "flatpak-bundle": {"flatpak"},
    "flatpak-ref": {"flatpakref"},
    "appimage": {"AppImage"},
    "source-archive": {"tar.gz", "zip"},
    "native-package": {"deb", "rpm", "pkg.tar.zst"},
}
FAMILY_PACKAGE = {
    "debian-family": ("deb", "apt"),
    "arch-family": ("pkg.tar.zst", "pacman"),
    "fedora-family": ("rpm", "dnf"),
    "suse-family": ("rpm", "zypper"),
}


class CatalogError(ValueError):
    """Raised when shared catalog/release metadata is invalid or inconsistent."""


def bundled_data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return base / "linux-software-lab-center"


def _read_json_bytes(content: bytes, source: str, maximum_bytes: int) -> dict[str, Any]:
    if len(content) > maximum_bytes:
        raise CatalogError(f"Metadata file is larger than {maximum_bytes} bytes: {source}")
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"Metadata root must be an object: {source}")
    return data


def _read_json(path: Path, maximum_bytes: int = MAX_METADATA_BYTES) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size > maximum_bytes:
            raise CatalogError(f"Metadata file is larger than {maximum_bytes} bytes: {path.name}")
        return _read_json_bytes(path.read_bytes(), str(path), maximum_bytes)
    except OSError as exc:
        raise CatalogError(f"Cannot read metadata file {path}: {exc}") from exc


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and port in (None, 443)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _validate_manifest_url(url: Any, product_id: str, version: str) -> str:
    if not isinstance(product_id, str) or not ID_PATTERN.fullmatch(product_id):
        raise CatalogError("Manifest references require a valid product ID.")
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise CatalogError(f"{product_id}: manifest version has an invalid format.")
    if not _is_https_url(url):
        raise CatalogError(f"{product_id} {version}: manifest URL must use HTTPS.")
    parsed = urlsplit(url)
    expected_path = (
        f"/{OWNER}/{REPOSITORY}/main/apps/{product_id}/releases/{version}/release.json"
    )
    if (
        parsed.hostname != "raw.githubusercontent.com"
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise CatalogError(
            f"{product_id} {version}: manifest URL must point to its canonical version directory."
        )
    return url


def validate_catalog_payload(data: dict[str, Any]) -> None:
    if data.get("schemaVersion") != 2:
        raise CatalogError("Catalog schemaVersion must be 2.")
    metadata = data.get("catalog")
    if not isinstance(metadata, dict):
        raise CatalogError("Catalog metadata block is missing.")
    updated_at = metadata.get("updatedAt")
    if not isinstance(updated_at, str):
        raise CatalogError("Catalog updatedAt must use YYYY-MM-DD.")
    try:
        date.fromisoformat(updated_at)
    except ValueError as exc:
        raise CatalogError("Catalog updatedAt must use YYYY-MM-DD.") from exc
    applications = data.get("software")
    if not isinstance(applications, list) or not applications:
        raise CatalogError("Catalog must contain a non-empty software list.")

    seen_ids: set[str] = set()
    for app in applications:
        if not isinstance(app, dict):
            raise CatalogError("Every catalog item must be an object.")
        app_id = app.get("id")
        if not isinstance(app_id, str) or not ID_PATTERN.fullmatch(app_id):
            raise CatalogError("Every app needs a valid lowercase ID.")
        if app_id in seen_ids:
            raise CatalogError(f"Duplicate application ID: {app_id}")
        seen_ids.add(app_id)
        for field in ("slug", "name", "version", "summary", "description", "category", "status", "type"):
            if not isinstance(app.get(field), str) or not app[field].strip():
                raise CatalogError(f"{app_id}: required field {field!r} is empty.")
        if app["slug"] != app_id:
            raise CatalogError(f"{app_id}: slug and id must match for release-directory lookup.")
        if app["status"] not in ALLOWED_STATUSES:
            raise CatalogError(f"{app_id}: unsupported status {app['status']!r}.")
        for field in ("platforms", "tags", "keywords", "features"):
            value = app.get(field, [])
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise CatalogError(f"{app_id}: {field} must be a list of strings.")
        for field in ("sourceUrl", "releaseUrl"):
            value = app.get(field, "")
            if value and not _is_https_url(value):
                raise CatalogError(f"{app_id}: {field} must be empty or a valid HTTPS URL.")


def validate_distribution_index(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise CatalogError("Distribution index schema_version must be 1.")
    updated_at = data.get("updated_at")
    if not isinstance(updated_at, str):
        raise CatalogError("Distribution index updated_at must use YYYY-MM-DD.")
    try:
        date.fromisoformat(updated_at)
    except ValueError as exc:
        raise CatalogError("Distribution index updated_at must use YYYY-MM-DD.") from exc

    policy = data.get("detection_policy")
    if not isinstance(policy, dict) or not all(
        isinstance(policy.get(field), str) and policy[field].strip()
        for field in ("native_launcher", "browser", "install_metadata")
    ):
        raise CatalogError("Distribution index needs its complete detection policy.")

    distributions = data.get("distributions")
    if not isinstance(distributions, list) or not distributions:
        raise CatalogError("Distribution index must contain distribution guidance.")
    seen_distributions: set[str] = set()
    valid_families = set(FAMILY_PACKAGE) | {"unknown"}
    for distro in distributions:
        if not isinstance(distro, dict):
            raise CatalogError("Every distribution entry must be an object.")
        distro_id = distro.get("id")
        family = distro.get("family")
        if not isinstance(distro_id, str) or not ID_PATTERN.fullmatch(distro_id):
            raise CatalogError("Distribution entries need valid lowercase IDs.")
        if distro_id in seen_distributions:
            raise CatalogError(f"Duplicate distribution entry: {distro_id}")
        seen_distributions.add(distro_id)
        if family not in valid_families:
            raise CatalogError(f"{distro_id}: unsupported distribution family.")
        if not isinstance(distro.get("label"), str) or not distro["label"].strip():
            raise CatalogError(f"{distro_id}: label is required.")
        if not isinstance(distro.get("note"), str) or not distro["note"].strip():
            raise CatalogError(f"{distro_id}: user-facing note is required.")
        source_formats = distro.get("source_formats")
        if not isinstance(source_formats, list) or any(
            value not in {"tar.gz", "zip"} for value in source_formats
        ):
            raise CatalogError(f"{distro_id}: source_formats must contain only source archive formats.")
        package_format = distro.get("package_format")
        package_manager = distro.get("package_manager")
        if family in FAMILY_PACKAGE:
            expected_format, expected_manager = FAMILY_PACKAGE[family]
            if package_format != expected_format or package_manager != expected_manager:
                raise CatalogError(f"{distro_id}: package format and manager do not match {family}.")
        elif package_format is not None or package_manager is not None:
            raise CatalogError(f"{distro_id}: unknown families cannot advertise a native package adapter.")

    products = data.get("products")
    if not isinstance(products, list):
        raise CatalogError("Distribution index products must be a list.")
    seen_products: set[str] = set()
    for product in products:
        if not isinstance(product, dict):
            raise CatalogError("Every release-index product must be an object.")
        product_id = product.get("id")
        if not isinstance(product_id, str) or not ID_PATTERN.fullmatch(product_id):
            raise CatalogError("Release-index products need valid lowercase IDs.")
        if product_id in seen_products:
            raise CatalogError(f"Duplicate product in distribution index: {product_id}")
        seen_products.add(product_id)
        releases = product.get("manifests")
        if not isinstance(releases, list):
            raise CatalogError(f"{product_id}: manifests must be a list.")
        seen_versions: set[str] = set()
        for release in releases:
            if not isinstance(release, dict):
                raise CatalogError(f"{product_id}: manifest references must be objects.")
            version = release.get("version")
            if not isinstance(version, str) or version in seen_versions:
                raise CatalogError(f"{product_id}: duplicate or missing manifest version.")
            seen_versions.add(version)
            _validate_manifest_url(release.get("url"), product_id, version)


def validate_distribution_manifest(
    data: dict[str, Any],
    product_id: str,
    product_name: str,
    version: str,
) -> None:
    if data.get("schema_version") != 1:
        raise CatalogError(f"{product_id} {version}: unsupported manifest schema.")
    manifest_product = data.get("product")
    if not isinstance(manifest_product, str) or manifest_product.casefold() not in {
        product_id.casefold(), product_name.casefold(),
    }:
        raise CatalogError(f"{product_id} {version}: manifest names the wrong product.")
    if data.get("version") != version:
        raise CatalogError(f"{product_id} {version}: manifest version mismatch.")
    if data.get("channel") not in ALLOWED_CHANNELS:
        raise CatalogError(f"{product_id} {version}: invalid release channel.")
    if data.get("status") not in ALLOWED_STATUSES:
        raise CatalogError(f"{product_id} {version}: invalid release status.")
    notes_url = data.get("notes_url", "")
    if notes_url and not _is_https_url(notes_url):
        raise CatalogError(f"{product_id} {version}: notes_url must use HTTPS.")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        raise CatalogError(f"{product_id} {version}: artifacts must be a list.")

    seen_files: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CatalogError(f"{product_id} {version}: every artifact must be an object.")
        filename = artifact.get("file")
        if not isinstance(filename, str) or not FILE_PATTERN.fullmatch(filename):
            raise CatalogError(f"{product_id} {version}: unsafe artifact filename.")
        if Path(filename).name != filename or filename in seen_files:
            raise CatalogError(f"{product_id} {version}: duplicate/unsafe artifact filename {filename}.")
        seen_files.add(filename)
        kind = artifact.get("kind")
        package_format = artifact.get("format")
        digest = artifact.get("sha256")
        if kind not in ALLOWED_KINDS or package_format not in ALLOWED_FORMATS:
            raise CatalogError(f"{filename}: unsupported artifact kind or format.")
        if package_format not in PACKAGE_KIND_FORMATS[kind]:
            raise CatalogError(f"{filename}: format {package_format} does not match kind {kind}.")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise CatalogError(f"{filename}: invalid SHA-256 digest.")

        architecture = artifact.get("architecture", "all")
        if architecture not in ALLOWED_ARCHITECTURES:
            raise CatalogError(f"{filename}: unsupported CPU architecture.")
        if kind != "source-archive" and "architecture" not in artifact:
            raise CatalogError(f"{filename}: native artifacts must declare their architecture.")
        if kind != "source-archive" and package_format in {"deb", "rpm", "pkg.tar.zst"}:
            if architecture == "all" and package_format == "pkg.tar.zst":
                raise CatalogError(f"{filename}: Arch packages must declare any or a CPU architecture.")

        allowed_artifact_fields = {
            "file", "kind", "format", "architecture", "sha256", "download_url",
            "signature_url", "minimum_os", "install_scope",
        }
        unknown = set(artifact) - allowed_artifact_fields
        if unknown:
            raise CatalogError(
                f"{filename}: unsupported metadata fields: {', '.join(sorted(unknown))}."
            )
        if artifact.get("download_url"):
            _validate_artifact_url(
                artifact["download_url"], product_id, version, filename
            )
        signature_url = artifact.get("signature_url")
        if signature_url and not _is_https_url(signature_url):
            raise CatalogError(f"{filename}: signature_url must use HTTPS.")
        if artifact.get("install_scope") not in {None, "user", "system", "not-applicable"}:
            raise CatalogError(f"{filename}: unsupported install_scope.")


def _validate_artifact_url(url: Any, product_id: str, version: str, filename: str) -> str:
    if not _is_https_url(url):
        raise CatalogError(f"{filename}: download URL must use HTTPS.")
    parsed = urlsplit(url)
    expected_path = (
        f"/{OWNER}/{REPOSITORY}/main/apps/{product_id}/releases/{version}/{filename}"
    )
    if (
        parsed.hostname != "raw.githubusercontent.com"
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise CatalogError(f"{filename}: download URL is outside its trusted version directory.")
    return url


def _manifest_relative_path(product_id: str, version: str) -> Path:
    return Path("manifests") / product_id / version / "release.json"


def _manifest_key(product_id: str, version: str) -> str:
    return f"{product_id}/{version}"


def _snapshot_digest(
    catalog_bytes: bytes,
    index_bytes: bytes,
    manifest_bytes: dict[str, bytes],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"catalog.json\0")
    digest.update(catalog_bytes)
    digest.update(b"\0distribution-index.json\0")
    digest.update(index_bytes)
    for key in sorted(manifest_bytes):
        digest.update(b"\0")
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(manifest_bytes[key])
    return digest.hexdigest()


def _manifest_entries(index_data: dict[str, Any]) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for product in index_data["products"]:
        for release in product["manifests"]:
            entries.append((product["id"], release["version"], release["url"]))
    return entries


def _load_snapshot_files(
    data_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], dict[str, bytes]]:
    catalog_data = _read_json(data_dir / "catalog.json")
    index_data = _read_json(data_dir / "distribution-index.json")
    validate_catalog_payload(catalog_data)
    validate_distribution_index(index_data)

    application_records = {
        app["id"]: app for app in catalog_data["software"]
    }
    indexed_ids = {product["id"] for product in index_data["products"]}
    if indexed_ids != set(application_records):
        missing = sorted(set(application_records) - indexed_ids)
        extra = sorted(indexed_ids - set(application_records))
        raise CatalogError(
            f"Catalog/index product IDs differ (missing index: {missing}; unknown index IDs: {extra})."
        )

    manifest_payloads: dict[str, dict[str, Any]] = {}
    manifest_bytes_by_key: dict[str, bytes] = {}
    for product_id, version, manifest_url in _manifest_entries(index_data):
        app_record = application_records[product_id]
        relative_path = _manifest_relative_path(product_id, version)
        manifest_path = (data_dir / relative_path).resolve()
        try:
            manifest_path.relative_to(data_dir.resolve())
            content = manifest_path.read_bytes()
        except (OSError, ValueError) as exc:
            raise CatalogError(
                f"Missing or unsafe release manifest for {product_id} {version}: {exc}"
            ) from exc
        manifest = _read_json_bytes(content, str(relative_path), MAX_MANIFEST_BYTES)
        validate_distribution_manifest(manifest, product_id, app_record["name"], version)
        _validate_manifest_url(manifest_url, product_id, version)
        key = _manifest_key(product_id, version)
        manifest_payloads[key] = manifest
        manifest_bytes_by_key[key] = content
    return catalog_data, index_data, manifest_payloads, manifest_bytes_by_key


class CatalogService:
    """Read the shared website catalogue and release manifests; keep offline snapshots intact."""

    def __init__(
        self,
        data_dir: Path | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._explicit_data_dir = data_dir
        self.cache_dir = cache_dir or default_cache_dir()
        self._cache_issue: str | None = None

    def _cached_snapshot_dir(self) -> Path | None:
        pointer_path = self.cache_dir / "active.json"
        if not pointer_path.is_file():
            if any(
                (self.cache_dir / name).exists()
                for name in ("catalog.json", "distribution-index.json")
            ):
                self._cache_issue = "Legacy or incomplete cache ignored; using the bundled snapshot."
            return None

        try:
            pointer = _read_json(pointer_path, maximum_bytes=64 * 1024)
            snapshot_id = pointer.get("snapshot")
            if (
                pointer.get("schema_version") != 1
                or not isinstance(snapshot_id, str)
                or not SHA256_PATTERN.fullmatch(snapshot_id)
            ):
                raise CatalogError("Cache pointer schema or snapshot ID is invalid.")

            cache_root = self.cache_dir.resolve()
            snapshots_root = (self.cache_dir / "snapshots").resolve()
            snapshots_root.relative_to(cache_root)
            snapshot_dir = (snapshots_root / snapshot_id).resolve()
            snapshot_dir.relative_to(snapshots_root)
            catalog_data, index_data, _, manifests = _load_snapshot_files(snapshot_dir)

            catalog_bytes = (snapshot_dir / "catalog.json").read_bytes()
            index_bytes = (snapshot_dir / "distribution-index.json").read_bytes()
            catalog_hash = hashlib.sha256(catalog_bytes).hexdigest()
            index_hash = hashlib.sha256(index_bytes).hexdigest()
            manifest_hashes = {
                key: hashlib.sha256(value).hexdigest() for key, value in manifests.items()
            }
            if pointer.get("catalog_sha256") != catalog_hash:
                raise CatalogError("Cached catalog does not match its active snapshot pointer.")
            if pointer.get("index_sha256") != index_hash:
                raise CatalogError("Cached distribution index does not match its active pointer.")
            if pointer.get("manifest_sha256s") != manifest_hashes:
                raise CatalogError("Cached release manifests do not match their active pointer.")
            if _snapshot_digest(catalog_bytes, index_bytes, manifests) != snapshot_id:
                raise CatalogError("Cache snapshot ID does not match its metadata contents.")
            # Keep these names referenced to emphasize that cache validation includes the full schema.
            _ = catalog_data, index_data
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
        catalog_data, index_data, manifests, _ = _load_snapshot_files(data_dir)
        product_artifacts: dict[str, list[Artifact]] = {}
        for product_id, version, manifest_url in _manifest_entries(index_data):
            app_record = next(item for item in catalog_data["software"] if item["id"] == product_id)
            manifest = manifests[_manifest_key(product_id, version)]
            version_dir = manifest_url.rsplit("/", 1)[0]
            checksum_url = f"{version_dir}/SHA256SUMS"
            for raw_artifact in manifest["artifacts"]:
                filename = raw_artifact["file"]
                download_url = raw_artifact.get("download_url") or f"{version_dir}/{filename}"
                _validate_artifact_url(download_url, product_id, version, filename)
                artifact = Artifact(
                    product_id=product_id,
                    product_name=app_record["name"],
                    version=version,
                    channel=manifest["channel"],
                    release_status=manifest["status"],
                    file=filename,
                    kind=raw_artifact["kind"],
                    format=raw_artifact["format"],
                    architecture=raw_artifact.get("architecture", "all"),
                    sha256=raw_artifact["sha256"],
                    url=download_url,
                    manifest_url=manifest_url,
                    checksums_url=checksum_url,
                )
                product_artifacts.setdefault(product_id, []).append(artifact)

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

        is_cache_snapshot = self._explicit_data_dir is None and data_dir != bundled_data_dir()
        data_source = "cache" if is_cache_snapshot else "bundled"
        if self._cache_issue and not is_cache_snapshot:
            data_source = "bundled fallback (cache invalid)"
        return CatalogSnapshot(
            applications=tuple(applications),
            updated_at=index_data["updated_at"],
            data_source=data_source,
        )

    def refresh(self) -> CatalogSnapshot:
        """Fetch and validate the catalog, index, and every indexed release before one atomic swap."""
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.cache_dir, 0o700)
        snapshots_dir = self.cache_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(snapshots_dir, 0o700)

        stage_dir = Path(tempfile.mkdtemp(prefix=".staging-", dir=snapshots_dir))
        active_temp: Path | None = None
        try:
            catalog_bytes = _fetch_metadata(CATALOG_URL)
            index_bytes = _fetch_metadata(DISTRIBUTION_INDEX_URL)
            (stage_dir / "catalog.json").write_bytes(catalog_bytes)
            (stage_dir / "distribution-index.json").write_bytes(index_bytes)

            catalog_data = _read_json_bytes(catalog_bytes, "software.json", MAX_METADATA_BYTES)
            index_data = _read_json_bytes(index_bytes, "distribution-index.json", MAX_METADATA_BYTES)
            validate_catalog_payload(catalog_data)
            validate_distribution_index(index_data)
            application_records = {
                app["id"]: app for app in catalog_data["software"]
            }
            indexed_ids = {product["id"] for product in index_data["products"]}
            if indexed_ids != set(application_records):
                raise CatalogError("Catalog and distribution index do not contain the same product IDs.")

            fetched_manifests: dict[str, bytes] = {}
            for product_id, version, manifest_url in _manifest_entries(index_data):
                manifest_bytes = _fetch_manifest(manifest_url, product_id, version)
                manifest = _read_json_bytes(
                    manifest_bytes, f"{product_id} {version} release.json", MAX_MANIFEST_BYTES
                )
                validate_distribution_manifest(
                    manifest, product_id, application_records[product_id]["name"], version
                )
                relative_path = _manifest_relative_path(product_id, version)
                manifest_path = stage_dir / relative_path
                manifest_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                manifest_path.write_bytes(manifest_bytes)
                fetched_manifests[_manifest_key(product_id, version)] = manifest_bytes

            CatalogService(data_dir=stage_dir).load()
            snapshot_id = _snapshot_digest(catalog_bytes, index_bytes, fetched_manifests)
            snapshot_dir = snapshots_dir / snapshot_id

            if snapshot_dir.exists() or snapshot_dir.is_symlink():
                existing_valid = False
                try:
                    _, _, _, existing_manifests = _load_snapshot_files(snapshot_dir)
                    existing_catalog = (snapshot_dir / "catalog.json").read_bytes()
                    existing_index = (snapshot_dir / "distribution-index.json").read_bytes()
                    existing_valid = (
                        _snapshot_digest(existing_catalog, existing_index, existing_manifests)
                        == snapshot_id
                    )
                except (CatalogError, OSError, ValueError):
                    existing_valid = False
                if existing_valid:
                    shutil.rmtree(stage_dir, ignore_errors=True)
                else:
                    if snapshot_dir.is_dir() and not snapshot_dir.is_symlink():
                        shutil.rmtree(snapshot_dir)
                    else:
                        snapshot_dir.unlink(missing_ok=True)
                    os.chmod(stage_dir, 0o700)
                    os.replace(stage_dir, snapshot_dir)
            else:
                os.chmod(stage_dir, 0o700)
                os.replace(stage_dir, snapshot_dir)

            pointer = {
                "schema_version": 1,
                "snapshot": snapshot_id,
                "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
                "manifest_sha256s": {
                    key: hashlib.sha256(value).hexdigest()
                    for key, value in fetched_manifests.items()
                },
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
    allowed_paths = {
        f"/{OWNER}/{REPOSITORY}/main/public/data/software.json",
        f"/{OWNER}/{REPOSITORY}/main/public/data/distribution-index.json",
    }
    if (
        parsed.scheme != "https"
        or parsed.hostname != "raw.githubusercontent.com"
        or parsed.port not in (None, 443)
        or parsed.path not in allowed_paths
        or parsed.query
        or parsed.fragment
    ):
        raise CatalogError("Metadata URL is not in the fixed trusted-source allowlist.")
    return _fetch_bytes(url, parsed.path, MAX_METADATA_BYTES, "catalog metadata")


def _fetch_manifest(url: str, product_id: str, version: str) -> bytes:
    _validate_manifest_url(url, product_id, version)
    parsed = urlsplit(url)
    return _fetch_bytes(url, parsed.path, MAX_MANIFEST_BYTES, f"{product_id} {version} manifest")


def _fetch_bytes(url: str, expected_path: str, maximum_bytes: int, label: str) -> bytes:
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
                or final_url.path != expected_path
                or final_url.query
                or final_url.fragment
            ):
                raise CatalogError(f"{label} download redirected to an untrusted resource.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > maximum_bytes:
                raise CatalogError(f"{label} response is too large.")
            body = response.read(maximum_bytes + 1)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise CatalogError(f"Could not fetch {label}: {exc}") from exc
    if len(body) > maximum_bytes:
        raise CatalogError(f"{label} response is too large.")
    return body
