# Package-source integration plan

## Purpose and boundary

The website's existing `public/data/software.json` catalog describes projects maintained by Linux Software Lab. It is not yet a cross-distribution package index. Do not mix project cards with records for packages from Debian, Arch, Fedora, or Flathub without an explicit data-model distinction.

The first integration milestone is a trustworthy, source-attributed package directory. It must never imply that a package from one distribution is compatible with another, or that a website search result means a package is installed or safe to install.

## Source registry

Prefer authoritative source pages and documented interfaces:

- Debian: package metadata and source pages from the official Debian package infrastructure.
- Arch Linux: the official Arch package index and documented package-search interface.
- Fedora: the official Fedora Packages portal; do not scrape private or undocumented endpoints.
- Flathub: official app listings and publisher/build information where available.
- PaketScope releases: the project's GitHub Releases page, only after a tagged artifact and its checksums have been verified.

The exact endpoint, allowed usage, update frequency, and fields must be validated for each source before enabling automated ingestion. If an official source has no stable public API suitable for the use case, use a clearly documented manual import or omit it rather than depending on brittle HTML scraping.

## Canonical package record

Every package record should carry these fields:

- `sourceId`: stable source identifier, such as `debian`, `arch`, `fedora`, or `flathub`.
- `packageId`: identifier in the source's own namespace; for Flatpak this is the application ID.
- `name` and `summary`: source-provided display metadata.
- `version`: source version, preserving the source's own version semantics.
- `architecture`: architecture or an explicit source-defined architecture scope.
- `repository`: repository/channel/component where the source provides it.
- `homepageUrl`, `sourceUrl`, and `detailsUrl`: verified HTTPS links where available.
- `license`: only when provided by the source and normalized without guessing.
- `lastVerifiedAt`: when the record was checked against the authoritative source.
- `availabilityStatus`: source-specific availability; never use it to imply local installation.

A package's identity is the tuple of source, repository/channel, package ID, and relevant architecture. Names alone are not unique across distributions or repositories.

## Ingestion and refresh model

1. Fetch only from an allowlisted official source adapter.
2. Validate response size, content type, schema, required identity fields, and HTTPS link destinations.
3. Normalize into the canonical record while retaining source identifiers and original detail URLs.
4. Deduplicate only within a source's documented identity rules.
5. Record the retrieval timestamp and fail visibly when an adapter breaks; do not silently publish an empty catalog.
6. Generate static JSON during a controlled build or scheduled workflow. Do not make visitors wait for a third-party API or send their search terms to an external provider.
7. Review metadata changes and run schema, link, freshness, and regression checks before publication.

## Installation safety

The website should link to official package details or release pages, not execute package operations. Never build shell commands from untrusted package metadata. Installation instructions must be distribution-specific, explain the package source, and only be published after the target workflow has been tested.

For PaketScope, a GitHub source archive is not a native RPM, Arch, or openSUSE package. Keep the Debian 13 binary target explicit until additional distributions have their own packaging and test evidence.

## Rollout order

1. Validate each source's documented interface and usage terms.
2. Add the source registry and schema tests.
3. Implement one source adapter at a time, beginning with the source whose interface is most stable.
4. Add freshness reporting and failure handling before scheduling automatic updates.
5. Add website search/filter UI only after representative, validated records exist.

No live cross-distribution package ingestion is enabled by this document alone. Do not label the package directory as complete until adapters, records, freshness checks, and source-specific tests are implemented.
