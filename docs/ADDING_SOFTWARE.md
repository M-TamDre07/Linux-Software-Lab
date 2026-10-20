# Adding software to the catalog

Use this checklist for each application, command-line tool, web app, library, or extension.

## 1. Choose an identity and honest status

Use a stable lowercase slug containing letters, numbers, and single hyphens, such as sample-tool. The id, slug, and detailUrl must match.

Supported types: desktop, web, cli, library, extension.

Supported statuses:
- planned: proposed, not yet a usable implementation.
- testing: implementation is being tested and is not a stable release.
- released: a real, verified HTTPS release URL exists.
- archived: no longer actively maintained.

## 2. Create the files in the right place

- Source code maintained in this repository: apps/<slug>/.
- Public product page: public/software/<slug>.html.
- Original icon and preview artwork: public/assets/images/.
- Single source of catalogue metadata: public/data/software.json.

Do not put application cards directly into JavaScript. public/data/software.schema.json describes the expected metadata contract; scripts/validate_catalog.py enforces the principal field and safety rules.

## 3. Complete the metadata

Every record must include id, slug, name, version, summary, description, category, status, type, platforms, tags, keywords, features, detailUrl, sourceUrl, releaseUrl, icon, iconImage, previewImage, previewAlt, and updatedAt.

Use an empty string for sourceUrl or releaseUrl if the verified URL is not available. Non-empty external links must use HTTPS. A record marked released must have a valid HTTPS releaseUrl; an unreleased project must not advertise a release URL. Concept artwork must be accurately labelled in previewAlt.

## 4. Update discovery and SEO metadata

Add the page's canonical URL to public/sitemap.xml. public/robots.txt should continue to point to the canonical sitemap. The CI link/sitemap check verifies that every catalogue detail route appears in the sitemap, the sitemap host matches the home canonical host, and each listed page has a matching canonical URL. Therefore, a new detail page without a matching sitemap entry will fail validation.

## 5. Validate before pull request

Run from repository root:

~~~bash
python scripts/validate_catalog.py
python scripts/check_site_links.py
node --check public/assets/js/site.js
python -m json.tool public/data/software.json > /dev/null
python -m json.tool public/data/software.schema.json > /dev/null
python -m json.tool vercel.json > /dev/null
python -m unittest discover -s tests -v
~~~

GitHub Actions repeats the checks. Fix validation failures rather than bypassing the workflow.

## 6. Keep the catalogue light and private

Use concise descriptions and optimized local SVG or raster assets. Search is client-side and the site has no analytics endpoint. Do not add trackers, remote search APIs, third-party scripts, or database dependencies without a concrete requirement and privacy/performance review.
