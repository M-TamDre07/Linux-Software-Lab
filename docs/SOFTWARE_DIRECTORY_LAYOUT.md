# Software directory and release layout

Linux Software Lab separates the **website**, **catalogue metadata**, and each **desktop software product**. The public catalogue has one canonical source; generated website, launcher, and database copies are mirrors.

## Repository map

```text
repository/
├── public/                         # Only website output deployed to Vercel
│   ├── index.html                  # Homepage and featured app entry points
│   ├── assets/                     # Shared CSS, JS, icons, and concept artwork
│   ├── data/
│   │   ├── software.json           # Canonical public catalogue source
│   │   └── distribution-index.json # Generated release/distro compatibility mirror
│   ├── software/
│   │   ├── index.html              # Storefront-style software directory
│   │   ├── paketscope.html         # PaketScope product details and archives
│   │   └── sorot.html              # Sorot product details and version history
│   ├── robots.txt
│   └── sitemap.xml
├── apps/                           # Source and immutable release files per product
│   ├── paketscope/
│   │   ├── paketscope/             # Current source tree
│   │   ├── tests/
│   │   └── releases/<version>/     # Versioned packages, manifest, checksums, notes
│   ├── sorot/
│   │   └── releases/
│   │       ├── index.json          # Canonical Sorot version register
│   │       ├── README.md           # Archive policy
│   │       └── <version>/          # Immutable manifest, SHA256SUMS, artifacts
│   └── software-center/            # Linux Software Lab desktop launcher and catalogue
├── scripts/                        # Catalogue, manifest, docs, and website tools
├── templates/application/          # Starter contract for new products
├── tests/                          # Website, catalogue, release, and integration tests
├── docs/                           # Architecture, SEO, release, and maintenance docs
├── supabase/migrations/             # Database schema and RLS history
└── vercel.json                     # Publishes public/ only
```

## Current product/version boundaries

- **PaketScope source:** `apps/paketscope/` on `main` is version `3.0.0.dev5`.
- **PaketScope preview artifact:** `4.0.0.dev3` is a separate versioned development package in `apps/paketscope/releases/4.0.0.dev3/`. It remains `testing`, targets Debian 13, and is not a stable release. The source-tree version and downloadable preview-artifact version must not be silently conflated.
- **Sorot:** `1.0.23` is `released` in the `beta` channel: .deb and Python wheel artifacts are listed with SHA-256, but a version-specific QA report and clean-install evidence are not published. Version `0.9.0` is retained as `archived`; its actual .deb remains downloadable but is not recommended for new installations. Versions `0.8.0` and earlier remain testing/Beta according to their manifests.
- **Catalogue:** `public/data/software.json` is the canonical product catalogue. It drives website cards and metadata synchronisation. Do not edit generated copies or the Supabase mirror as independent sources.
- **Distribution compatibility:** `public/data/distribution-index.json` is generated from versioned release manifests and distribution metadata. A browser may suggest a broad OS family; users still choose their Linux distribution manually because a browser cannot reliably identify the exact distro.

## Rules for adding an application

- Use a stable lowercase product slug for `apps/<slug>/` and `public/software/<slug>.html`.
- Keep each product's code, tests, docs, licence, dependencies, changelog, and packaging files in its own directory wherever possible.
- Do not reuse a licence file from another product without an explicit licensing decision.
- Keep public catalogue content in `public/data/software.json`; do not hard-code product cards into website JavaScript.
- Keep Vercel's static output set to `public/`. Application source, packaging metadata, tests, and private maintainer notes must not be published as site assets.
- Treat lifecycle status and release channel as separate fields. `released` means an artifact is available; it does not mean `stable`. Use `archived` for old builds that remain downloadable but are not recommended for new installations.
- A release URL must point to a real, verified HTTPS artifact. Every artifact needs a manifest entry and SHA-256 that matches the actual bytes.
- Never claim a distro is supported solely because the package manager format looks compatible. Require a tested target matrix.

## Canonical starter template

Use `templates/application/` as the baseline rather than copying one existing product's layout. It establishes the shared root contract—`README.md`, `application.yaml`, `CHANGELOG.md`, a licence decision gate, source, unit/integration/security tests, architecture/development/security/release docs, assets/fixtures, packaging placeholders, and immutable release guidance.

Generate the scaffold safely:

```bash
python scripts/scaffold_app.py --slug sample-tool --name "Sample Tool" --description "A concise purpose statement."
```

The helper writes only `apps/<slug>/`; it refuses to overwrite, rejects malformed slugs, and leaves `public/data/software.json`, product pages, launcher allowlists, and release indexes untouched. The template is intentionally runtime-neutral. Packaging subdirectories are documentation placeholders, not enabled formats. See [templates/README.md](../templates/README.md), [release platform foundations](RELEASE_PLATFORM_FOUNDATION.md), and [the error-handling standard](ERROR_HANDLING_STANDARD.md).

## Debian package verification

Before advertising a `.deb`:

1. Build it in a clean Debian-compatible environment.
2. Inspect package metadata and contents.
3. Test install, launch, upgrade, and uninstall in a disposable environment for every claimed distro/version target.
4. Verify dependencies and that no application state is removed unexpectedly.
5. Publish SHA-256 checksums and a clear versioned changelog.
6. Define a trusted signing/repository plan before publishing an APT repository.

The website should display installation commands only after the corresponding artifact and instructions pass those checks. A checksum detects a mismatch against the published manifest; it is not a publisher signature.

## Validation flow

From the repository root:

```bash
python scripts/validate_catalog.py
python apps/sorot/validate_releases.py
python scripts/sync_distribution_index.py --check
python scripts/check_site_links.py
python scripts/check_docs_links.py
python -m unittest discover -s tests -v
```

GitHub Actions repeats the relevant checks. On merge, the release-index workflow regenerates derived web/launcher manifests, while the trusted Supabase catalogue workflow mirrors canonical rows. Do not write catalogue rows directly from browser code; keep the mirror read-only for anonymous clients.

See [Sorot release policy](SOROT_RELEASES.md), [SEO maintenance](SEO_MAINTENANCE.md), and [website maintenance](WEBSITE_MAINTENANCE.md).
