# Website architecture

Linux Software Lab is a static-first software catalogue. The design favours a small attack surface, predictable deployments, fast page loads, and simple maintenance. A database or backend search service is not needed for the current catalogue size.

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
5. GitHub Actions runs the validators, JavaScript syntax check, JSON parsing, and regression tests.
6. The browser fetches same-origin JSON and builds a searchable catalogue; it does not transmit search terms to a third-party search service.

## Catalogue scaling

Search indexes are built once when catalogue JSON loads. Search covers names, summaries, descriptions, categories, versions, types, tags, keywords, features, and platforms. Category and platform options come from metadata rather than being hard-coded. Status and sort settings are shareable in the URL. Results are appended in small batches so hundreds of records do not need to be rendered into the DOM at once.

Measure catalogue payload and render time before introducing a database, generated full-text index, external search provider, or framework build. Add infrastructure when measurements and user needs justify it, not by default.

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
- The website has no backend, account database, or telemetry endpoint.
- CSP allows same-origin scripts/data and the Google Fonts files/styles used by the pages.
- X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy are configured in vercel.json.
- Never place .env files, API keys, private credentials, or unreviewed files under public/.
