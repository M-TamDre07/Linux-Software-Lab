#!/usr/bin/env python3
"""Regenerate distribution metadata and Sorot catalogue labels from the canonical release index."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE_INDEX_PATH = ROOT / "apps" / "sorot" / "releases" / "index.json"
PUBLIC_INDEX_PATH = ROOT / "public" / "data" / "distribution-index.json"
BUNDLED_INDEX_PATH = ROOT / "apps" / "software-center" / "lsl_center" / "data" / "distribution-index.json"
PUBLIC_CATALOG_PATH = ROOT / "public" / "data" / "software.json"
BUNDLED_CATALOG_PATH = ROOT / "apps" / "software-center" / "lsl_center" / "data" / "catalog.json"
RAW_ROOT = "https://raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main"
ALLOWED_STATUSES = {"testing", "released", "archived"}
ALLOWED_CHANNELS = {"alpha", "beta", "rc", "stable", "development"}
CHANNEL_LABELS = {
    "alpha": "Alpha",
    "beta": "Beta",
    "rc": "RC",
    "stable": "",
    "development": "Development",
}


class IndexSyncError(ValueError):
    """Source release metadata is missing or inconsistent."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndexSyncError(f"Cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise IndexSyncError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def _format_version_label(entry: dict[str, Any]) -> str:
    version = entry.get("version")
    channel = entry.get("channel")
    if not isinstance(version, str) or channel not in CHANNEL_LABELS:
        raise IndexSyncError("Latest Sorot version must contain a valid version and channel")
    return f"{version} {CHANNEL_LABELS[channel]}".strip()


def _build_catalog_with_current_sorot_version(path: Path, version_label: str) -> dict[str, Any]:
    data = _load(path)
    software = data.get("software")
    if not isinstance(software, list):
        raise IndexSyncError(f"{path.relative_to(ROOT)} must contain a software array")
    matches = [
        item for item in software
        if isinstance(item, dict) and item.get("id") == "sorot"
    ]
    if len(matches) != 1:
        raise IndexSyncError(
            f"{path.relative_to(ROOT)} must contain exactly one Sorot catalogue entry"
        )
    # The canonical version list lives in apps/sorot/releases/index.json.
    # This field is a generated display/search label, never a second source of truth.
    matches[0]["version"] = version_label
    return data


def _build_public_index() -> dict[str, Any]:
    source = _load(RELEASE_INDEX_PATH)
    if source.get("schema_version") != 1 or source.get("product") != "Sorot":
        raise IndexSyncError("Sorot releases/index.json has an unsupported schema/product")
    entries = source.get("versions")
    if not isinstance(entries, list) or not entries:
        raise IndexSyncError("Sorot release index must contain a non-empty versions list")

    version_refs: list[dict[str, str]] = []
    seen: set[str] = set()
    releases_root = RELEASE_INDEX_PATH.parent
    for entry in entries:
        if not isinstance(entry, dict):
            raise IndexSyncError("Each versions entry must be an object")
        version = entry.get("version")
        if not isinstance(version, str) or version in seen:
            raise IndexSyncError(f"Invalid or duplicate version: {version!r}")
        seen.add(version)
        manifest_path = releases_root / version / "release.json"
        manifest = _load(manifest_path)
        if manifest.get("schema_version") != 1 or manifest.get("product") != "Sorot":
            raise IndexSyncError(f"{version}: invalid manifest schema/product")
        if manifest.get("version") != version:
            raise IndexSyncError(f"{version}: manifest version does not match index")
        if manifest.get("status") not in ALLOWED_STATUSES or manifest.get("channel") not in ALLOWED_CHANNELS:
            raise IndexSyncError(f"{version}: invalid status/channel")
        if manifest.get("status") != entry.get("status") or manifest.get("channel") != entry.get("channel"):
            raise IndexSyncError(f"{version}: status/channel differs between index and manifest")
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise IndexSyncError(f"{version}: manifest must contain artifacts")
        formats = {item.get("format") for item in artifacts if isinstance(item, dict)}
        if formats != set(entry.get("formats", [])):
            raise IndexSyncError(f"{version}: formats differ between index and manifest")
        version_refs.append({
            "version": version,
            "url": f"{RAW_ROOT}/apps/sorot/releases/{version}/release.json",
        })

    dirs = sorted(
        item.name for item in releases_root.iterdir()
        if item.is_dir() and item.name[:1].isdigit()
    )
    if set(dirs) != seen:
        missing = sorted(set(dirs) - seen)
        unknown = sorted(seen - set(dirs))
        raise IndexSyncError(f"Version folders and index differ; unindexed={missing}, missing_folders={unknown}")

    generated = _load(PUBLIC_INDEX_PATH)
    if generated.get("schema_version") != 1:
        raise IndexSyncError("Public distribution index has an unsupported schema")
    products = generated.get("products")
    distributions = generated.get("distributions")
    if not isinstance(products, list) or not isinstance(distributions, list):
        raise IndexSyncError("Public distribution index needs products and distributions arrays")
    sorot = next((item for item in products if isinstance(item, dict) and item.get("id") == "sorot"), None)
    if sorot is None:
        raise IndexSyncError("Public distribution index has no Sorot entry")
    sorot["manifests"] = version_refs

    distro_ids_by_label = {
        str(item.get("label", "")).casefold(): item.get("id")
        for item in distributions if isinstance(item, dict)
    }
    planned: list[dict[str, str]] = []
    targets = source.get("planned_targets", [])
    if not isinstance(targets, list):
        raise IndexSyncError("planned_targets must be an array")
    for target in targets:
        if not isinstance(target, dict) or target.get("status") != "planned":
            raise IndexSyncError("Each planned target must be an object with status=planned")
        version = target.get("version")
        label = target.get("distribution")
        note = target.get("note")
        if not isinstance(version, str) or not isinstance(label, str) or not isinstance(note, str) or not note.strip():
            raise IndexSyncError("Planned target needs version, distribution, and non-empty note")
        distro_id = target.get("distribution_id") or distro_ids_by_label.get(label.casefold())
        if distro_id not in {item.get("id") for item in distributions if isinstance(item, dict)}:
            raise IndexSyncError(f"Planned target points to unknown distribution: {label}")
        planned.append({
            "distribution_id": str(distro_id),
            "version": version,
            "status": "planned",
            "note": note,
        })
    sorot["planned_targets"] = planned

    latest = entries[-1]
    latest_label = _format_version_label(latest)
    debian = next((item for item in distributions if item.get("id") == "debian-family"), None)
    if debian is not None and "deb" in set(latest.get("formats", [])):
        debian["note"] = (
            f"Sorot {latest_label} ({latest['status']}) memiliki paket .deb. "
            "Lihat laporan versi untuk cakupan uji; ini bukan jaminan instalasi bersih pada semua turunan Debian."
        )
    arch_target = next((item for item in planned if item["distribution_id"] == "arch"), None)
    arch = next((item for item in distributions if item.get("id") == "arch"), None)
    if arch is not None and arch_target is not None:
        arch["note"] = arch_target["note"] + " Target ini belum menjadi unduhan."

    updated_at = source.get("updated_at")
    if isinstance(updated_at, str) and updated_at:
        generated["updated_at"] = updated_at
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if checked-in generated metadata is stale")
    parser.add_argument("--write", action="store_true", help="write all generated distribution metadata")
    args = parser.parse_args()
    if args.check and args.write:
        parser.error("choose either --check or --write")
    try:
        expected_index = json.dumps(_build_public_index(), ensure_ascii=False, indent=2) + "\n"
        release_source = _load(RELEASE_INDEX_PATH)
        latest = release_source["versions"][-1]
        version_label = _format_version_label(latest)
        expected_files = {
            PUBLIC_INDEX_PATH: expected_index,
            BUNDLED_INDEX_PATH: expected_index,
            PUBLIC_CATALOG_PATH: json.dumps(
                _build_catalog_with_current_sorot_version(PUBLIC_CATALOG_PATH, version_label),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            BUNDLED_CATALOG_PATH: json.dumps(
                _build_catalog_with_current_sorot_version(BUNDLED_CATALOG_PATH, version_label),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
        }
    except (IndexSyncError, OSError, KeyError, IndexError, TypeError) as exc:
        print(f"Distribution index sync failed: {exc}", file=sys.stderr)
        return 1
    if args.write:
        for path, content in expected_files.items():
            path.write_text(content, encoding="utf-8")
        print(
            "Generated website/launcher distribution indexes and Sorot display-version labels "
            "from apps/sorot/releases/index.json."
        )
        return 0
    for path, expected in expected_files.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            print(f"{path.relative_to(ROOT)} is stale; run python scripts/sync_distribution_index.py --write.", file=sys.stderr)
            return 1
    print(
        "Website and Software Center distribution indexes/catalogue version labels "
        "match the Sorot release index."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
