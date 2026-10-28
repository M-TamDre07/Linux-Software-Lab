#!/usr/bin/env python3
"""Persist a validated catalogue health report using trusted CI credentials."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPORT = Path("/tmp/liso-catalog-health.json")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SUPABASE_URL = "https://ttofugaqwthmvhvntdlc.supabase.co"


class ApiError(RuntimeError):
    pass


def api_request(base_url: str, secret: str, path: str, method: str = "GET",
                payload: object | None = None, prefer: str | None = None):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = Request(base_url.rstrip("/") + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except (HTTPError, URLError, TimeoutError) as exc:
        # Never print request headers, credentials, or raw server responses.
        status = getattr(exc, "code", "network")
        raise ApiError(f"Supabase REST request failed ({status}) for {path.split('?')[0]}.") from None


def main() -> int:
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    secret = os.environ.get("SUPABASE_SECRET_KEY", "")
    commit_sha = os.environ.get("GITHUB_SHA", "")
    if base_url.rstrip("/") != EXPECTED_SUPABASE_URL:
        print("Invalid SUPABASE_URL; report persistence is restricted to the configured LISO LAB project.", file=sys.stderr)
        return 2
    if not secret:
        print("SUPABASE_SECRET_KEY is not configured; report persistence skipped.")
        return 0
    if not SHA_RE.fullmatch(commit_sha):
        print("GITHUB_SHA must be a full 40-character commit SHA.", file=sys.stderr)
        return 2

    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        if report.get("algorithm") != "lsl-catalog-health-v1":
            raise ValueError("Unexpected report algorithm version.")
        if not isinstance(report.get("entries"), list) or not report["entries"]:
            raise ValueError("Report entries are missing.")
        if not isinstance(report.get("findings"), list):
            raise ValueError("Report findings are invalid.")
        summary = {
            "source_commit_sha": commit_sha,
            "algorithm_version": report["algorithm"],
            "entry_count": int(report["entry_count"]),
            "overall_score": int(report["overall_score"]),
            "recommendation": report["recommendation"],
            "finding_count": int(report["finding_count"]),
            "severity_counts": report["severity_counts"],
        }
        created = api_request(
            base_url, secret, "/rest/v1/catalog_quality_runs?select=id",
            "POST", summary, "return=representation",
        )
        if not isinstance(created, list) or len(created) != 1 or not isinstance(created[0].get("id"), str):
            raise ApiError("Supabase did not return a report run identifier.")
        run_id = created[0]["id"]
        findings = [{
            "run_id": run_id,
            "software_id": finding.get("software_id"),
            "rule_code": finding["rule"],
            "severity": finding["severity"],
            "deduction": int(finding["deduction"]),
            "message": finding["message"],
        } for finding in report["findings"]]
        try:
            if findings:
                api_request(base_url, secret, "/rest/v1/catalog_quality_findings",
                            "POST", findings, "return=minimal")
        except ApiError:
            # Avoid leaving a misleading summary if the child insert failed.
            api_request(base_url, secret, "/rest/v1/catalog_quality_runs?id=eq." + quote(run_id, safe=""),
                        "DELETE", None, "return=minimal")
            raise
        print(f"Persisted catalogue health report for commit {commit_sha[:12]} ({len(findings)} findings).")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, ApiError) as exc:
        print(f"Catalogue report persistence failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
