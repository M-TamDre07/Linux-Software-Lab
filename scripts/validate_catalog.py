#!/usr/bin/env python3
"""Validate the software catalog before a static-site deployment."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_STATUS = {"released", "testing", "planned", "archived"}
ALLOWED_TYPES = {"desktop", "web", "cli", "library", "extension"}


def _is_https_url(value: str) -> bool:
    if any(char.isspace() for char in value):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.username is None and parsed.password is None


def _check_local_path(value: Any, root: Path, prefix: str, label: str, errors: list[str], app_id: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix) or value.startswith("//"):
        errors.append(f"{app_id}: {label} must begin with {prefix}.")
        return
    relative = value.lstrip("/")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{app_id}: {label} contains an unsafe path.")
        return
    if not (root / path).is_file():
        errors.append(f"{app_id}: missing local file {value}.")


def validate_data(data: Any, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Catalog root must be a JSON object."]
    if data.get("schemaVersion") != 2:
        errors.append("schemaVersion must be 2.")

    catalog = data.get("catalog")
    if not isinstance(catalog, dict):
        errors.append("catalog metadata must be an object.")
    else:
        if not isinstance(catalog.get("name"), str) or not catalog["name"].strip():
            errors.append("catalog.name is required.")
        if not isinstance(catalog.get("description"), str) or not catalog["description"].strip():
            errors.append("catalog.description is required.")
        if catalog.get("searchMode") != "client-side":
            errors.append("catalog.searchMode must be 'client-side'.")
        page_size = catalog.get("pageSize")
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 100:
            errors.append("catalog.pageSize must be an integer from 1 to 100.")
        try:
            date.fromisoformat(str(catalog.get("updatedAt", "")))
        except ValueError:
            errors.append("catalog.updatedAt must use YYYY-MM-DD.")

    apps = data.get("software")
    if not isinstance(apps, list):
        return errors + ["software must be an array."]
    if not apps:
        errors.append("Catalog must contain at least one software entry.")

    ids: set[str] = set()
    slugs: set[str] = set()
    details: set[str] = set()
    required_strings = (
        "id", "slug", "name", "version", "summary", "description",
        "category", "status", "type", "detailUrl", "icon", "iconImage",
        "previewImage", "previewAlt", "updatedAt",
    )
    required_arrays = ("platforms", "tags", "keywords", "features")

    for position, app in enumerate(apps, start=1):
        if not isinstance(app, dict):
            errors.append(f"software[{position}] must be an object.")
            continue
        app_id = str(app.get("id", f"software[{position}]"))
        for key in ("sourceUrl", "releaseUrl"):
            if key not in app or not isinstance(app[key], str):
                errors.append(f"{app_id}: required string '{key}' is missing.")
        for key in required_strings:
            if not isinstance(app.get(key), str) or not app[key].strip():
                errors.append(f"{app_id}: required string '{key}' is missing.")

        if not all(isinstance(app.get(key), str) and app[key].strip() for key in ("id", "slug", "detailUrl", "name")):
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
        try:
            date.fromisoformat(app["updatedAt"])
        except ValueError:
            errors.append(f"{app_id}: updatedAt must use YYYY-MM-DD.")

        for key in required_arrays:
            value = app.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                errors.append(f"{app_id}: '{key}' must be an array of non-empty strings.")
            else:
                if key in ("platforms", "tags") and not value:
                    errors.append(f"{app_id}: '{key}' cannot be empty.")
                if len(value) != len(set(value)):
                    errors.append(f"{app_id}: '{key}' contains duplicate values.")

        detail = app["detailUrl"]
        _check_local_path(detail, root, "/software/", "detailUrl", errors, app_id)
        if detail in details:
            errors.append(f"{app_id}: duplicate detailUrl.")
        details.add(detail)
        _check_local_path(app.get("iconImage"), root, "/assets/images/", "iconImage", errors, app_id)
        _check_local_path(app.get("previewImage"), root, "/assets/images/", "previewImage", errors, app_id)

        for key in ("sourceUrl", "releaseUrl"):
            value = app.get(key, "")
            if value and (not isinstance(value, str) or not _is_https_url(value)):
                errors.append(f"{app_id}: '{key}' must be empty or an HTTPS URL.")
        if app.get("releaseUrl") and app.get("status") != "released":
            errors.append(f"{app_id}: a download/release URL can only be shown for status 'released'.")

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
    parser.add_argument("--root", type=Path, default=ROOT, help="Website repository root")
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
