#!/usr/bin/env python3
"""Find broken local href/src targets in the static HTML pages."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://site-check.invalid/"


class LinkParser(HTMLParser):
    def __init__(self, file_path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.file_path = file_path
        self.links: list[tuple[str, int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key not in ("href", "src") or not value:
                continue
            value = value.strip()
            if value and not value.startswith("#"):
                self.links.append((key, value, self.getpos()[0]))


def find_broken_links(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for page in sorted(root.rglob("*.html")):
        if any(part.startswith(".") for part in page.relative_to(root).parts):
            continue
        try:
            html = page.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{page.relative_to(root)}: HTML is not UTF-8.")
            continue
        parser = LinkParser(page)
        parser.feed(html)
        page_relative = page.relative_to(root).as_posix()
        base = urljoin(BASE_URL, page_relative)
        for _kind, value, line in parser.links:
            parsed = urlparse(value)
            if parsed.scheme or parsed.netloc or value.startswith("//"):
                continue
            target = urlparse(urljoin(base, value))
            path = target.path
            if not path or path == "/":
                local = root / "index.html"
            else:
                relative = path.lstrip("/")
                local = root / relative
                if path.endswith("/"):
                    local = local / "index.html"
            try:
                local.resolve().relative_to(root.resolve())
            except ValueError:
                errors.append(f"{page_relative}:{line}: path escapes website root: {value}")
                continue
            if not local.is_file():
                errors.append(f"{page_relative}:{line}: missing local target {value}")
    return errors


def main() -> int:
    errors = find_broken_links()
    if errors:
        print("Local link check FAILED:")
        for error in errors:
            print(" - " + error)
        return 1
    print("Local link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
