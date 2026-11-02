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
                nav_start = source.index('<nav class="nav-links" id="navLinks"')
                nav_end = source.index("</nav>", nav_start)
                nav = source[nav_start:nav_end]
                for href in ('href="/"', 'href="/software/"', 'href="/launcher/"',
                             'href="/#pendekatan"', 'href="/#install"', 'href="/#kontribusi"'):
                    self.assertIn(href, nav)
                self.assertIn('class="footer-nav"', source)
                self.assertIn('href="https://github.com/M-TamDre07/Linux-Software-Lab/issues"', source)
                self.assertIn('href="https://saweria.co/tamaandrea"', source)
                self.assertIn('id="year"', source)

    def test_active_navigation_state_is_accessible(self) -> None:
        expected = {
            "index.html": 'aria-current="page" aria-label="Kembali ke halaman utama"',
            "software/index.html": 'href="/software/" aria-current="page"',
            "launcher/index.html": 'href="/launcher/" aria-current="page"',
            "software/paketscope.html": 'href="/software/" aria-current="location"',
            "software/sorot.html": 'href="/software/" aria-current="location"',
        }
        for relative, marker in expected.items():
            with self.subTest(page=relative):
                source, _ = self.parse_page(relative)
                self.assertIn(marker, source)

    def test_internal_fragment_links_resolve_to_real_ids(self) -> None:
        page_ids: dict[str, set[str]] = {}
        parsed: dict[str, tuple[str, PageLinks]] = {}
        for relative in CORE_PAGES:
            parsed[relative] = self.parse_page(relative)
            page_ids[relative] = parsed[relative][1].ids

        for relative, (_, parser) in parsed.items():
            for href in parser.hrefs:
                url = urlsplit(href)
                if not url.fragment:
                    continue
                if url.netloc and url.netloc != PRODUCTION_HOST:
                    continue
                if url.netloc and url.netloc == PRODUCTION_HOST:
                    target_path = url.path.lstrip("/") or "index.html"
                elif url.path.startswith("/"):
                    target_path = url.path.lstrip("/") or "index.html"
                elif url.path:
                    continue
                else:
                    target_path = relative
                if target_path.endswith("/"):
                    target_path += "index.html"
                target_file = PUBLIC / target_path
                self.assertTrue(target_file.is_file(), f"{relative}: missing local target {href}")
                if target_path in page_ids:
                    self.assertIn(url.fragment, page_ids[target_path], f"{relative}: broken fragment {href}")
                else:
                    target_parser = PageLinks()
                    target_parser.feed(target_file.read_text(encoding="utf-8"))
                    self.assertIn(url.fragment, target_parser.ids, f"{relative}: broken fragment {href}")

    def test_public_release_versions_match_canonical_metadata(self) -> None:
        catalogue = json.loads((PUBLIC / "data/software.json").read_text(encoding="utf-8"))
        paketscope = next(item for item in catalogue["software"] if item["id"] == "paketscope")
        paketscope_page = (PUBLIC / "software/paketscope.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(paketscope["version"], paketscope_page)
        self.assertIn(paketscope["version"], readme)

        sorot_index = json.loads((ROOT / "apps/sorot/releases/index.json").read_text(encoding="utf-8"))
        latest = sorot_index["versions"][-1]
        self.assertEqual(latest["status"], "testing")
        home = (PUBLIC / "index.html").read_text(encoding="utf-8")
        sorot_page = (PUBLIC / "software/sorot.html").read_text(encoding="utf-8")
        self.assertIn(f"Sorot {latest['version']} Beta", home)
        self.assertIn(latest["version"], sorot_page)
        self.assertIn(f"Sorot {latest['version']}", readme)

    def test_compatibility_metadata_fails_closed(self) -> None:
        renderer = (PUBLIC / "assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn("compatibilityIndex = null;", renderer)
        self.assertIn("compatibilityByApp.clear();", renderer)
        self.assertIn("compatibilitySelect.disabled = !compatibilityIndex", renderer)

    def test_website_maintenance_standard_is_linked_from_readme(self) -> None:
        doc = ROOT / "docs/WEBSITE_MAINTENANCE.md"
        self.assertTrue(doc.is_file())
        contents = doc.read_text(encoding="utf-8")
        for topic in ("Source of truth", "Responsif dan aksesibilitas",
                      "Informasi produk dan rilis", "Checklist sebelum merge"):
            self.assertIn(topic, contents)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/WEBSITE_MAINTENANCE.md", readme)

    def test_launcher_page_has_no_obsolete_pull_request_cta(self) -> None:
        launcher = (PUBLIC / "launcher/index.html").read_text(encoding="utf-8")
        self.assertNotIn("/pull/22", launcher)
        self.assertIn("Panduan pengembangan", launcher)


if __name__ == "__main__":
    unittest.main()
