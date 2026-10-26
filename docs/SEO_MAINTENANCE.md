# SEO and crawlability maintenance

This is a technical/content checklist, not a promise of ranking position. Rankings depend on query intent, useful original content, competition, links/reputation, indexing, and many other factors outside this repository. Never add keyword stuffing, fake ratings/reviews, copied descriptions, or a claim that a page is "number one".

## Canonical source and crawlable routes

- Keep the repository's canonical host consistent: `https://linux-software-lab.vercel.app/`.
- Every indexable public HTML page needs one unique, absolute self-referencing canonical URL, a unique descriptive title, and a concise page-specific meta description.
- The sitemap contains only stable public canonical URLs, including the detail routes generated from `public/data/software.json`. It must not include the admin dashboard, preview URLs, search/filter query URLs, broken routes, or duplicate canonicals.
- `robots.txt` should point to the canonical sitemap. Never rely on robots.txt to protect private content; the admin page also uses `noindex,nofollow,noarchive` and its own authentication/authorization policy.
- Keep titles and descriptions consistent with the actual heading and visible page content. Do not promise a released download for an app whose real artifact is missing.
- Links between the home page, catalogue, detail pages, documentation, source repository, and verified releases should use meaningful anchor text and not be broken.
- Use stable, descriptive URL paths. Do not create duplicate pages for every search query or filter combination.

## Structured metadata

- JSON-LD must be valid JSON and describe the page honestly. Use `WebSite`, `Organization`, `BreadcrumbList`, or a software-specific schema only when the properties match the visible page and actual product state.
- Do not invent ratings, review totals, prices, downloads, software availability, or operating-system compatibility to qualify for a rich result.
- Open Graph and Twitter/X metadata should identify the same canonical page. The current preview artwork is SVG; some social preview consumers may not render SVG consistently. Before relying on large social cards, add a real, locally hosted PNG/JPEG derivative and verify the platform preview. Label concept artwork accurately.
- Alt text should communicate an image's real purpose. Use empty alt text for purely decorative assets and do not treat concept artwork as an actual product screenshot.

## Content usefulness and search intent

- Write original Indonesian descriptions around the actual user problem, the intended audience, supported environment, core workflow, limitations, privacy/security implications, and current release status.
- Give each application a useful, distinct detail page. A thin catalogue card alone is not a substitute for documentation of the actual product.
- Keep release notes, supported OS versions, package formats, checksums, and source links current. Remove obsolete claims instead of adding generic SEO paragraphs.
- Use relevant cross-links to installation docs, architecture, contribution guidance, and upstream source where they help the reader. Avoid unnatural repeated keywords.

## Performance and mobile experience

Measure the deployed site instead of assuming that a static website is automatically fast. Use PageSpeed Insights/Lighthouse for lab diagnostics and Google Search Console's Core Web Vitals report for field data when sufficient real-user data exists.

Google's published "good" Core Web Vitals targets are:
- LCP (loading): at or below 2.5 seconds.
- INP (responsiveness): below 200 milliseconds.
- CLS (visual stability): at or below 0.1.

Treat these as user-experience targets, not a guarantee of top search placement. Check the page at mobile widths, keyboard navigation, readable contrast, image dimensions, layout shifts, font-loading behaviour, and whether search/filtering stays responsive with a larger catalogue.

## Before adding a new app

1. Add one validated record to `public/data/software.json`, a truthful detail page, and real local artwork.
2. Add the canonical URL to `public/sitemap.xml` and verify the same canonical in the HTML.
3. Run `python scripts/validate_catalog.py`, `python scripts/check_site_links.py`, `python scripts/check_docs_links.py`, and `python -m unittest discover -s tests -v`.
4. Ensure the public metadata, Supabase mirror sync mapping, local JSON fallback, details page, launcher metadata, and actual artifacts agree. Search terms must remain client-side.
5. After deployment, verify the production URL, HTTP response, canonical/sitemap reachability, and preview metadata. Submit/inspect the sitemap and indexing status in Search Console where access is available.

## Official references

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google URL structure best practices](https://developers.google.com/search/docs/crawling-indexing/url-structure)
- [Google Core Web Vitals and Search](https://developers.google.com/search/docs/appearance/core-web-vitals)
- [Google page experience guidance](https://developers.google.com/search/docs/appearance/page-experience)
- [Google image SEO best practices](https://developers.google.com/search/docs/appearance/google-images)
