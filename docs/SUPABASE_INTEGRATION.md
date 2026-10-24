# Supabase catalogue integration

## Source of truth and responsibilities

- **GitHub** is the source of truth: public/data/software.json, its schema, website code, and migration files are reviewed like other code.
- **GitHub Actions** validates catalogue changes on pull requests and mirrors the catalogue to Supabase after a change reaches main.
- **Supabase** serves a public, read-only mirror of curated catalogue metadata. It is not a second authoring interface; visitors cannot add, edit, or delete rows.
- **Vercel** serves the static website from public/. The website reads the mirror when available and falls back to the same-origin JSON file if the API is unavailable.

Search, filtering, and sorting remain in the browser. Search terms are not sent to Supabase or another remote service. Existing layout, styling, and static catalogue behavior remain available without the backend.

## Database and access model

The migration supabase/migrations/20261024172127_create_software_catalog.sql defines public.software_catalog with a narrow catalogue schema. Row Level Security is enabled. The anonymous role has SELECT only, and the software_catalog_public_read policy exposes rows where published is true. No public write privileges are granted. Do not add credentials, per-user data, logs, or secrets to this table.

The browser uses only the public publishable key in public/assets/js/supabase-config.js. A publishable key is not an authorization boundary: RLS and SQL grants are the data protection. Never put an sb_secret_ key or legacy service-role key in website assets, HTML, source code, or public environment variables.

## CI credential setup

To enable automatic GitHub-to-Supabase updates:

1. In the Supabase Dashboard, open Project Settings → API Keys and create or locate a modern secret key (sb_secret_...) for the Linux-Software-Lab project.
2. In GitHub, open repository Settings → Secrets and variables → Actions → New repository secret.
3. Name it SUPABASE_SECRET_KEY and paste the key directly into GitHub's secret form. Never put the key in a commit or chat.
4. Run the Supabase catalogue sync workflow from the default main branch. The workflow upserts current rows, marks removed IDs unpublished instead of deleting history, and verifies active IDs after synchronization.

Pull-request runs only validate local data and never contact production Supabase. If the secret is absent, the production sync step emits a warning and skips writing; the public website continues using the static fallback.

## Verification

Run locally:

    python scripts/validate_catalog.py
    python scripts/sync_supabase_catalog.py --check
    python -m unittest discover -s tests -v

After database changes, inspect migration history and Supabase security/performance advisors. The intended public query is a filtered SELECT on software_catalog; it must never accept writes from an anonymous browser. If the Data API is disabled for this project, enable it deliberately in the Supabase dashboard or keep static JSON as the operational path.

## Scope and limitations

This mirror is a catalogue backend, not authentication, analytics, user storage, package downloads, or a server-side search service. Any future authenticated feature needs a separate data model, RLS policies, and security review.
