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
        self.assertIn("validateCatalogPayload(await fetchSupabaseCatalog())", js)
        self.assertIn("validateCatalogPayload(await fetchStaticCatalog())", js)
        self.assertIn("Sumber katalog: mirror Supabase tersedia.", js)
        self.assertIn("menggunakan data statis website", js)
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

    def test_admin_migration_keeps_membership_and_catalog_reads_restricted(self):
        migrations = ROOT / "supabase" / "migrations"
        admin_files = sorted(migrations.glob("*add_admin_catalog_read_access.sql"))
        self.assertEqual(len(admin_files), 1, "The migration already applied to Supabase must be tracked in Git.")
        migration = admin_files[0].read_text(encoding="utf-8").casefold()
        self.assertIn("alter table public.lsl_admin_users enable row level security", migration)
        self.assertIn("revoke all on table public.lsl_admin_users from public, anon, authenticated", migration)
        self.assertIn("grant select on table public.lsl_admin_users to authenticated", migration)
        self.assertIn("using (user_id = (select auth.uid()))", migration)
        self.assertIn("grant select on table public.software_catalog to authenticated", migration)
        self.assertIn("where user_id = (select auth.uid())", migration)
        self.assertIn("active is true", migration)
        self.assertNotRegex(migration, r"grant\s+(?:insert|update|delete|all)\s+.*\bto\s+anon\b")

    def test_browser_search_stays_local_and_supabase_filter_is_fixed(self):
        js = (ROOT / "public/assets/js/site.js").read_text(encoding="utf-8")
        self.assertIn("const getFilteredRows = () =>", js)
        self.assertIn("app.id, app.slug, app.name", js)
        self.assertIn("tokens.every(token => app._searchText.includes(token))", js)
        self.assertIn("new URLSearchParams({", js)
        self.assertIn("published: 'eq.true'", js)
        self.assertIn("order: 'sort_order.asc,name.asc'", js)
        self.assertNotIn("query: query", js)
        self.assertNotIn("searchInput.value", js[js.index("const fetchSupabaseCatalog"):js.index("if (grid) {")])
        self.assertIn("const escapeHTML =", js)
        self.assertIn("validateCatalogPayload", js)
        self.assertNotIn(".filter(app => app && typeof app.id", js)

    def test_admin_ui_does_not_interpolate_untrusted_data_as_html(self):
        js = (ROOT / "public/assets/js/admin.js").read_text(encoding="utf-8")
        self.assertNotIn(".innerHTML", js)
        self.assertIn("user_id: 'eq.' + authUser.id", js)
        self.assertIn("active: 'eq.true'", js)
        self.assertIn("/auth/v1/user", js)
        self.assertIn("credentials: 'omit'", js)

    def test_sync_workflow_never_writes_from_pull_requests(self):
        workflow = (ROOT / ".github/workflows/supabase-catalog-sync.yml").read_text(encoding="utf-8")
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertIn("${{ secrets.SUPABASE_SECRET_KEY }}", workflow)
        self.assertIn("python scripts/sync_supabase_catalog.py --check", workflow)


if __name__ == "__main__":
    unittest.main()
