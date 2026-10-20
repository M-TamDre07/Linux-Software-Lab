# Adding software to the catalog

Use this checklist for each new item.

## 1. Decide what kind of item it is

Choose a stable lowercase slug with hyphens only, such as `sample-tool`. The catalog `id` and `slug` must match.

Supported types: `desktop`, `web`, `cli`, `library`, `extension`.

Supported states: `planned`, `testing`, `released`, and `archived`.

## 2. Create the files

- Source code belongs in `apps/<slug>/` when it is an application maintained in this repository.
- The public product page belongs in `software/<slug>.html`.
- Original SVG icon and preview artwork belong in `assets/images/`.
- Register all user-facing metadata in `data/software.json`. Do not add card content directly to `site.js`.

The preview `previewAlt` text must accurately describe the image. Concept artwork must be explicitly labelled as concept art.

## 3. Fill every catalog field

Each software entry needs `id`, `slug`, `name`, `version`, `summary`, `description`, `category`, `status`, `type`, `platforms`, `tags`, `keywords`, `features`, `detailUrl`, `sourceUrl`, `releaseUrl`, `icon`, `iconImage`, `previewImage`, `previewAlt`, and `updatedAt`.

Use empty strings for `sourceUrl` or `releaseUrl` when a verified URL does not exist. Do not use a placeholder download link. Release URLs must be HTTPS and the record must have `status: released`.

## 4. Validate before opening a pull request

From the repository root:

~~~bash
python3 scripts/validate_catalog.py
node --check assets/js/site.js
python3 -m unittest discover -s tests -v
~~~

The catalog validator confirms that IDs/slugs are unique, date/status/type fields are valid, local detail pages and SVG files exist, and external links use HTTPS. CI repeats these checks on pushes and pull requests.

## 5. Keep the site light

Prefer optimized local SVG previews and concise descriptions. Do not add trackers, external search APIs, or a database without a specific requirement and a privacy/performance review.
