#!/usr/bin/env python3
"""Deterministic, explainable catalogue health scoring (no external AI/API)."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "public" / "data" / "software.json"
RULES = {
    "missing_keywords": (8, "warning"),
    "missing_features": (8, "warning"),
    "testing_stale": (12, "warning"),
    "planned_has_release_url": (25, "error"),
    "released_missing_release_url": (30, "error"),
    "metadata_stale": (5, "info"),
}


def _age_days(value: Any, today: date) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return (today - date.fromisoformat(value)).days
    except ValueError:
        return None


def analyze_catalog(data: Any, today: date | None = None) -> dict[str, Any]:
    """Return an explainable quality report; this never changes source data."""
    today = today or date.today()
    if not isinstance(data, dict) or not isinstance(data.get("software"), list):
        raise ValueError("Catalog must be an object with a software array.")
    apps = data["software"]
    if not apps:
        raise ValueError("Catalog must contain at least one software entry.")

    findings: list[dict[str, Any]] = []
    per_app: list[dict[str, Any]] = []
    for app in apps:
        if not isinstance(app, dict):
            findings.append({"software_id": None, "rule": "invalid_entry", "severity": "error",
                             "deduction": 30, "message": "Entry is not a JSON object."})
            continue
        app_id = app.get("id") if isinstance(app.get("id"), str) else "unknown"
        local: list[dict[str, Any]] = []

        def add(rule: str, message: str) -> None:
            deduction, severity = RULES[rule]
            local.append({"software_id": app_id, "rule": rule, "severity": severity,
                          "deduction": deduction, "message": message})

        if not app.get("keywords"):
            add("missing_keywords", "Add search keywords to improve catalogue discovery.")
        if not app.get("features"):
            add("missing_features", "Document at least one user-facing feature.")
        age = _age_days(app.get("updatedAt"), today)
        status = app.get("status")
        if status == "testing" and age is not None and age > 30:
            add("testing_stale", f"Testing entry has not been reviewed for {age} days.")
        if status == "planned" and app.get("releaseUrl"):
            add("planned_has_release_url", "Planned software must not expose a release URL.")
        if status == "released" and not app.get("releaseUrl"):
            add("released_missing_release_url", "Released software needs a verified release URL.")
        if age is not None and age > 90:
            add("metadata_stale", f"Metadata is {age} days old; review whether it is still current.")

        # Diminishing returns: repeated findings cannot produce negative scores.
        score = max(0, 100 - sum(item["deduction"] for item in local))
        if score >= 90:
            recommendation = "ready"
        elif score >= 70:
            recommendation = "review"
        else:
            recommendation = "needs_attention"
        per_app.append({"software_id": app_id, "score": score, "recommendation": recommendation,
                        "finding_count": len(local)})
        findings.extend(local)

    average = round(sum(item["score"] for item in per_app) / len(per_app))
    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    return {
        "algorithm": "lsl-catalog-health-v1",
        "generated_on": today.isoformat(),
        "overall_score": average,
        "recommendation": "needs_attention" if errors else ("review" if warnings else "ready"),
        "entry_count": len(apps),
        "finding_count": len(findings),
        "severity_counts": {
            "error": errors,
            "warning": warnings,
            "info": sum(item["severity"] == "info" for item in findings),
        },
        "entries": per_app,
        "findings": findings,
        "note": "Heuristic rules only; recommendations require human review and never publish or edit records.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()
    try:
        data = json.loads(args.catalog.read_text(encoding="utf-8"))
        report = analyze_catalog(data)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Catalogue analysis failed: {exc}")
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
