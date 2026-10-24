import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SupabaseIntegrationTests(unittest.TestCase):
    def test_browser_config_contains_only_the_public_key(self):
        config = (ROOT / "public/assets/js/supabase-config.js").read_text(encoding="utf-8")
        self.assertIn("https://ttofugaqwthmvhvntdlc.supabase.co", config)
        self.assertIn("sb_publishable_", config)
        self.assertNotIn("sb_secret_", config)
        self.assertNotIn("service_role", config)

    def test_browser_sends_both_required_api_headers(self):
        js = (ROOT / "public/assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn("apikey: config.publishableKey", js)
        self.assertIn("Authorization: 'Bearer ' + config.publishableKey", js)

    def test_sync_uses_api_key_and_authorization_headers(self):
        script = (ROOT / "scripts/sync_supabase_catalog.py").read_text(encoding="utf-8")
        self.assertIn('"apikey": key', script)
        self.assertIn('"Authorization": f"Bearer {key}"', script)
        self.assertIn('secret_key.startswith("sb_secret_")', script)

    def test_catalogue_falls_back_to_static_json_without_remote_search(self):
        js = (ROOT / "public/assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn("fetch('/data/software.json'", js)
        self.assertIn("return await fetchSupabaseCatalog()", js)
        self.assertIn("return await fetchStaticCatalog()", js)
        self.assertIn("catch (_)", js)
        self.assertIn("getFilteredRows()", js)

    def test_database_migration_is_read_only_for_anonymous_clients(self):
        migration = next((ROOT / "supabase/migrations").glob("*create_software_catalog.sql")).read_text(encoding="utf-8").lower()
        self.assertIn("enable row level security", migration)
        self.assertIn("revoke all on table public.software_catalog from public, anon, authenticated", migration)
        self.assertIn("grant select on table public.software_catalog to anon", migration)
        self.assertIn("for select", migration)
        self.assertIn("using (published is true)", migration)
        self.assertNotRegex(migration, r"grant\s+(?:insert|update|delete|all)\s+.*\bto\s+anon\b")

    def test_sync_workflow_never_writes_from_pull_requests(self):
        workflow = (ROOT / ".github/workflows/supabase-catalog-sync.yml").read_text(encoding="utf-8")
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertIn("${{ secrets.SUPABASE_SECRET_KEY }}", workflow)
        self.assertIn("python scripts/sync_supabase_catalog.py --check", workflow)


if __name__ == "__main__":
    unittest.main()
