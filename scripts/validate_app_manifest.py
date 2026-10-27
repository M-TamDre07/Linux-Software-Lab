#!/usr/bin/env python3
"""Validate the standard app manifest without third-party dependencies."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "templates" / "application" / "application.json"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DETAIL_ROUTE = re.compile(r"^/software/[a-z0-9-]+\.html$")
RELEASE_FORMATS = {"deb", "rpm", "pkg.tar.zst", "flatpak", "flatpakref", "AppImage", "tar.gz", "zip"}
LIFECYCLES = {"planned", "testing", "released", "archived"}
TOP_LEVEL_FIELDS = {
    "$schema", "schema_version", "id", "slug", "name", "description", "lifecycle",
    "runtime", "supported_os", "supported_architectures", "entrypoints", "distribution",
    "integrity", "integration",
}


def validate_manifest(data: Any, *, base_dir: Path | None = None) -> list[str]:
    """Return actionable schema and cross-field errors; never mutate the manifest."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Akar manifest harus berupa objek JSON."]

    unknown = set(data) - TOP_LEVEL_FIELDS
    missing = TOP_LEVEL_FIELDS - set(data)
    if unknown:
        errors.append("Field tidak dikenal: " + ", ".join(sorted(unknown)) + ".")
    if missing:
        errors.append("Field wajib belum ada: " + ", ".join(sorted(missing)) + ".")

    if data.get("$schema") != "./application.schema.json":
        errors.append("Field '$schema' harus menunjuk ke ./application.schema.json.")
    if type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        errors.append("'schema_version' harus berupa integer 1.")

    identifier = data.get("id")
    slug = data.get("slug")
    for field, value in (("id", identifier), ("slug", slug)):
        if not isinstance(value, str) or not SLUG.fullmatch(value) or len(value) > 64:
            errors.append(f"'{field}' harus berupa slug huruf kecil, angka, dan tanda hubung.")
    if isinstance(identifier, str) and isinstance(slug, str) and identifier != slug:
        errors.append("'id' dan 'slug' harus sama agar identitas lintas platform konsisten.")

    for field, maximum in (("name", 100), ("description", 320), ("runtime", 100)):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            errors.append(f"'{field}' harus berupa teks dengan panjang 1–{maximum} karakter.")
        elif any(ord(character) < 32 or ord(character) == 127 for character in value):
            errors.append(f"'{field}' tidak boleh mengandung karakter kontrol.")

    lifecycle = data.get("lifecycle")
    if not isinstance(lifecycle, str) or lifecycle not in LIFECYCLES:
        errors.append("'lifecycle' harus planned, testing, released, atau archived.")

    for field in ("supported_os", "supported_architectures"):
        value = data.get(field)
        invalid_list = not isinstance(value, list)
        if isinstance(value, list):
            invalid_list = any(not isinstance(item, str) or not item.strip() for item in value)
            if not invalid_list:
                invalid_list = len(value) != len(set(value))
        if invalid_list:
            errors.append(f"'{field}' harus berupa daftar teks unik tanpa nilai kosong.")

    entrypoints = data.get("entrypoints")
    if not isinstance(entrypoints, dict) or set(entrypoints) != {"gui", "cli"}:
        errors.append("'entrypoints' harus berisi hanya field gui dan cli.")
    else:
        for field in ("gui", "cli"):
            value = entrypoints[field]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                errors.append(f"'entrypoints.{field}' harus berupa teks atau null.")

    distribution = data.get("distribution")
    release_manifest: str | None = None
    enabled_formats: list[str] = []
    if not isinstance(distribution, dict) or set(distribution) != {"enabled_formats", "release_manifest"}:
        errors.append("'distribution' harus berisi hanya enabled_formats dan release_manifest.")
    else:
        enabled = distribution["enabled_formats"]
        if not isinstance(enabled, list) or any(
            not isinstance(item, str) or item not in RELEASE_FORMATS for item in enabled
        ):
            errors.append("'distribution.enabled_formats' berisi format tidak dikenal.")
        elif len(enabled) != len(set(enabled)):
            errors.append("'distribution.enabled_formats' tidak boleh berisi format duplikat.")
        else:
            enabled_formats = enabled

        release_manifest = distribution["release_manifest"]
        if release_manifest is not None:
            if not isinstance(release_manifest, str) or not release_manifest.strip():
                errors.append("'distribution.release_manifest' harus berupa path relatif atau null.")
                release_manifest = None
            else:
                manifest_path = PurePosixPath(release_manifest)
                if (
                    manifest_path.is_absolute()
                    or ".." in manifest_path.parts
                    or not manifest_path.parts
                    or manifest_path.parts[0] != "releases"
                    or manifest_path.name != "release.json"
                ):
                    errors.append("'distribution.release_manifest' harus berada di releases/<versi>/release.json.")

    integrity = data.get("integrity")
    if not isinstance(integrity, dict) or set(integrity) != {"sha256_checksums", "publisher_signature"}:
        errors.append("'integrity' harus berisi hanya sha256_checksums dan publisher_signature.")
    else:
        checksum_state = integrity["sha256_checksums"]
        signature_state = integrity["publisher_signature"]
        if not isinstance(checksum_state, str) or checksum_state not in {"not-published", "published"}:
            errors.append("'integrity.sha256_checksums' harus not-published atau published.")
        if not isinstance(signature_state, str) or signature_state not in {"not-implemented", "implemented"}:
            errors.append("'integrity.publisher_signature' harus not-implemented atau implemented.")

    integration = data.get("integration")
    if not isinstance(integration, dict) or set(integration) != {"website_page", "launcher_allowlist", "catalogue_record"}:
        errors.append("'integration' harus berisi hanya website_page, launcher_allowlist, dan catalogue_record.")
    else:
        route = integration["website_page"]
        if not isinstance(route, str) or not DETAIL_ROUTE.fullmatch(route):
            errors.append("'integration.website_page' harus berbentuk /software/<slug>.html.")
        elif isinstance(slug, str) and route != f"/software/{slug}.html":
            errors.append("'integration.website_page' harus memakai slug aplikasi yang sama.")
        for field in ("launcher_allowlist", "catalogue_record"):
            value = integration[field]
            if not isinstance(value, str) or value not in {"not-registered", "registered"}:
                errors.append(f"'integration.{field}' harus not-registered atau registered.")

    if lifecycle == "planned":
        if enabled_formats:
            errors.append("Aplikasi planned tidak boleh menyatakan format rilis tersedia.")
        if release_manifest is not None:
            errors.append("Aplikasi planned tidak boleh menunjuk manifest rilis.")
        if isinstance(integrity, dict) and (
            integrity.get("sha256_checksums") != "not-published"
            or integrity.get("publisher_signature") != "not-implemented"
        ):
            errors.append("Aplikasi planned harus menyatakan integritas rilis belum dipublikasikan.")

    if lifecycle == "released":
        if not enabled_formats:
            errors.append("Aplikasi released wajib mencantumkan format rilis yang benar-benar tersedia.")
        if release_manifest is None:
            errors.append("Aplikasi released wajib menunjuk manifest rilis yang nyata.")
        elif base_dir is not None:
            root = base_dir.resolve()
            candidate = (root / Path(*PurePosixPath(release_manifest).parts)).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append("Manifest rilis menyelesaikan path di luar folder aplikasi.")
            else:
                if not candidate.is_file():
                    errors.append("Manifest rilis yang dirujuk tidak ditemukan sebagai file.")
        if isinstance(integrity, dict) and integrity.get("sha256_checksums") != "published":
            errors.append("Aplikasi released harus menyatakan bahwa checksum rilis tersedia.")

    return errors


def validate_manifest_file(path: Path, *, template: bool = False) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"Manifest tidak dapat dibaca sebagai UTF-8: {exc}"]
    if template:
        # Use inert sample values only in memory; never rewrite the committed template.
        source = source.replace('"{{APP_SLUG}}"', '"template-app"')
        source = source.replace('{{APP_NAME_JSON}}', json.dumps("Template App")[1:-1])
        source = source.replace(
            '{{APP_DESCRIPTION_JSON}}',
            json.dumps("Synthetic description used to validate the scaffold contract.")[1:-1],
        )
        source = source.replace("/software/{{APP_SLUG}}.html", "/software/template-app.html")
    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        return [f"JSON tidak valid di baris {exc.lineno}, kolom {exc.colno}."]
    return validate_manifest(data, base_dir=None if template else path.parent)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Periksa kontrak application.json tanpa mengubah file atau mengakses layanan online."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        help="Path application.json; jika dihilangkan, validasi template resmi dengan fixture inert.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = args.manifest or DEFAULT_MANIFEST
    is_template = args.manifest is None
    errors = validate_manifest_file(target, template=is_template)
    if errors:
        label = "Template manifest" if is_template else "Manifest"
        print(f"{label} tidak valid: {target}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    label = "Template manifest valid" if is_template else "Manifest valid"
    print(f"{label}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
