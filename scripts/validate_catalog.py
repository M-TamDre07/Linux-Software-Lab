#!/usr/bin/env python3
"""Validate software catalogue data before a static-site deployment."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "public"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_STATUS = {"released", "testing", "planned", "archived"}
ALLOWED_TYPES = {"desktop", "web", "cli", "library", "extension"}
ROOT_FIELDS = {"schemaVersion", "catalog", "software"}
CATALOG_FIELDS = {"name", "description", "searchMode", "pageSize", "updatedAt"}
REQUIRED_STRINGS = {
    "id", "slug", "name", "version", "summary", "description", "category",
    "status", "type", "detailUrl", "icon", "iconImage", "previewImage",
    "previewAlt", "updatedAt",
}
REQUIRED_ARRAYS = {"platforms", "tags", "keywords", "features"}
OPTIONAL_EMPTY_URLS = {"sourceUrl", "releaseUrl"}
APP_FIELDS = REQUIRED_STRINGS | REQUIRED_ARRAYS | OPTIONAL_EMPTY_URLS


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_https_url(value: str) -> bool:
    """Accept only absolute HTTPS URLs with a valid host and port syntax."""
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        # Accessing .port validates malformed port values; urlparse alone does not.
        parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(hostname)
        and parsed.username is None
        and parsed.password is None
    )


def _check_local_path(
    value: Any, root: Path, prefix: str, label: str, errors: list[str], app_id: str
) -> None:
    if not isinstance(value, str) or not value.startswith(prefix) or value.startswith("//"):
        errors.append(f"{app_id}: {label} must begin with {prefix}.")
        return
    relative = Path(value.lstrip("/"))
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{app_id}: {label} contains an unsafe path.")
        return
    try:
        resolved_root = root.resolve()
        resolved_path = (root / relative).resolve()
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError):
        errors.append(f"{app_id}: {label} resolves outside the website root.")
        return
    if not resolved_path.is_file():
        errors.append(f"{app_id}: missing local file {value}.")


def validate_data(data: Any, root: Path = ROOT) -> list[str]:
    """Return all catalogue errors without raising on malformed user-edited JSON."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Catalog root must be a JSON object."]

    unknown_root_fields = set(data) - ROOT_FIELDS
    if unknown_root_fields:
        errors.append("Unknown catalog root field(s): " + ", ".join(sorted(unknown_root_fields)) + ".")
    if data.get("schemaVersion") != 2:
        errors.append("schemaVersion must be 2.")

    catalog = data.get("catalog")
    if not isinstance(catalog, dict):
        errors.append("catalog metadata must be an object.")
    else:
        unknown_catalog_fields = set(catalog) - CATALOG_FIELDS
        if unknown_catalog_fields:
            errors.append("Unknown catalog metadata field(s): " + ", ".join(sorted(unknown_catalog_fields)) + ".")
        for key in ("name", "description"):
            if not isinstance(catalog.get(key), str) or not catalog[key].strip():
                errors.append(f"catalog.{key} is required.")
        if catalog.get("searchMode") != "client-side":
            errors.append("catalog.searchMode must be 'client-side'.")
        page_size = catalog.get("pageSize")
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 100:
            errors.append("catalog.pageSize must be an integer from 1 to 100.")
        if not _is_iso_date(catalog.get("updatedAt")):
            errors.append("catalog.updatedAt must use YYYY-MM-DD.")

    apps = data.get("software")
    if not isinstance(apps, list):
        return errors + ["software must be an array."]
    if not apps:
        errors.append("Catalog must contain at least one software entry.")

    ids: set[str] = set()
    slugs: set[str] = set()
    details: set[str] = set()

    for position, app in enumerate(apps, start=1):
        label = f"software[{position}]"
        if not isinstance(app, dict):
            errors.append(f"{label} must be an object.")
            continue

        raw_id = app.get("id")
        app_id = raw_id if isinstance(raw_id, str) and raw_id else label
        unknown_fields = set(app) - APP_FIELDS
        if unknown_fields:
            errors.append(f"{app_id}: unknown field(s): " + ", ".join(sorted(unknown_fields)) + ".")

        for key in REQUIRED_STRINGS:
            value = app.get(key)
            if not isinstance(value, str):
                errors.append(f"{app_id}: required string '{key}' is missing or has the wrong type.")
            elif not value.strip():
                errors.append(f"{app_id}: required string '{key}' cannot be empty.")

        for key in OPTIONAL_EMPTY_URLS:
            if key not in app or not isinstance(app[key], str):
                errors.append(f"{app_id}: required string '{key}' is missing or has the wrong type.")

        # Do not continue with operations such as len(), set membership, or date parsing
        # until each field has the type those operations expect.
        required_type_errors = [
            key for key in REQUIRED_STRINGS if not isinstance(app.get(key), str)
        ] + [
            key for key in OPTIONAL_EMPTY_URLS if not isinstance(app.get(key), str)
        ]
        if required_type_errors:
            continue

        if app["id"] in ids:
            errors.append(f"{app_id}: duplicate id.")
        ids.add(app["id"])
        if app["slug"] in slugs:
            errors.append(f"{app_id}: duplicate slug.")
        slugs.add(app["slug"])

        if not SLUG_RE.fullmatch(app["slug"]):
            errors.append(f"{app_id}: slug must use lowercase letters, numbers, and single hyphens.")
        if app["id"] != app["slug"]:
            errors.append(f"{app_id}: id and slug must match.")

        if len(app["summary"]) > 320:
            errors.append(f"{app_id}: summary cannot exceed 320 characters.")
        if app["status"] not in ALLOWED_STATUS:
            errors.append(f"{app_id}: unsupported status '{app['status']}'.")
        if app["type"] not in ALLOWED_TYPES:
            errors.append(f"{app_id}: unsupported type '{app['type']}'.")
        if not _is_iso_date(app["updatedAt"]):
            errors.append(f"{app_id}: updatedAt must use YYYY-MM-DD.")

        for key in REQUIRED_ARRAYS:
            value = app.get(key)
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                errors.append(f"{app_id}: '{key}' must be an array of non-empty strings.")
                continue
            if key in {"platforms", "tags"} and not value:
                errors.append(f"{app_id}: '{key}' cannot be empty.")
            if len(value) != len(set(value)):
                errors.append(f"{app_id}: '{key}' contains duplicate values.")

        expected_detail_url = f"/software/{app['slug']}.html"
        if app["detailUrl"] != expected_detail_url:
            errors.append(f"{app_id}: detailUrl must be '{expected_detail_url}'.")
        _check_local_path(app["detailUrl"], root, "/software/", "detailUrl", errors, app_id)
        if app["detailUrl"] in details:
            errors.append(f"{app_id}: duplicate detailUrl.")
        details.add(app["detailUrl"])
        _check_local_path(app["iconImage"], root, "/assets/images/", "iconImage", errors, app_id)
        _check_local_path(app["previewImage"], root, "/assets/images/", "previewImage", errors, app_id)

        for key in OPTIONAL_EMPTY_URLS:
            value = app[key]
            if value and not _is_https_url(value):
                errors.append(f"{app_id}: '{key}' must be empty or an HTTPS URL.")
        if app["releaseUrl"] and app["status"] != "released":
            errors.append(f"{app_id}: a download/release URL can only be shown for status 'released'.")
        if app["status"] == "released" and not app["releaseUrl"]:
            errors.append(f"{app_id}: status 'released' requires a verified HTTPS releaseUrl.")

    return errors


def validate_catalog(root: Path = ROOT, catalog_path: Path | None = None) -> list[str]:
    path = catalog_path or (root / "data" / "software.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"Could not read catalog {path}: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON in {path}: {exc}"]
    return validate_data(data, root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Website public directory")
    parser.add_argument("--catalog", type=Path, default=None, help="Catalog JSON path (defaults to ROOT/data/software.json)")
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.catalog.resolve() if args.catalog else root / "data" / "software.json"
    errors = validate_catalog(root, path)
    if errors:
        print("Catalog validation FAILED:")
        for error in errors:
            print(" - " + error)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Catalog valid: {len(data['software'])} software entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
