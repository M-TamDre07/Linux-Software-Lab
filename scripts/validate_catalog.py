#!/usr/bin/env python3
"""Validate catalogue metadata and local website links using the standard library."""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "data" / "software.json"
SCHEMA = PUBLIC / "data" / "catalog.schema.json"
ALLOWED_STATUSES = {"testing", "planned", "released"}
REQUIRED = (
    "id", "name", "summary", "category", "status", "platforms", "tags",
    "detailUrl", "sourceUrl", "releaseUrl", "iconImage", "previewImage", "previewAlt",
)


class LocalLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and key.lower() in {"href", "src", "poster", "action"}:
                self.links.append((key.lower(), value.strip()))


def public_file_for_url(raw_url: str, base_file: Path | None = None) -> Path | None:
    parsed = urlsplit(raw_url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if path.startswith("/"):
        destination = (PUBLIC / path.lstrip("/")).resolve()
    elif base_file is not None:
        destination = (base_file.parent / path).resolve()
    else:
        destination = (PUBLIC / path).resolve()
    try:
        destination.relative_to(PUBLIC.resolve())
    except ValueError:
        raise ValueError(f"path keluar dari public/: {raw_url}") from None
    if path.endswith("/") or destination == PUBLIC.resolve():
        destination = destination / "index.html"
    return destination


def validate_catalog() -> list[str]:
    errors: list[str] = []
    if not CATALOG.is_file():
        return ["public/data/software.json tidak ditemukan"]
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"software.json bukan JSON valid: {exc}"]
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"catalog.schema.json bukan JSON valid: {exc}"]

    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        errors.append("schemaVersion harus bernilai 1")
    if not isinstance(data, dict) or not isinstance(data.get("software"), list):
        return errors + ["software harus berupa array"]
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("catalog.schema.json harus menggunakan JSON Schema 2020-12")

    ids: set[str] = set()
    names: set[str] = set()
    for index, item in enumerate(data["software"], start=1):
        label = f"software[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} harus berupa object")
            continue
        missing = [key for key in REQUIRED if key not in item]
        if missing:
            errors.append(f"{label} kehilangan field: {', '.join(missing)}")
            continue

        app_id = item["id"]
        name = item["name"]
        if not isinstance(app_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app_id):
            errors.append(f"{label}.id harus berupa slug huruf kecil dan tanda hubung")
        elif app_id in ids:
            errors.append(f"ID duplikat: {app_id}")
        else:
            ids.add(app_id)

        if not isinstance(name, str) or not name.strip():
            errors.append(f"{label}.name tidak boleh kosong")
        elif name.casefold() in names:
            errors.append(f"Nama software duplikat: {name}")
        else:
            names.add(name.casefold())

        for field in ("summary", "category", "previewAlt"):
            if not isinstance(item[field], str) or not item[field].strip():
                errors.append(f"{label}.{field} tidak boleh kosong")
        if not isinstance(item["status"], str) or item["status"] not in ALLOWED_STATUSES:
            errors.append(f"{label}.status harus salah satu dari {sorted(ALLOWED_STATUSES)}")
        if item["status"] == "released" and not item["releaseUrl"]:
            errors.append(f"{label} berstatus released tetapi releaseUrl kosong")

        for field in ("platforms", "tags", "keywords", "features"):
            if field in item and (
                not isinstance(item[field], list) or not all(isinstance(v, str) for v in item[field])
            ):
                errors.append(f"{label}.{field} harus berupa array string")

        for field in ("detailUrl", "iconImage", "previewImage"):
            value = item[field]
            if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
                errors.append(f"{label}.{field} harus berupa path lokal absolut")
                continue
            if field == "detailUrl" and not re.fullmatch(r"/software/[a-z0-9-]+\.html", value):
                errors.append(f"{label}.detailUrl harus mengarah ke halaman detail lokal")
                continue
            if field != "detailUrl" and not re.fullmatch(r"/assets/images/[a-z0-9-]+\.svg", value):
                errors.append(f"{label}.{field} harus mengarah ke aset SVG lokal")
                continue
            try:
                target = public_file_for_url(value)
                if target is None or not target.is_file():
                    errors.append(f"{label}.{field} tidak menunjuk ke berkas: {value}")
            except ValueError as exc:
                errors.append(f"{label}.{field}: {exc}")

        for field in ("sourceUrl", "releaseUrl"):
            value = item[field]
            if not isinstance(value, str):
                errors.append(f"{label}.{field} harus berupa string")
            elif value:
                try:
                    parsed = urlsplit(value)
                    if parsed.scheme != "https" or not parsed.netloc:
                        errors.append(f"{label}.{field} hanya boleh berupa tautan HTTPS atau string kosong")
                except ValueError:
                    errors.append(f"{label}.{field} bukan URL HTTPS yang valid")

    return errors


def validate_html_links() -> tuple[list[str], int]:
    errors: list[str] = []
    pages = sorted(PUBLIC.rglob("*.html"))
    for page in pages:
        try:
            parser = LocalLinkParser()
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{page.relative_to(ROOT)} tidak dapat dibaca: {exc}")
            continue
        for kind, value in parser.links:
            parsed = urlsplit(value)
            if parsed.scheme in {"mailto", "tel", "data"} or value.startswith("#"):
                continue
            if parsed.scheme and parsed.scheme not in {"http", "https"}:
                errors.append(f"{page.relative_to(ROOT)} memiliki skema URL tidak diizinkan: {value}")
                continue
            if parsed.netloc:
                continue
            try:
                target = public_file_for_url(value, base_file=page)
                if target is not None and not target.is_file():
                    errors.append(f"{page.relative_to(ROOT)}: {kind} lokal tidak ditemukan: {value}")
            except ValueError as exc:
                errors.append(f"{page.relative_to(ROOT)}: {exc}")
    return errors, len(pages)


def main() -> int:
    errors = validate_catalog()
    html_errors, page_count = validate_html_links()
    errors.extend(html_errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} issue(s).", file=sys.stderr)
        return 1
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    print(f"Catalog valid: {len(data['software'])} software record(s), {page_count} HTML page(s), local links and assets present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
