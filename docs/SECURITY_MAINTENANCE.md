# Security maintenance checklist

This is an operational checklist, not a claim that the project has passed an independent audit.

## Website and HTTPS

- The Vercel project publishes only `public/`; it is not configured as a PHP application in this repository.
- Vercel manages TLS certificates for assigned, verified domains. Verify the domain is assigned to the intended project and that production deployments are reachable over HTTPS in the Vercel dashboard.
- `vercel.json` sets HSTS, a restrictive Content Security Policy, anti-framing protections, and baseline browser security headers. Do not enable HSTS `includeSubDomains` or `preload` unless every affected subdomain has been checked.
- The site uses external Google Fonts stylesheets, but no inline script or inline style is required. CI guards this assumption before the CSP is tightened.

## Node.js runtime

- The Vercel project is configured for Node.js `24.x`. The website is statically published, but CI also uses Node.js to validate its JavaScript.
- The site-quality workflow follows the current `24.x` patch line so security fixes arrive without pinning CI to a stale patch. Review the official Node.js security announcements whenever the project is maintained.
- The repository currently has no npm package manifest or npm lockfile, so `npm audit` is not a meaningful dependency check until npm dependencies are introduced. If dependencies are added, commit a lockfile and add a dependency audit to CI.

## Supabase database

- The `Linux-Software-Lab` Supabase project was initialized on 2026-10-22. During the initial review it had no application tables, no user-created Storage buckets, and no migration history. Do not treat an empty database as a backup of the website: static website source and release artifacts must also be backed up in Git and/or an independent artifact archive.
- The database has an `ensure_rls` DDL event trigger which calls `public.rls_auto_enable()`. It remains enabled after the security fix. This function automatically enables RLS on new tables in `public`; **RLS being enabled does not create access policies**. Every future table still needs explicit, reviewed policies appropriate to its data and access model.
- Migration `20261022164925_revoke_public_execute_rls_auto_enable.sql` revokes direct function execution from `PUBLIC`, `anon`, `authenticated`, and `service_role`. It does not drop or disable the event trigger. Keep database changes in versioned migrations and re-run the Supabase Security Advisor after schema updates.
- Verify the configured backup/export mechanism and perform a restore test before storing production data. Supabase backup availability depends on the plan; database backups do not include the contents of Storage buckets. Keep an independent off-site export where the plan does not provide suitable backups.

## Dependency and source scanning

- The PaketScope CI workflow runs unit tests, Ruff checks, compilation, and `pip-audit --strict` against a pinned snapshot of resolved non-editable Python dependencies. The local editable PaketScope project is explicitly excluded from the external package index audit.
- Dependabot checks Python package metadata and GitHub Actions updates weekly. Review update PRs; do not merge solely because a bot proposed them.
- CodeQL analyzes the JavaScript website and Python desktop application on pushes, pull requests, and a weekly schedule.
- The Debian 13 packaging job refreshes repository metadata, then builds, installs, smoke-tests, and purges the development package in a clean container.

## Incident applicability

- The PHP advisories CVE-2026-109618 and CVE-2026-109619 require remediation of vulnerable PHP runtimes or products that bundle PHP. The current repository has no PHP application or PHP dependency manifest. Do not make an arbitrary PHP version change to the Python desktop application; confirm the hosting/runtime inventory if the deployment architecture changes.
- The Python and JavaScript code still needs its own dependency and source analysis. A green CI run does not prove that an application is free of security vulnerabilities.
- A valid HTTPS certificate encrypts the connection and authenticates the domain; it does not replace code review, dependency patching, server-side configuration checks, or incident monitoring.

## Before publishing a stable PaketScope release

- Test the GUI, polkit cancellation, failure recovery, and package operations on a real Debian 13 desktop or disposable VM.
- Review the resolved dependency audit and all findings, including false positives or unfixable transitive dependencies.
- Verify checksums, signatures/provenance, package metadata, and the actual release source.
- Keep the app labelled a development preview until desktop validation and independent review are complete.
