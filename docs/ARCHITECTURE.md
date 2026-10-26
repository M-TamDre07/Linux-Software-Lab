# Website architecture

Linux Software Lab is a static-first software catalogue with a read-only Supabase mirror and a committed JSON fallback. GitHub remains the source of truth, Vercel serves the site, and the mirror is used only to retrieve public product metadata. This adds synchronization and central read access without making catalogue search depend on a backend.

## Directory ownership

~~~text
repository/
├── public/                       # Published website only
│   ├── index.html
│   ├── assets/css/site.css
│   ├── assets/js/site.js
│   ├── assets/images/
│   ├── data/software.json
│   ├── data/software.schema.json
│   └── software/
│       ├── index.html
│       └── <slug>.html
├── apps/<slug>/                  # Application source code
├── templates/application/        # Standard starter layout for new products
├── scripts/                      # Validators, sync checks, and safe scaffolding
├── tests/                        # Regression and security-boundary tests
├── docs/                         # Maintainer documentation, never published
└── vercel.json                   # Sets outputDirectory to public/
~~~

Keep the Vercel Root Directory at the repository root. vercel.json selects public/ as the static output, so source code, test files, documentation, and unused legacy files are not part of the deployed website.

## Source of truth and data flow

1. Each entry is defined once in public/data/software.json.
2. public/data/software.schema.json documents the catalogue data contract.
3. scripts/validate_catalog.py validates required fields, safe local paths, unique IDs/slugs, date and URL formats, accepted software types/statuses, and release-link rules.
4. scripts/check_site_links.py checks local HTML references and verifies sitemap, robots directives, and canonical URLs against actual catalogue pages.
5. GitHub Actions runs site checks and validates the Supabase sync mapping; a trusted main-branch workflow mirrors approved metadata to Supabase.
6. The browser reads published rows from Supabase with the public publishable key. `public/assets/js/catalog-contract.js` validates both the mirror response and the same-origin JSON fallback before anything is rendered; if the mirror is unavailable or malformed, the browser uses the validated static catalogue. Search and filtering remain client-side.
7. The read-only `scripts/check_live_integrations.py` compares production Vercel JSON and published Supabase rows with the canonical GitHub catalogue. The scheduled/manual `Live integration integrity` workflow catches deployment lag or mirror drift without writing to either service.

## Catalogue scaling

A shared runtime contract rejects malformed rows, duplicate IDs/slugs, unknown statuses/types, unsafe URLs/assets, and invalid dates before rendering. Search indexes are built once after catalogue JSON loads. Search covers names, summaries, descriptions, categories, versions, types, tags, keywords, features, and platforms. Category and platform options come from metadata rather than being hard-coded. Status and sort settings are shareable in the URL. Results are appended in small batches so hundreds of records do not need to be rendered into the DOM at once.

The Supabase mirror is limited to public catalogue metadata. Do not expand it into user data, analytics, package search, or a write API without a concrete requirement, measured need, and a separate security review.

## Metadata and release integrity

- planned: idea or specification, not yet usable.
- testing: implementation exists but is not ready for a stable release.
- released: a real, verified HTTPS release URL exists.
- archived: no longer actively maintained.
- The catalogue must never present concept artwork as a screenshot of a released app.
- Avoid compatibility claims that have not been tested on the stated platform.
- New product pages must have canonical URLs and be added to public/sitemap.xml. Follow [SEO_MAINTENANCE.md](SEO_MAINTENANCE.md) for the complete crawlability and content quality contract.
- Search filters are client-side; search terms stay in the browser.

## Application contribution contract

New applications start from `templates/application/` via `python scripts/scaffold_app.py`. The scaffold is intentionally runtime-neutral; each product chooses its own runtime, licence, OS matrix, and real package formats. The helper never mutates the catalogue, public pages, release index, or launcher allowlist. User-facing error messages follow [ERROR_HANDLING_STANDARD.md](ERROR_HANDLING_STANDARD.md). Runtime/framework and OS support decisions follow [TECH_STACK_AND_RUNTIME_POLICY.md](TECH_STACK_AND_RUNTIME_POLICY.md).

## Security boundaries

- Only public/ is sent to Vercel as static output.
- The website has no accounts or telemetry endpoint; Supabase is a read-only public catalogue mirror.
- CSP allows same-origin scripts, Google Fonts files/styles, and connections only to the configured Supabase project.
- X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy are configured in vercel.json.
- Only the Supabase publishable key is present in browser assets. Never place an sb_secret_ key, service-role key, .env file, or other private credential under public/.
