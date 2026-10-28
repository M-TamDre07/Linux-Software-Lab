"""Security and usability regression checks for the private admin dashboard."""
from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


class AdminMarkupAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.scripts: list[str] = []
        self.inline_scripts = 0
        self.inline_handlers: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "script":
            source = values.get("src", "")
            if source:
                self.scripts.append(source or "")
            elif (values.get("type") or "").casefold() != "application/ld+json":
                self.inline_scripts += 1
        self.inline_handlers.extend(name for name in values if name.lower().startswith("on"))


class AdminDashboardTests(unittest.TestCase):
    def test_private_dashboard_uses_shared_design_and_noindex(self) -> None:
        source = (PUBLIC / "admin" / "index.html").read_text(encoding="utf-8")
        parser = AdminMarkupAudit()
        parser.feed(source)
        self.assertIn('name="robots" content="noindex,nofollow,noarchive"', source)
        self.assertIn('href="https://linux-software-lab.vercel.app/admin/"', source)
        self.assertIn('/assets/css/experience.css', source)
        self.assertIn('/assets/css/admin.css', source)
        self.assertIn('/assets/js/supabase-config.js', parser.scripts)
        self.assertIn('/assets/js/admin.js', parser.scripts)
        self.assertEqual(parser.inline_scripts, 0)
        self.assertEqual(parser.inline_handlers, [])
        self.assertEqual(parser.ids.count("main"), 1)
        self.assertEqual(parser.ids.count("loginForm"), 1)
        self.assertEqual(parser.ids.count("catalogRows"), 1)
        self.assertIn('href="/launcher/"', source)
        self.assertNotIn("sb_secret_", source)

    def test_dashboard_requires_server_checked_admin_membership(self) -> None:
        script = (PUBLIC / "assets" / "js" / "admin.js").read_text(encoding="utf-8")
        self.assertIn("/auth/v1/token?grant_type=password", script)
        self.assertIn("/auth/v1/user", script)
        self.assertIn("/rest/v1/lsl_admin_users?", script)
        self.assertIn("/rest/v1/software_catalog?", script)
        self.assertIn("active: 'eq.true'", script)
        self.assertIn("localStorage", script)
        self.assertIn("SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60", script)
        self.assertIn("authenticated_at", script)
        self.assertIn("parsed.authenticated_at < SESSION_MAX_AGE_SECONDS", script)
        self.assertIn("/auth/v1/logout?scope=local", script)
        self.assertIn("credentials: 'omit'", script)
        self.assertIn("redirect: 'error'", script)
        self.assertNotIn(".innerHTML", script)
        self.assertNotIn("service_role", script)
        self.assertNotIn("sb_secret_", script)
        self.assertNotIn("SUPABASE_SECRET_KEY", script)

    def test_dashboard_keeps_catalog_mirror_read_only(self) -> None:
        script = (PUBLIC / "assets" / "js" / "admin.js").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "ADMIN_DASHBOARD.md").read_text(encoding="utf-8")
        self.assertNotIn("method: 'PATCH'", script)
        self.assertNotIn("method: 'PUT'", script)
        self.assertNotIn("method: 'DELETE'", script)
        self.assertIn("public/data/software.json", docs)
        self.assertIn("pull request", docs.casefold())
        self.assertIn("REPLACE_WITH_AUTH_USER_UUID", docs)
        self.assertIn("active", docs.casefold())

    def test_admin_styles_include_responsive_and_reduced_motion_rules(self) -> None:
        css = (PUBLIC / "assets" / "css" / "admin.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:780px)", css)
        self.assertIn("@media(max-width:700px)", css)
        self.assertIn("@media(max-width:380px)", css)
        self.assertIn("prefers-reduced-motion:reduce", css)
        self.assertIn("[hidden]{display:none!important}", css)


if __name__ == "__main__":
    unittest.main()
