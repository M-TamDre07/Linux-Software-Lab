import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((REPO_ROOT / "vercel.json").read_text(encoding="utf-8"))

    def test_vercel_publishes_only_the_public_directory(self):
        self.assertEqual(self.config.get("outputDirectory"), "public")
        public = REPO_ROOT / "public"
        for relative in (
            "index.html",
            "assets/css/site.css",
            "assets/css/experience.css",
            "assets/js/site.js",
            "assets/images/linux-software-lab.svg",
            "data/software.json",
            "data/software.schema.json",
            "software/index.html",
            "software/paketscope.html",
            "software/prompter-overlay.html",
            "robots.txt",
            "sitemap.xml",
            "google505d5a75f881baa2.html",
        ):
            with self.subTest(path=relative):
                self.assertTrue((public / relative).is_file(), f"Missing public/{relative}")

    def test_legacy_portfolio_files_are_not_tracked_at_repository_root(self):
        for relative in (
            "MuhammadAndreatama.png",
            "favicon.png",
            "project1.png",
            "project2.png",
            "project3.png",
            "script.js",
            "style.css",
        ):
            with self.subTest(path=relative):
                self.assertFalse(
                    (REPO_ROOT / relative).exists(),
                    f"Legacy portfolio file should be removed: {relative}",
                )

    def test_baseline_security_headers_are_configured(self):
        headers = {}
        for rule in self.config.get("headers", []):
            if rule.get("source") == "/(.*)":
                headers = {item.get("key"): item.get("value") for item in rule.get("headers", [])}
                break
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("frame-ancestors 'none'", headers.get("Content-Security-Policy", ""))
        self.assertIn("object-src 'none'", headers.get("Content-Security-Policy", ""))
        self.assertIn("script-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertIn("connect-src 'self'", headers.get("Content-Security-Policy", ""))

    def test_catalog_data_has_a_short_cache_lifetime(self):
        rules = {
            rule.get("source"): {
                header.get("key"): header.get("value")
                for header in rule.get("headers", [])
            }
            for rule in self.config.get("headers", [])
        }
        self.assertEqual(
            rules.get("/data/software.json", {}).get("Cache-Control"),
            "public, max-age=60, stale-while-revalidate=300",
        )

    def test_search_console_verification_file_is_not_lost(self):
        path = REPO_ROOT / "public" / "google505d5a75f881baa2.html"
        self.assertIn("google-site-verification", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
