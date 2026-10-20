# Website architecture

Linux Software Lab is a static-first website. The goal is to keep it inexpensive to host, fast to deliver, easy to audit, and able to list many projects without introducing a database or search service before one is needed.

## Directory map

- `index.html` — landing page and a compact catalog view.
- `software/index.html` — dedicated searchable software directory.
- `software/<slug>.html` — product detail page with release and status information.
- `data/software.json` — single source of truth for catalog cards and search metadata.
- `data/software.schema.json` — versioned metadata contract for tools and editors.
- `assets/css/site.css` — design tokens, layout, themes, responsive and accessible components.
- `assets/js/site.js` — navigation/theme and client-side catalog search, filtering, sort, URL state, and pagination.
- `assets/images/` — original icons and concept preview artwork.
- `apps/<slug>/` — application source code. This is not the website directory.
- `scripts/validate_catalog.py` — schema/asset/link checks run before deployment.
- `.github/workflows/` — automated catalog quality and application tests.
- `docs/` — contribution, architecture, and deployment guidance.

## Data flow

1. A maintainer edits one entry in `data/software.json`.
2. The validator checks required metadata, unique IDs/slugs, supported states, dates, links, and local image/detail files.
3. CI runs the validator and a JavaScript syntax check.
4. Pages read the JSON from the same origin. Search and filters run in the browser; search strings are not sent to an external search API.
5. The UI renders a small page of results at a time. URL query parameters preserve a shareable search/filter state.

## Scaling decisions

The first implementation supports a growing static catalog without a server or database. Category and platform filter options are derived from the data, not hard-coded. Search indexing is prepared once after loading. Only 12 cards are rendered at first and more are appended on demand.

For much larger catalogs, review payload size and browser performance using real measurements before introducing a generated search index, static build generator, database, or external search product. Do not add an external service just because the catalog gains its first few dozen entries.

## Truthful metadata

- Use `planned` for an idea without a usable implementation.
- Use `testing` for an implementation that is not ready for a stable release.
- Use `released` only when a real, verified release link exists.
- Use `archived` for software that is no longer actively maintained.
- Do not imply a concept image is a screenshot of a released app.
- Do not advertise platform compatibility without testing it.
