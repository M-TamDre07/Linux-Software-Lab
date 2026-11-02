"""Regression tests for the shared public website experience.

These checks keep the core pages consistent and catch common accessibility and
responsive-layout regressions without depending on an external browser service.
"""
from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CORE_PAGES = (
    "index.html",
    "software/index.html",
    "software/paketscope.html",
    "software/sorot.html",
    "launcher/index.html",
)


class PageAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.meta: dict[str, str] = {}
        self.canonicals: list[str] = []
        self.stylesheets: list[str] = []
        self.ids: list[str] = []
        self.h1_count = 0
        self.skip_links: list[str] = []
        self.inline_scripts = 0
        self.inline_styles = 0
        self.inline_event_handlers: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang", "") or ""
        if tag == "meta":
            name = values.get("name", "")
            if name:
                self.meta[name.lower()] = values.get("content", "") or ""
        if tag == "link":
            rel = (values.get("rel", "") or "").lower().split(¶»§q«^