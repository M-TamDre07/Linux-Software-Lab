## Purpose
Describe the foundation or behavior change and the problem it solves.

## Change area
- [ ] Architecture or documentation
- [ ] Website, search, or SEO
- [ ] Linux app or OS/distro integration
- [ ] Supabase schema, RLS, or synchronization
- [ ] Release metadata or packaging
- [ ] Security or CI

## Validation
- [ ] `python scripts/validate_catalog.py`
- [ ] `python scripts/check_site_links.py`
- [ ] `python scripts/check_docs_links.py`
- [ ] `python scripts/validate_app_manifest.py` (when application-template files change)
- [ ] `node --check public/assets/js/site.js` (when website JS changes)
- [ ] `python -m unittest discover -s tests -v`
- [ ] App-specific tests/build checks pass for each affected application.
- [ ] Reviewed current GitHub Actions and any relevant Vercel/Supabase result.

## Security and integration review
- [ ] No keys, tokens, credentials, private user data, or production dumps are included.
- [ ] Database changes have a versioned SQL migration in `supabase/migrations/`, least-privilege grants, and reviewed RLS policies.
- [ ] Remote catalogue metadata cannot provide shell commands or privileged operations.
- [ ] New app source is separated from `public/`; no installer/package format is advertised unless a real artifact exists.
- [ ] Release manifests and checksums describe the actual immutable artifact bytes; no test-only/fake downloads are shown.
- [ ] For website content changes, canonical URLs, sitemap entries, metadata, mobile accessibility, and documentation links were reviewed.

## Known limitations / rollback
State anything unverified, the effect on users, and the safe rollback or recovery path.
