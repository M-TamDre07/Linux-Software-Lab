import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_site_links import find_broken_links, validate_sitemap


BASE = "https://example.test"


class SiteLinksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "software").mkdir()
        (self.root / "launcher").mkdir()
        (self.root / "data").mkdir()
        (self.root / "assets").mkdir()
        (self.root / "index.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://example.test/"></head>'
            '<body><a href="/software/">Catalogue</a></body></html>',
            encoding="utf-8",
        )
        (self.root / "software" / "index.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://example.test/software/"></head>'
            '<body><a href="/software/demo.html">Demo</a></body></html>',
            encoding="utf-8",
        )
        (self.root / "launcher" / "index.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://example.test/launcher/"></head>'
            '<body><a href="/">Home</a></body></html>',
            encoding="utf-8",
        )
        (self.root / "software" / "demo.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://example.test/software/demo.html"></head>'
            '<body><a href="/">Home</a></body></html>',
            encoding="utf-8",
        )
        (self.root / "data" / "software.json").write_text(
            json.dumps({"schemaVersion": 2, "software": [{"detailUrl": "/software/demo.html"}]}),
            encoding="utf-8",
        )
        (self.root / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n\nSitemap: https://example.test/sitemap.xml\n",
            encoding="utf-8",
        )
        (self.root / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://example.test/</loc></url>'
            '<url><loc>https://example.test/software/</loc></url>'
            '<url><loc>https://example.test/launcher/</loc></url>'
            '<url><loc>https://example.test/software/demo.html</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()


    def test_duplicate_html_ids_are_rejected(self):
        (self.root / "software" / "demo.html").write_text(
            '<html><head><link rel="canonical" href="https://example.test/software/demo.html"></head>'
            '<body><div id="duplicate"></div><section id="duplicate"></section></body></html>',
            encoding="utf-8",
        )
        errors = find_broken_links(self.root)
        self.assertTrue(any("duplicate id 'duplicate'" in error for error in errors))

    def test_inline_scripts_and_event_handlers_are_rejected_by_markup_policy(self):
        (self.root / "software" / "demo.html").write_text(
            '<html><head><link rel="canonical" href="https://example.test/software/demo.html"></head>'
            '<body><button onclick="run()">Go</button><script>run()</script></body></html>',
            encoding="utf-8",
        )
        errors = find_broken_links(self.root)
        self.assertTrue(any("inline event handler 'onclick'" in error for error in errors))
        self.assertTrue(any("inline script violates" in error for error in errors))

    def test_json_ld_data_block_is_allowed_and_validated(self):
        (self.root / "software" / "demo.html").write_text(
            '<html><head><link rel="canonical" href="https://example.test/software/demo.html">'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"SoftwareApplication"}</script>'
            '</head><body></body></html>',
            encoding="utf-8",
        )
        self.assertEqual(find_broken_links(self.root), [])

    def test_malformed_json_ld_data_block_is_rejected(self):
        (self.root / "software" / "demo.html").write_text(
            '<html><head><link rel="canonical" href="https://example.test/software/demo.html">'
            '<script type="application/ld+json">{"@type":}</script>'
            '</head><body></body></html>',
            encoding="utf-8",
        )
        errors = find_broken_links(self.root)
        self.assertTrue(any("valid JSON data" in error for error in errors))

    def test_local_links_and_assets_pass(self):
        self.assertEqual(find_broken_links(self.root), [])

    def test_valid_sitemap_and_canonical_tags_pass(self):
        self.assertEqual(validate_sitemap(self.root), [])

    def test_missing_software_route_is_rejected_by_sitemap(self):
        sitemap = self.root / "sitemap.xml"
        sitemap.write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://example.test/</loc></url>'
            '<url><loc>https://example.test/software/</loc></url></urlset>',
            encoding="utf-8",
        )
        errors = validate_sitemap(self.root)
        self.assertTrue(any("missing catalogue/page route" in error for error in errors))

    def test_wrong_robots_sitemap_host_is_rejected(self):
        robots = self.root / "robots.txt"
        robots.write_text("User-agent: *\nSitemap: https://wrong.example/sitemap.xml\n", encoding="utf-8")
        errors = validate_sitemap(self.root)
        self.assertTrue(any("robots.txt must point to exactly" in error for error in errors))

    def test_noncanonical_host_in_sitemap_is_rejected(self):
        sitemap = self.root / "sitemap.xml"
        sitemap.write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://example.test/</loc></url>'
            '<url><loc>https://wrong.example/software/</loc></url>'
            '<url><loc>https://example.test/software/demo.html</loc></url></urlset>',
            encoding="utf-8",
        )
        errors = validate_sitemap(self.root)
        self.assertTrue(any("canonical host" in error for error in errors))

    def test_missing_local_target_is_rejected(self):
        (self.root / "index.html").write_text(
            '<html><head><link rel="canonical" href="https://example.test/"></head>'
            '<body><img src="/assets/missing.svg"></body></html>',
            encoding="utf-8",
        )
        errors = find_broken_links(self.root)
        self.assertTrue(any("missing local target" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
