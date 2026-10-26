# Supabase catalogue integration

## Source of truth and responsibilities

- **GitHub** is the source of truth: public/data/software.json, its schema, website code, migration files, and distribution metadata are reviewed like other code.
- **GitHub Actions** validates catalogue changes on pull requests and mirrors the canonical catalogue to Supabase after a change reaches main.
- **Supabase** serves a read-only public mirror and an authenticated, RLS-protected view for maintainers. It is not a second authoring interface while GitHub remains canonical.
- **Vercel** serves the static website from public/. The public catalogue reads the mirror when available and falls back to the same-origin JSON file if the API is unavailable.
- **Linux Software Lab Center** consumes the same reviewed catalogue/distribution contract and local cache. It does not need the website's publishable key or any server secret just to read its canonical public metadata.

Search, filtering, and sorting remain in the browser. Search terms are not sent to Supabase or another remote service. Existing layout, styling, and static catalogue behavior remain available without the backend.

## Public database and access model

The migration supabase/migrations/20261024172127_create_software_catalog.sql defines public.software_catalog with a narrow catalogue schema. Row Level Security is enabled. Anonymous visitors have SELECT only, and the software_catalog_public_read policy exposes rows where published is true. No public write privileges are granted. Do not put credentials, per-user data, logs, or secrets into this table.

The browser uses the publishable key configured in public/assets/js/supabase-config.js. A publishable key is expected to be present in public frontend code and is not an authorization boundary. SQL grants and RLS determine which data can be read. Never put an sb_secret_ key or legacy service-role key in website assets, HTML, source code, or browser-public environment variables.

## Admin Control Room

The private route is /admin/. It uses the pinned Supabase JavaScript client, Supabase Auth password login, and the database policies from migration 20261026105902_add_admin_catalog_read_access.sql.

The migration creates public.lsl_admin_users. It has RLS enabled, grants SELECT only to authenticated users, and only lets a user read their own access row. A second SELECT policy on software_catalog allows an active registered maintainer to read all catalogue rows, including unpublished entries. Anonymous reads continue to be restricted to published rows.

The dashboard is intentionally read-only for catalogue records because GitHub is the source of truth. It offers statistics, filtering, row detail JSON, JSON export, and links to the canonical GitHub source, the CI sync workflow, and Supabase Table Editor. Editing Supabase mirror rows directly is disabled to prevent changes being overwritten by the next GitHub sync.

See docs/ADMIN_DASHBOARD.md for creating the first maintainer, granting/revoking access, and troubleshooting.

## Set up CI credentials

To enable automatic GitHub-to-Supabase updates:

1. In Supabase, open Project Settings → API Keys and create or locate a modern server key (sb_secret_...) for the Linux-Software-Lab project.
2. In GitHub, open repository Settings → Secrets and variables → Actions → New repository secret.
3. Name it SUPABASE_SECRET_KEY and paste the key directly into the GitHub secret form. Never put the key in a commit, public environment variable, browser JavaScript, or chat.
4. Run the Supabase catalogue sync workflow from the default main branch. The workflow upserts current rows, marks removed IDs unpublished instead of deleting history, and verifies active catalogue fields after synchronization.

Pull-request runs only validate local data and never contact production Supabase. If the secret is absent, the production sync step emits a warning and skips writing; the public website continues using the static fallback. A publishable key is not a replacement for the CI server key.

## Verification

Run locally:

    python scripts/validate_catalog.py
    python scripts/sync_supabase_catalog.py --check
    python -m unittest discover -s tests -v

After database changes, inspect migration history and Supabase security/performance advisors. Confirm anonymous clients cannot read unpublished rows or write to the mirror, and that a normal authenticated account without an active lsl_admin_users row cannot read unpublished rows. If the Data API is disabled for the project, enable it deliberately or keep the static JSON as the operational path.

## Scope and future direction

The current mirror is a catalogue backend, not an analytics platform, package download host, user database, or server-side search service. Future dynamic data needs its own data model, explicit RLS policies, and a security review.

If full catalogue CRUD is required inside the dashboard, first select one authority model. A trusted backend can open pull requests to GitHub, or the system can migrate fully to Supabase as the source of truth and treat JSON as a generated build artifact. Do not enable direct edits to the mirror while GitHub remains canonical.
