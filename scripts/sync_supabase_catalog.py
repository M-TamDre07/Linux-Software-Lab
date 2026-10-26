#!/usr/bin/env python3
"""Synchronize the canonical static software catalogue to Supabase safely."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "public" / "data" / "software.json"
REQUIRED_FIELDS = {
    "id", "slug", "name", "version", "summary", "description", "category",
    "status", "type", "platforms", "tags", "keywords", "features",
    "detailUrl", "sourceUrl", "releaseUrl", "icon", "iconImage",
    "previewImage", "previewAlt", "updatedAt",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_SUPABASE_URL = "https://ttofugaqwthmvhvntdlc.supabase.co"
VERIFY_COLUMNS = (
    "id", "slug", "name", "version", "summary", "description", "category",
    "status", "type", "platforms", "tags", "keywords", "features",
    "detail_url", "source_url", "release_url", "icon", "icon_image",
    "preview_image", "preview_alt", "updated_at", "sort_order", "published",
)


class _NoRedirect(HTTPRedirectHandler):
    """Do not forward database credentials to redirected hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTP_OPENER = build_opener(_NoRedirect())


def validate_supabase_url(value: str) -> str:
    """Restrict credentials to the exact configured project's HTTPS origin."""
    normalized = value.strip().rstrip("/")
    if normalized != EXPECTED_SUPABASE_URL:
        raise ValueError("SUPABASE_URL must match the configured Linux Software Lab project exactly.")
    return normalized


def catalog_rows_match(expected_rows: list[dict[str, Any]], actual_rows: Any) -> bool:
    """Compare all published catalogue fields, not just record IDs."""
    if not isinstance(actual_rows, list) or len(expected_rows) != len(actual_rows):
        return False

    def project(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
        projected: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                return None
            identifier = row.get("id")
            if not isinstance(identifier, str) or identifier in projected:
                return None
            if any(column not in row for column in VERIFY_COLUMNS):
                return None
            projected[identifier] = {column: row[column] for column in VERIFY_COLUMNS}
        return projected

    expected = project(expected_rows)
    actual = project(actual_rows)
    return expected is not None and actual is not None and expected == actual


def build_stale_filter(active_ids: list[str]) -> str:
    """Build a PostgREST filter only from canonical, validated catalogue slugs."""
    if not isinstance(active_ids, list) or not active_ids:
        raise ValueError("At least one validated catalogue ID is required for the stale-row filter.")
    if any(not isinstance(identifier, str) or not SLUG.fullmatch(identifier) for identifier in active_ids):
        raise ValueError("Stale-row filter accepts only canonical lowercase application slugs.")
    if len(active_ids) != len(set(active_ids)):
        raise ValueError("Stale-row filter cannot contain duplicate application IDs.")
    return urlencode({"id": f"not.in.({','.join(active_ids)})"})


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read a valid catalogue from {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != 2:
        raise ValueError("Catalogue schemaVersion must be 2.")
    apps = data.get("software")
    if not isinstance(apps, list) or not apps:
        raise ValueError("Catalogue must contain at least one software entry.")
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    for number, app in enumerate(apps, start=1):
        if not isinstance(app, dict):
            raise ValueError(f"software[{number}] must be an object.")
        missing = REQUIRED_FIELDS - set(app)
        if missing:
            raise ValueError(f"software[{number}] is missing required fields: {', '.join(sorted(missing))}.")
        if not isinstance(app["id"], str) or not SLUG.fullmatch(app["id"]):
            raise ValueError(f"software[{number}] has an invalid id.")
        if not isinstance(app["slug"], str) or not SLUG.fullmatch(app["slug"]):
            raise ValueError(f"software[{number}] has an invalid slug.")
        if app["id"] != app["slug"]:
            raise ValueError(f"software[{number}] id must match slug.")
        if app["id"] in seen_ids or app["slug"] in seen_slugs:
            raise ValueError(f"software[{number}] duplicates an id or slug.")
        seen_ids.add(app["id"])
        seen_slugs.add(app["slug"])
        for field in ("platforms", "tags", "keywords", "features"):
            if not isinstance(app[field], list) or not all(isinstance(value, str) for value in app[field]):
                raise ValueError(f"software[{number}] field {field} must be a string array.")
        for field in ("name", "version", "summary", "description", "category", "detailUrl",
                      "sourceUrl", "releaseUrl", "icon", "iconImage", "previewImage", "previewAlt", "updatedAt"):
            if not isinstance(app[field], str):
                raise ValueError(f"software[{number}] field {field} must be a string.")
    return data


def to_record(app: dict[str, Any], sort_order: int, synced_at: str) -> dict[str, Any]:
    return {
        "id": app["id"], "slug": app["slug"], "name": app["name"],
        "version": app["version"], "summary": app["summary"],
        "description": app["description"], "category": app["category"],
        "status": app["status"], "type": app["type"],
        "platforms": app["platforms"], "tags": app["tags"],
        "keywords": app["keywords"], "features": app["features"],
        "detail_url": app["detailUrl"], "source_url": app["sourceUrl"],
        "release_url": app["releaseUrl"], "icon": app["icon"],
        "icon_image": app["iconImage"], "preview_image": app["previewImage"],
        "preview_alt": app["previewAlt"], "updated_at": app["updatedAt"],
        "sort_order": sort_order, "published": True, "synced_at": synced_at,
    }


def request_json(url: str, key: str, *, method: str = "GET",
                 payload: Any | None = None, prefer: str | None = None) -> Any:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with _HTTP_OPENER.open(request, timeout=25) as response:
            content = response.read()
            if not content:
                return None
            return json.loads(content.decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Supabase request failed with HTTP {exc.code}. Check Data API access, key scope, grants, and RLS.") from None
    except URLError as exc:
        raise RuntimeError("Could not reach the Supabase API.") from None
    except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("Supabase returned a timeout or invalid JSON response.") from None


def sync_catalog() -> int:
    data = load_catalog()
    base_url = validate_supabase_url(os.environ.get("SUPABASE_URL", ""))
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not secret_key.startswith("sb_secret_"):
        raise ValueError("SUPABASE_SECRET_KEY must be a modern sb_secret_ key stored in the CI secret store.")
    synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [to_record(app, index, synced_at) for index, app in enumerate(data["software"])]
    endpoint = base_url + "/rest/v1/software_catalog"
    request_json(endpoint + "?on_conflict=id", secret_key, method="POST",
                 payload=rows, prefer="resolution=merge-duplicates,return=minimal")

    # Mark removed entries as unpublished instead of deleting historical data.
    stale_filter = build_stale_filter([row["id"] for row in rows])
    request_json(endpoint + "?" + stale_filter, secret_key, method="PATCH",
                 payload={"published": False, "synced_at": synced_at},
                 prefer="return=minimal")

    verify_query = urlencode({
        "select": ",".join(VERIFY_COLUMNS),
        "published": "eq.true",
        "order": "sort_order.asc",
    })
    verified = request_json(endpoint + "?" + verify_query, secret_key)
    if not catalog_rows_match(rows, verified):
        raise RuntimeError("Post-sync verification detected missing or mismatched catalogue fields.")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate catalogue mapping without contacting Supabase")
    args = parser.parse_args()
    try:
        data = load_catalog()
        if args.check:
            print(f"Supabase sync preflight passed: schema v2, {len(data['software'])} catalogue entries.")
            return 0
        count = sync_catalog()
    except (ValueError, RuntimeError) as exc:
        print(f"Supabase catalogue sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"Supabase catalogue sync and verification succeeded ({count} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
