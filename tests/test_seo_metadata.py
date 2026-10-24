import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
PAGES = (
    "index.html",
    "software/index.html",
    "software/paketscope.html",
    "software/sorot.html",
)
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class SeoMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sitemap_path = PUBLIC / "sitemap.xml"
        cls.sitemap = ET.parse(sitemap_path).getroot()
        cls.sitemap_urls = {
            node.text.strip()
            for node in cls.sitemap.findall("sm:url/sm:loc", SITEMAP_NS)
            if node.text
        }

    def test_pages_have_unique_canonical_and_share_metadata(self):
        for relative_path in PAGES:
            with self.subTest(page=relative_path):
                html = (PUBLIC / relative_path).read_text(encoding="utf-8")
                canonicals = re.findall(
                    r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>',
                    html,
                    flags=re.IGNORECASE,
                )
                self.assertEqual(len(canonicals), 1, "page must have one canonical URL")
                self.assertEqual(len(re.findall(r"<title>.*?</title>", html, re.DOTALL)), 1)
                self.assertRegex(html, r'<meta\s+name="description"\s+content="[^"]+"')
                self.assertRegex(html, r'<meta\s+name="robots"\s+content="index,follow"')
                self.assertRegex(html, r'<meta\s+property="og:image"\s+content="https://[^"]+"')
                self.assertRegex(html, r'<meta\s+name="twitter:card"\s+content="summary_large_image"')

                canonical = canonicals[0]
                self.assertIn(canonical, self.sitemap_urls, "canonical page must be in sitemap")
                canonical_parts = urlparse(canonical)
                image_match = re.search(
                    r'<meta\s+property="og:image"\s+content="([^"]+)"', html
                )
                self.assertIsNotNone(image_match)
                image_url = urlparse(image_match.group(1))
                self.assertEqual(image_url.scheme, "https")
                self.assertEqual(image_url.netloc, canonical_parts.netloc)
                image_path = PUBLIC / image_url.path.lstrip("/")
                self.assertTrue(image_path.is_file(), f"social image does not exist: {image_path}")

    def test_json_ld_is_valid_schema_org_data(self):
        for relative_path in PAGES:
            with self.subTest(page=relative_path):
                html = (PUBLIC / relative_path).read_text(encoding="utf-8")
                blocks = re.findall(
                    r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
                    html,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                self.assertEqual(len(blocks), 1, "page must have one JSON-LD block")
                data = json.loads(blocks[0])
                self.assertEqual(data.get("@context"), "https://schema.org")
                if "@graph" in data:
                    types = {item.get("@type") for item in data["@graph"]}
                    self.assertIn("Organization", types)
                    self.assertIn("WebSite", types)
                else:
                    self.assertEqual(data.get("@type"), "BreadcrumbList")


if __name__ == "__main__":
    unittest.main()
