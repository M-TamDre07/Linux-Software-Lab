#!/usr/bin/env python3
"""Check local Markdown links in repository docs without contacting external hosts."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
FENCE_LINE = re.compile(r"^\\s*(`{3,}|~{3,})(.*)$")
INLINE_CODE = re.compile(r"`[^`]*`")
MARKDOWN_LINK = re.compile(r"(?<!!)\\[[^\\]]*\\]\\(([^)]+)\\)")


def _without_fenced_code(source: str) -> str:
    """Blank backtick and tilde fenced blocks while preserving line numbers."""
    output: list[str] = []
    fence_char: str | None = None
    fence_size = 0
    for line in source.splitlines(keepends=True):
        content = line.rstrip("\\r\\n")
        match = FENCE_LINE.match(content)
        if fence_char is None and match:
            marker = match.group(1)
            fence_char, fence_size = marker[0], len(marker)
            output.append("\\n" if line.endswith("\\n") else "")
            continue
        if fence_char is not None:
            if (
                match
                and match.group(1)[0] == fence_char
                and len(match.group(1)) >= fence_size
                and not match.group(2).strip()
            ):
                fence_char = None
                fence_size = 0
            output.append("\\n" if line.endswith("\\n") else "")
            continue
        output.append(line)
    return "".join(output)


def markdown_files(root: Path = ROOT) -> list[Path]:
    """Return repository Markdown files without following symlinks or generated trees."""
    found: list[Path] = []
    for path in root.rglob("*.md"):
        if path.is_symlink() or any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            found.append(path)
    return sorted(found)


def _link_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    else:
        value = value.split(None, 1)[0]
    return value.strip()


def check_markdown_file(path: Path, *, root: Path = ROOT) -> list[str]:
    """Return broken local file/directory link descriptions for one Markdown file."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path.relative_to(root)}: cannot read Markdown as UTF-8 ({exc})"]

    source = _without_fenced_code(source)
    source = INLINE_CODE.sub("", source)
    problems: list[str] = []
    for match in MARKDOWN_LINK.finditer(source):
        raw = match.group(1).strip()
        target = _link_target(raw)
        if not target:
            continue
        parsed = urlsplit(target)
        if parsed.scheme:
            if parsed.scheme.casefold() in {"http", "https", "mailto", "tel", "ftp"}:
                continue
            problems.append(f"{path.relative_to(root)}: unsafe link scheme in {target!r}")
            continue
        if parsed.netloc or target.startswith("#"):
            continue
        path_part = unquote(parsed.path)
        if not path_part:
            continue
        if "\\" in path_part or "\x00" in path_part:
            problems.append(f"{path.relative_to(root)}: unsafe local link target {target!r}")
            continue

        candidate = (path.parent / path_part).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            problems.append(f"{path.relative_to(root)}: local link escapes the repository: {target!r}")
            continue
        if not candidate.exists():
            line = source.count("\n", 0, match.start()) + 1
            problems.append(f"{path.relative_to(root)}:{line}: missing local target {target!r}")
    return problems


def check_all(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in markdown_files(root):
        errors.extend(check_markdown_file(path, root=root))
    return errors


def main() -> int:
    errors = check_all()
    if errors:
        print("Repository Markdown link check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(f"{len(errors)} broken or unsafe local Markdown link(s) found.", file=sys.stderr)
        return 1
    print(f"Markdown link check passed: {len(markdown_files())} files scanned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
