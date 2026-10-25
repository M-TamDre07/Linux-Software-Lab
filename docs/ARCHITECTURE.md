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
├── scripts/                      # Repository checks, never published
├── tests/                        # Regression tests, never published
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
6. The browser reads published rows from Supabase with the public publishable key, falling back to same-origin JSON if the API fails; search and filtering remain client-side.

## Catalogue scaling

Search indexes are built once when catalogue JSON loads. Search covers names, summaries, descriptions, categories, versions, types, tags, keywords, features, and platforms. Category and platform options come from metadata rather than being hard-coded. Status and sort settings are shareable in the URL. Results are appended in small batches so hundreds of records do not need to be rendered into the DOM at once.

The Supabase mirror is limited to public catalogue metadata. Do not expand it into user data, analytics, package search, or a write API without a concrete requirement, measured need, and a separate security review.

## Metadata and release integrity

- planned: idea or specification, not yet usable.
- testing: implementation exists but is not ready for a stable release.
- released: a real, verified HTTPS release URL exists.
- archived: no longer actively maintained.
- The catalogue must never present concept artwork as a screenshot of a released app.
- Avoid compatibility claims that have not been tested on the stated platform.
- New product pages must have canonical URLs and be added to public/sitemap.xml.
- Search filters are client-side; search terms stay in the browser.

## Security boundaries

- Only public/ is sent to Vercel as static output.
- The website has no accounts or telemetry endpoint; Supabase is a read-only public catalogue mirror.
- CSP allows same-origin scripts, Google Fonts files/styles, and connections only to the configured Supabase project.
- X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy are configured in vercel.json.
- Only the Supabase publishable key is present in browser assets. Never place an sb_secret_ key, service-role key, .env file, or other private credential under public/.
