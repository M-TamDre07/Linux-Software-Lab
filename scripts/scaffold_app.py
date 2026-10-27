#!/usr/bin/env python3
"""Generate a safe, technology-neutral application scaffold for Linux Software Lab."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = ROOT / "templates" / "application"
DEFAULT_APPS_DIR = ROOT / "apps"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOKEN_PATTERN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
MAX_SLUG_LENGTH = 64
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 320


class ScaffoldError(ValueError):
    """Raised when a scaffold request is invalid or cannot be installed safely."""


def _single_line(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ScaffoldError(f"{field} harus berupa teks.")
    value = value.strip()
    if not value:
        raise ScaffoldError(f"{field} wajib diisi.")
    if len(value) > maximum:
        raise ScaffoldError(f"{field} terlalu panjang (maksimum {maximum} karakter).")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ScaffoldError(f"{field} tidak boleh mengandung karakter kontrol atau baris baru.")
    return value


def validate_slug(slug: str) -> str:
    """Allow stable path-safe IDs only; do not try to sanitise an invalid path."""
    if not isinstance(slug, str) or len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(slug):
        raise ScaffoldError(
            "Slug tidak valid. Gunakan huruf kecil, angka, dan tanda hubung tunggal, "
            "misalnya 'sample-tool'."
        )
    return slug


def _markdown_text(value: str) -> str:
    """Render caller-provided label/description as literal Markdown text."""
    special = r"\\`*_{}[]()#+-.!|>"
    return "".join("\\" + character if character in special else character for character in value)


def _replace_tokens(source: str, replacements: dict[str, str], relative_path: Path) -> str:
    for key, value in replacements.items():
        source = source.replace("{{" + key + "}}", value)
    remaining = TOKEN_PATTERN.findall(source)
    if remaining:
        tokens = ", ".join(sorted(set(remaining)))
        raise ScaffoldError(f"Template {relative_path} memiliki placeholder yang belum dikenal: {tokens}.")
    return source


def scaffold_application(
    slug: str,
    name: str,
    description: str,
    *,
    apps_dir: Path | None = None,
    template_dir: Path | None = None,
    today: date | None = None,
) -> Path:
    """Create a new scaffold directory without overwriting data or touching the catalogue."""
    slug = validate_slug(slug)
    name = _single_line(name, "Nama aplikasi", MAX_NAME_LENGTH)
    description = _single_line(description, "Deskripsi aplikasi", MAX_DESCRIPTION_LENGTH)
    target_apps = (apps_dir or DEFAULT_APPS_DIR).expanduser().resolve()
    source_template = (template_dir or DEFAULT_TEMPLATE_DIR).expanduser().resolve()

    if not target_apps.is_dir():
        raise ScaffoldError(f"Folder tujuan aplikasi tidak ditemukan: {target_apps}")
    if not source_template.is_dir():
        raise ScaffoldError(f"Template aplikasi tidak ditemukan: {source_template}")

    target = target_apps / slug
    if target.parent.resolve() != target_apps or target.exists() or target.is_symlink():
        raise ScaffoldError(f"Folder apps/{slug} sudah ada atau bukan tujuan yang aman. Tidak ada file yang diubah.")

    created = today or datetime.now(timezone.utc).date()
    replacements = {
        "APP_SLUG": slug,
        "APP_NAME": _markdown_text(name),
        "APP_DESCRIPTION": _markdown_text(description),
        "APP_NAME_JSON": json.dumps(name, ensure_ascii=False)[1:-1],
        "APP_DESCRIPTION_JSON": json.dumps(description, ensure_ascii=False)[1:-1],
        "APP_CREATED_DATE": created.isoformat(),
    }

    # Keep the temporary workspace private; publish only the completed payload by rename.
    staging_root = Path(tempfile.mkdtemp(prefix=".lsl-scaffold-", dir=target_apps))
    staging = staging_root / "payload"
    try:
        shutil.copytree(source_template, staging, symlinks=True)
        for path in staging.rglob("*"):
            if path.is_symlink():
                raise ScaffoldError(f"Template tidak boleh berisi symlink: {path.relative_to(staging)}")
            if not path.is_file():
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ScaffoldError(f"Template harus berupa file teks UTF-8: {path.relative_to(staging)}") from exc
            transformed = _replace_tokens(source, replacements, path.relative_to(staging))
            path.write_text(transformed, encoding="utf-8", newline="\\n")

        if target.exists() or target.is_symlink():
            raise ScaffoldError(f"Folder apps/{slug} dibuat oleh proses lain. Tidak ada file yang ditimpa.")
        staging.rename(target)
        return target
    except ScaffoldError:
        raise
    except OSError as exc:
        raise ScaffoldError(f"Gagal membuat scaffold aplikasi: {exc}") from exc
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Buat scaffold aplikasi standar tanpa mengubah katalog atau merilis paket."
    )
    parser.add_argument("--slug", required=True, help="ID direktori yang stabil, misalnya sample-tool.")
    parser.add_argument("--name", required=True, help="Nama tampilan aplikasi.")
    parser.add_argument("--description", required=True, help="Deskripsi singkat tujuan aplikasi.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        destination = scaffold_application(args.slug, args.name, args.description)
    except ScaffoldError as exc:
        print(f"Scaffold gagal: {exc}", file=sys.stderr)
        return 2
    print(f"Scaffold dibuat: {destination.relative_to(ROOT)}")
    print("Status: planned. Ini kerangka dokumentasi, bukan aplikasi siap jalan atau paket rilis.")
    print("Langkah berikutnya: pilih lisensi/runtime, isi arsitektur, implementasikan source dan tes, lalu buka pull request.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
