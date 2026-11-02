"""Regression checks for shared website structure and release-information accuracy."""
from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CORE_PAGES = (
    "index.html",
    "software/index.html",
    "software/paketscope.html",
    "software/sorot.html",
    "launcher/index.html",
)
PRODUCTION_HOST = "linux-software-lab.vercel.app"


class PageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.hrefs.append(str(values["href"]))


class WebsiteMaintenanceTests(unittest.TestCase):
    def parse_page(self, relative: str) -> tuple[str, PageLinks]:
        source = (PUBLIC / relative).read_text(encoding="utf-8")
        parser = PageLinks()
        parser.feed(source)
        return source, parser

    def test_primary_pages_share_navigation_and_footer_contract(self) -> None:
        for relative in CORE_PAGES:
            with self.subTest(page=relative):
                source, _ = self.parse_page(relative)
                nav_start = source.¶»§q«^