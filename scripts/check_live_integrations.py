#!/usr/bin/env python3
"""Read-only smoke test of the GitHub catalogue, deployed Vercel JSON, and Supabase mirror."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from sync_supabase_catalog import (
    CATALOG_PATH,
    EXPECTED_SUPABASE_URL,
    VERIFY_COLUMNS,
    catalog_rows_match,
    load_catalog,
    to_record,
    validate_supabase_url,
)

ROOT = Path(__file__).resolve().parents[1]
SUPABASE_CONFIG = ROOT / "public" / "assets" / "js" / "supabase-config.js"
PRODUCTION_CATALOG_URL = "https://linux-software-lab.vercel.app/data/software.json"
HTTP_TIMEOUT_SECONDS = 20


class IntegrationCheckError(RuntimeError):
    """Raised when a deployed service fails its read-only integration check."""


def load_public_supabase_config(path: Path = SUPABASE_CONFIG) -> tuple[str, str]:
    """Read the project's browser-safe URL and publishable key without evaluating JavaScript."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise IntegrationCheckError("Supabase browser configuration cannot be read as UTF-8.") from exc

    url_match = re.search(r'\burl\s*:\s*(["\'])(.*?)\1', source)
    key_match = re.search(r'\bpublishableKey\s*:\s*(["\'])(.*?)\1', source)
    if not url_match or not key_match:
        raise IntegrationCheckError("Expected url and publishableKey entries were not found in browser configuration.")

    try:
        url = validate_supabase_url(url_match.group(2))
    except ValueError as exc:
        raise IntegrationCheckError("Browser configuration points to an unexpected Supabase project.") from exc

    key = key_match.group(2).strip()
    if not key.startswith("sb_publishable_"):
        raise IntegrationCheckError("Only the modern public sb_publishable_ key is permitted for read-only checks.")
    if any(ord(char) < 33 or ord(char) == 127 for char in key):
        raise IntegrationCheckError("The public Supabase key contains invalid whitespace/control characters.")
    return url, key


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    request = Request(url, headers={"Accept": "application/json", **(headers or {})}, method="GET")
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise IntegrationCheckError(f"Read-only GET returned HTTP {response.status}.")
            raw = response.read()
    except HTTPError as exc:
        raise IntegrationCheckError(f"Read-only GET failed with HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise IntegrationCheckError("The remote endpoint could not be reached. Check deployment/network status.") from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise IntegrationCheckError("The remote endpoint did not return valid UTF-8 JSON.") from None


def _catalogue_diff(expected: Any, actual: Any) -> list[str]:
    """Summarise source-vs-deployment differences without dumping untrusted values."""
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return ["catalogue root is not an object"]
    issues: list[str] = []
    for key in sorted(set(expected) | set(actual)):
        if key == "software":
            continue
        if expected.get(key) != actual.get(key):
            issues.append(f"top-level field '{key}' differs")

    expected_rows = expected.get("software")
    actual_rows = actual.get("software")
    if not isinstance(expected_rows, list) or not isinstance(actual_rows, list):
        issues.append("'software' is missing or is not an array")
        return issues

    def index_rows(rows: list[Any]) -> dict[str, dict[str, Any]] | None:
        indexed: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in indexed:
                return None
            indexed[row["id"]] = row
        return indexed

    expected_by_id = index_rows(expected_rows)
    actual_by_id = index_rows(actual_rows)
    if expected_by_id is None or actual_by_id is None:
        issues.append("catalogue contains a malformed row or duplicate ID")
        return issues

    for identifier in sorted(set(expected_by_id) - set(actual_by_id)):
        issues.append(f"application '{identifier}' is missing from deployment")
    for identifier in sorted(set(actual_by_id) - set(expected_by_id)):
        issues.append(f"deployment contains unexpected application '{identifier}'")
    for identifier in sorted(set(expected_by_id) & set(actual_by_id)):
        left, right = expected_by_id[identifier], actual_by_id[identifier]
        for field in sorted(set(left) | set(right)):
            if left.get(field) != right.get(field):
                issues.append(f"application '{identifier}' field '{field}' differs")
                if len(issues) >= 50:
                    issues.append("difference report truncated at 50 issues")
                    return issues
    if [row.get("id") for row in expected_rows] != [row.get("id") for row in actual_rows]:
        issues.append("catalogue ordering differs from the canonical repository")
    return issues


def _supabase_diff(expected: list[dict[str, Any]], actual: Any) -> list[str]:
    """Identify mirror drift using exactly the fields verified by the trusted sync process."""
    if not isinstance(actual, list):
        return ["published catalogue response is not an array"]
    expected_by_id = {row["id"]: row for row in expected}
    actual_by_id: dict[str, dict[str, Any]] = {}
    for row in actual:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            return ["published catalogue contains a malformed row"]
        if row["id"] in actual_by_id:
            return [f"published catalogue contains duplicate ID '{row['id']}'"]
        actual_by_id[row["id"]] = row

    issues: list[str] = []
    for identifier in sorted(set(expected_by_id) - set(actual_by_id)):
        issues.append(f"application '{identifier}' is missing from Supabase")
    for identifier in sorted(set(actual_by_id) - set(expected_by_id)):
        issues.append(f"Supabase contains unexpected published application '{identifier}'")
    for identifier in sorted(set(expected_by_id) & set(actual_by_id)):
        expected_row, actual_row = expected_by_id[identifier], actual_by_id[identifier]
        for column in VERIFY_COLUMNS:
            if expected_row.get(column) != actual_row.get(column):
                issues.append(f"application '{identifier}' field '{column}' differs in Supabase")
                if len(issues) >= 50:
                    issues.append("difference report truncated at 50 issues")
                    return issues
    if not catalog_rows_match(expected, actual) and not issues:
        issues.append("published rows differ from the canonical sync mapping")
    return issues


def check_vercel(canonical_catalog: dict[str, Any]) -> None:
    deployed = _http_get_json(PRODUCTION_CATALOG_URL)
    issues = _catalogue_diff(canonical_catalog, deployed)
    if issues:
        raise IntegrationCheckError("Vercel production catalogue does not match GitHub: " + "; ".join(issues))
    print("PASS — Vercel production /data/software.json matches the canonical GitHub catalogue.")


def check_supabase(canonical_catalog: dict[str, Any]) -> None:
    base_url, public_key = load_public_supabase_config()
    query = urlencode({
        "select": ",".join(VERIFY_COLUMNS),
        "published": "eq.true",
        "order": "sort_order.asc",
    })
    # Fixed field selection and filters only; no input from a user/query string is interpolated.
    actual = _http_get_json(
        base_url + "/rest/v1/software_catalog?" + query,
        headers={"apikey": public_key, "Authorization": f"Bearer {public_key}"},
    )
    expected = [
        to_record(app, index, "")
        for index, app in enumerate(canonical_catalog["software"])
    ]
    issues = _supabase_diff(expected, actual)
    if issues:
        raise IntegrationCheckError("Supabase public mirror does not match GitHub: " + "; ".join(issues))
    print(f"PASS — Supabase read-only mirror matches {len(expected)} canonical GitHub catalogue records.")


def main() -> int:
    try:
        canonical = load_catalog(CATALOG_PATH)
    except ValueError as exc:
        print(f"FAIL — canonical GitHub catalogue is invalid: {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for name, check in (("Vercel", check_vercel), ("Supabase", check_supabase)):
        try:
            check(canonical)
        except IntegrationCheckError as exc:
            failures.append(f"{name}: {exc}")
            print(f"FAIL — {name}: {exc}", file=sys.stderr)

    if failures:
        print("Live integration audit failed. No writes or schema changes were attempted.", file=sys.stderr)
        return 1
    print("Live integration audit passed. All requests were read-only; no changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
