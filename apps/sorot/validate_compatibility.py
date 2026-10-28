#!/usr/bin/env python3
"""Validate Sorot per-distribution compatibility metadata against canonical release metadata."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

COMPATIBILITY_PATH = Path(__file__).resolve().with_name("compatibility.json")
RELEASE_INDEX_PATH = Path(__file__).resolve().parent / "releases" / "index.json"
VALID_STATUSES = {"supported", "testing", "unverified", "blocked", "planned"}
REQUIRED_SUPPORTED_EVIDENCE = {"install", "launch", "upgrade", "uninstall"}

class CompatibilityValidationError(ValueError):
    """Raised when compatibility metadata is invalid or contradictory."""

def validate_compatibility(compatibility: Any, release_index: Any, release_manifest: Any) -> dict[str, Any]:
    if not isinstance(compatibility, dict) or compatibility.get("schema_version") != 1:
        raise CompatibilityValidationError("compatibility metadata must use schema_version 1")
    if compatibility.get("product") != "Sorot":
        raise CompatibilityValidationError("product must be Sorot")
    version = compatibility.get("version")
    if not isinstance(version, str) or not version:
        raise CompatibilityValidationError("version must be a non-empty string")
    status = compatibility.get("release_status")
    if status not in {"testing", "released", "archived"}:
        raise CompatibilityValidationError("release_status is invalid")
    if not isinstance(release_index, dict) or not isinstance(release_index.get("versions"), list):
        raise CompatibilityValidationError("release index is missing versions")
    matches = [x for x in release_index["versions"] if isinstance(x, dict) and x.get("version") == version]
    if len(matches) != 1:
        raise CompatibilityValidationError(f"release index must contain exactly one entry for {version}")
    if matches[0].get("status") != status:
        raise CompatibilityValidationError("release_status differs from canonical release index")
    if not isinstance(release_manifest, dict) or release_manifest.get("version") != version:
        raise CompatibilityValidationError("release manifest version differs from compatibility metadata")
    if release_manifest.get("status") != status:
        raise CompatibilityValidationError("release_status differs from per-version release manifest")
    distributions = compatibility.get("distributions")
    if not isinstance(distributions, list) or not distributions:
        raise CompatibilityValidationError("distributions must be a non-empty list")
    seen: set[str] = set()
    for item in distributions:
        if not isinstance(item, dict):
            raise CompatibilityValidationError("each distribution entry must be an object")
        distro_id = item.get("id")
        if not isinstance(distro_id, str) or not distro_id.strip():
            raise CompatibilityValidationError("each distribution requires a non-empty id")
        if distro_id in seen:
            raise CompatibilityValidationError(f"duplicate distribution id: {distro_id}")
        seen.add(distro_id)
        if item.get("status") not in VALID_STATUSES:
            raise CompatibilityValidationError(f"{distro_id}: invalid compatibility status")
        if not isinstance(item.get("family"), str) or not item["family"]:
            raise CompatibilityValidationError(f"{distro_id}: family is required")
        if not isinstance(item.get("package_formats"), list):
            raise CompatibilityValidationError(f"{distro_id}: package_formats must be a list")
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            raise CompatibilityValidationError(f"{distro_id}: evidence must be a list")
        if item["status"] == "supported":
            passed = {e.get("kind") for e in evidence if isinstance(e, dict) and e.get("result") == "passed"}
            missing = sorted(REQUIRED_SUPPORTED_EVIDENCE - passed)
            if missing:
                raise CompatibilityValidationError(f"{distro_id}: supported status requires passed evidence for {missing}")
        limits = item.get("limitations")
        if not isinstance(limits, list) or not all(isinstance(x, str) for x in limits):
            raise CompatibilityValidationError(f"{distro_id}: limitations must be a list of strings")
    return {"product":"Sorot","version":version,"release_status":status,
            "distribution_count":len(distributions),
            "supported_count":sum(x["status"] == "supported" for x in distributions),
            "unverified_count":sum(x["status"] == "unverified" for x in distributions)}

def main() -> int:
    try:
        compatibility = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"))
        index = json.loads(RELEASE_INDEX_PATH.read_text(encoding="utf-8"))
        version = compatibility.get("version") if isinstance(compatibility, dict) else None
        if not isinstance(version, str):
            raise CompatibilityValidationError("compatibility version is missing")
        manifest_path = Path(__file__).resolve().parent / "releases" / version / "release.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = validate_compatibility(compatibility, index, manifest)
    except (OSError, json.JSONDecodeError, CompatibilityValidationError) as exc:
        print(f"Sorot compatibility validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {result['product']} {result['version']}: release_status={result['release_status']}, distributions={result['distribution_count']}, supported={result['supported_count']}, unverified={result['unverified_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
