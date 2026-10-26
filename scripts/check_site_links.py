#!/usr/bin/env python3
"""Validate static HTML targets, markup policy, canonical URLs, robots.txt, and sitemap coverage."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "public"
BASE_URL = "https://site-check.invalid/"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, int, str]] = []
        self.ids: list[tuple[str, int]] = []
        self.policy_violations: list[tuple[int, str]] = []
        self._inline_script = False
        self._script_type = ""
        self._script_line = 0
        self._script_data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs}
        line = self.getpos()[0]
        for key, value in attrs:
            lowered = key.lower()
            if lowered == "id" and value:
                self.ids.append((value, line))
            if lowered.startswith("on"):
                self.policy_violations.append((line, f"inline event handler '{key}' violates the website script policy"))
            if lowered in ("href", "src") and value:
                value = value.strip()
                if value and not value.startswith("#"):
                    self.links.append((lowered, line, value))
        if tag.lower() == "script":
            self._inline_script = not bool(attributes.get("src"))
            self._script_type = (attributes.get("type") or "").split(";", 1)[0].strip().casefold()
            self._script_line = line
            self._script_data = []
            # JSON-LD is a non-executable data block, not inline JavaScript.
            if self._inline_script and self._script_type != "application/ld+json":
                self.policy_violations.append((line, "inline script violates script-src 'self' policy"))

    def handle_data(self, data: str) -> None:
        if self._inline_script and self._script_type == "application/ld+json":
            self._script_data.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            if self._inline_script and self._script_type == "application/ld+json":
                try:
                    json.loads("".join(self._script_data))
                except json.JSONDecodeError:
                    self.policy_violations.append((self._script_line, "inline JSON-LD must contain valid JSON data"))
            self._inline_script = False
            self._script_type = ""
            self._script_data = []


class CanonicalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        values = {key.lower(): value for key, value in attrs if value is not None}
        relations = {value.lower() for value in (values.get("rel") or "").split()}
        href = (values.get("href") or "").strip()
        if "canonical" in relations and href:
            self.urls.append(href)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _canonical_urls(page: Path) -> list[str]:
    html = _read_text(page)
    if html is None:
        return []
    parser = CanonicalParser()
    parser.feed(html)
    parser.close()
    return parser.urls


def _local_target(root: Path, url_path: str) -> Path:
    decoded_path = url_path.lstrip("/")
    if not decoded_path:
        return root / "index.html"
    target = root / decoded_path
    if url_path.endswith("/"):
        target = target / "index.html"
    return target


def find_broken_links(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for page in sorted(root.rglob("*.html")):
        if any(part.startswith(".") for part in page.relative_to(root).parts):
            continue
        html = _read_text(page)
        if html is None:
            errors.append(f"{page.relative_to(root)}: HTML cannot be read as UTF-8.")
            continue
        parser = LinkParser()
        parser.feed(html)
        parser.close()
        page_relative = page.relative_to(root).as_posix()

        counts = Counter(identifier for identifier, _line in parser.ids)
        for identifier, count in counts.items():
            if count > 1:
                lines = [str(line) for value, line in parser.ids if value == identifier]
                errors.append(f"{page_relative}: duplicate id '{identifier}' on lines {', '.join(lines)}.")
        for line, message in parser.policy_violations:
            errors.append(f"{page_relative}:{line}: {message}.")

        base = urljoin(BASE_URL, page_relative)
        for _kind, line, value in parser.links:
            parsed = urlparse(value)
            if parsed.scheme or parsed.netloc or value.startswith("//"):
                continue
            target_url = urlparse(urljoin(base, value))
            target = _local_target(root, target_url.path)
            try:
                target.resolve().relative_to(root)
            except ValueError:
                errors.append(f"{page_relative}:{line}: path escapes website root: {value}")
                continue
            if not target.is_file():
                errors.append(f"{page_relative}:{line}: missing local target {value}")
    return errors


def validate_sitemap(root: Path = ROOT) -> list[str]:
    """Ensure the sitemap, robots.txt, and canonical tags stay in sync."""
    errors: list[str] = []
    root = root.resolve()
    home_page = root / "index.html"
    canonical_urls = _canonical_urls(home_page)
    if len(canonical_urls) != 1:
        return [f"index.html must contain exactly one canonical URL; found {len(canonical_urls)}."]
    canonical = urlparse(canonical_urls[0])
    if canonical.scheme != "https" or not canonical.netloc or canonical.path not in ("", "/") or canonical.query or canonical.fragment:
        return ["index.html canonical URL must be an HTTPS origin URL ending in '/'."]

    origin = f"{canonical.scheme}://{canonical.netloc}"
    expected_paths = {"/", "/software/", "/launcher/"}
    expected_pages = {
        "/": root / "index.html",
        "/software/": root / "software" / "index.html",
        "/launcher/": root / "launcher" / "index.html",
    }

    catalog_path = root / "data" / "software.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        software_items = catalog.get("software", [])
        if not isinstance(software_items, list):
            raise ValueError("'software' must be an array")
        for item in software_items:
            if not isinstance(item, dict) or not isinstance(item.get("detailUrl"), str):
                errors.append("Each software entry must have a string detailUrl for sitemap validation.")
                continue
            detail_path = item["detailUrl"]
            expected_paths.add(detail_path)
            expected_pages[detail_path] = _local_target(root, detail_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, AttributeError) as exc:
        errors.append(f"Cannot read catalogue for sitemap validation: {exc}")

    for route, page in expected_pages.items():
        try:
            page.resolve().relative_to(root)
        except ValueError:
            errors.append(f"Sitemap route {route} escapes the website root.")
            continue
        if not page.is_file():
            errors.append(f"Sitemap route {route} points to a missing page: {page.relative_to(root)}.")
            continue
        expected_url = origin + (route if route != "/" else "/")
        page_canonicals = _canonical_urls(page)
        if page_canonicals != [expected_url]:
            errors.append(f"{page.relative_to(root)} must have exactly this canonical URL: {expected_url}.")

    sitemap_path = root / "sitemap.xml"
    try:
        tree = ET.parse(sitemap_path)
        urls = [(node.text or "").strip() for node in tree.findall("sm:url/sm:loc", SITEMAP_NS)]
        if not urls:
            errors.append("sitemap.xml must contain at least one <loc> URL.")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"sitemap.xml is missing or invalid XML: {exc}")
        urls = []

    seen_urls: set[str] = set()
    actual_paths: set[str] = set()
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != canonical.netloc or parsed.query or parsed.fragment:
            errors.append(f"sitemap URL must be absolute HTTPS on the canonical host: {url}")
            continue
        route = parsed.path or "/"
        if route in actual_paths:
            errors.append(f"sitemap.xml contains a duplicate route: {route}")
        if url in seen_urls:
            errors.append(f"sitemap.xml contains a duplicate URL: {url}")
        seen_urls.add(url)
        actual_paths.add(route)
        page = _local_target(root, route)
        try:
            page.resolve().relative_to(root)
        except ValueError:
            errors.append(f"sitemap URL escapes website root: {url}")
            continue
        if not page.is_file():
            errors.append(f"sitemap URL has no local page: {url}")

    missing_paths = expected_paths - actual_paths
    if missing_paths:
        errors.append("sitemap.xml is missing catalogue/page route(s): " + ", ".join(sorted(missing_paths)) + ".")

    robots_path = root / "robots.txt"
    robots = _read_text(robots_path)
    if robots is None:
        errors.append("robots.txt is missing or cannot be read.")
    else:
        sitemap_directives = [
            line.split(":", 1)[1].strip()
            for line in robots.splitlines()
            if line.strip().lower().startswith("sitemap:")
        ]
        expected_sitemap_url = origin + "/sitemap.xml"
        if sitemap_directives != [expected_sitemap_url]:
            errors.append(f"robots.txt must point to exactly {expected_sitemap_url}.")

    return errors


def main() -> int:
    errors = find_broken_links()
    errors.extend(validate_sitemap())
    if errors:
        print("Static-site validation FAILED:")
        for error in errors:
            print(" - " + error)
        return 1
    print("Static-site validation passed: markup policy, unique HTML IDs, local links, canonical URLs, robots.txt, and sitemap are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
