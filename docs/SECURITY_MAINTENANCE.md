# Security maintenance checklist

This is an operational checklist, not a claim that the project has passed an independent audit.

## Website and HTTPS

- The Vercel project publishes only `public/`; it is not configured as a PHP application in this repository.
- Vercel manages TLS certificates for assigned, verified domains. Verify the domain is assigned to the intended project and that production deployments are reachable over HTTPS in the Vercel dashboard.
- `vercel.json` sets HSTS, a restrictive Content Security Policy, anti-framing protections, and baseline browser security headers. Do not enable HSTS `includeSubDomains` or `preload` unless every affected subdomain has been checked.
- The site uses external Google Fonts stylesheets, but no inline script or inline style is required. CI guards this assumption before the CSP is tightened.

## Node.js runtime

- The Vercel project is configured for Node.js `24.x`. The website is statically published, but CI also uses Node.js to validate its JavaScript.
- The site-quality workflow uses Node.js `24.x` with `check-latest: true`, so a stale runner cache cannot silently keep CI on an older patch. Verify the exact version in the workflow log after a runtime update.
- The repository currently has no npm package manifest or npm lockfile, so `npm audit` is not a meaningful dependency check until npm dependencies are introduced. If dependencies are added, commit a lockfile and add a dependency audit to CI.

## Supabase database

- The `Linux-Software-Lab` Supabase project was initialized on 2026-10-22. A live read-only audit on 2026-10-27 found two public tables (`software_catalog` and `lsl_admin_users`) and three applied migrations. Migration history must be tracked in `supabase/migrations/` in Git as well as in the database; a migration applied directly to the database but missing from Git is source-control drift and must be reconciled before future schema changes. Static website source and release artifacts still need Git and/or independent artifact backups.
- The database has an `ensure_rls` DDL event trigger which calls `public.rls_auto_enable()`. It remains enabled after the security fix. This function automatically enables RLS on new tables in `public`; **RLS being enabled does not create access policies**. Every future table still needs explicit, reviewed policies appropriate to its data and access model.
- Migration `20261022164925_revoke_public_execute_rls_auto_enable.sql` revokes direct function execution from `PUBLIC`, `anon`, `authenticated`, and `service_role`. It does not drop or disable the event trigger. Keep database changes in versioned migrations and re-run the Supabase Security Advisor after schema updates.
- Verify the configured backup/export mechanism and perform a restore test before storing production data. Supabase backup availability depends on the plan; database backups do not include the contents of Storage buckets. Keep an independent off-site export where the plan does not provide suitable backups.

## Foundation audit snapshot — 2026-10-27

The live project was inspected without changing schema or data:

- `public.software_catalog`: RLS enabled; anonymous role has SELECT only for rows where `published IS TRUE`.
- `public.lsl_admin_users`: RLS enabled; public and anonymous table access are revoked. Authenticated users can only read their own membership row. Admin catalogue reads require an active membership row.
- A role-scoped SQL probe observed two published catalogue rows and zero unpublished rows as `anon`; a read of the admin registry was denied. Under `authenticated` without a valid user identity, RLS returned no admin or catalogue rows. The admin membership table currently contains zero rows, so no user is provisioned as a dashboard administrator yet; that is a deliberate fail-closed state until the owner creates a reviewed membership through trusted Supabase Dashboard access. Do not seed a default admin or permit self-registration into the admin table.
- Supabase Security Advisor returned no security lints at the time of the audit. The performance advisor reported the published-order index had not yet been used, which is not sufficient evidence to drop it while the catalogue contains only a few rows.
- A read-only SQL literal probe evaluated the injection-shaped value `x' OR '1'='1` as a literal under the `anon` role and matched zero catalogue rows; an explicit privilege check confirmed that `anon` has no SELECT grant on the admin registry. Automated sync tests also reject quotes, semicolons, spaces, path traversal, and duplicate IDs before building the fixed PostgREST stale-row filter. This verifies these specific input paths; it is not a full HTTP fuzzing campaign or proof that every input path is secure.
- This was a configuration/RLS audit and safe regression check, **not** an independent penetration test. Keep malicious-input cases as unit/regression tests; never run destructive injection payloads against production.
- The website's latest production deployment was verified as `READY` on the merged GitHub `main` commit. The separate Vercel project `paketscope` still reports failed deployments because it is configured like a web application despite PaketScope being a native desktop app. Review and disconnect that project's Git integration manually in Vercel only after confirming it is not needed; do not change the website project's connection.

## Dependency and source scanning

- The PaketScope CI workflow runs unit tests, Ruff checks, compilation, and `pip-audit --strict` against a pinned snapshot of resolved non-editable Python dependencies. The local editable PaketScope project is explicitly excluded from the external package index audit.
- Dependabot checks Python package metadata and GitHub Actions updates weekly. Review update PRs; do not merge solely because a bot proposed them.
- CodeQL analyzes the JavaScript website and Python desktop application on pushes, pull requests, and a weekly schedule.
- The Debian 13 packaging job refreshes repository metadata, then builds, installs, smoke-tests, and purges the development package in a clean container.

## PaketScope System & Code Lab

- The ordinary system snapshot uses local read-only APIs and a fixed systemctl list-units command. It exposes only summary fields and bounded samples; it does not change services, mounts, or files.
- The Code Inspector only processes the local file/folder explicitly chosen by the user. It never executes inspected code or uploads source. It applies file, directory, depth, and byte caps, does not follow symlinks, skips common build/cache trees, and skips conventional credential/key filenames. No heuristic can identify every possible secret; users should select projects they are authorized to inspect.
- The source viewer displays text only in a read-only Qt widget. Binary inspection currently identifies ELF class/architecture and a bounded SHA-256 hash; it does not claim to decompile binaries or reproduce a full reverse-engineering suite.
- Administrator inspection is optional and session-only. The user must enable it in the UI, confirm each metadata scan, and complete a Polkit authorization. It invokes only a fixed action in a root-owned helper installed at /usr/lib/python3/dist-packages/paketscope/admin_helper.py.
- The privileged helper accepts no user-supplied filesystem path or shell command. It lists metadata only under /etc, /boot, /usr/local, and /opt, with depth/entry limits; common sensitive paths and key filenames are excluded. It does not read file contents or make changes.
- The helper intentionally refuses to run from a source checkout or virtual environment. Do not start the main GUI with sudo or as root to get more access. The current trusted helper path and .deb behavior still require live Debian 13 desktop validation before a stable release.

## Incident applicability

- The PHP advisories CVE-2026-109618 and CVE-2026-109619 require remediation of vulnerable PHP runtimes or products that bundle PHP. The current repository has no PHP application or PHP dependency manifest. Do not make an arbitrary PHP version change to the Python desktop application; confirm the hosting/runtime inventory if the deployment architecture changes.
- The Python and JavaScript code still needs its own dependency and source analysis. A green CI run does not prove that an application is free of security vulnerabilities.
- A valid HTTPS certificate encrypts the connection and authenticates the domain; it does not replace code review, dependency patching, server-side configuration checks, or incident monitoring.

## Before publishing a stable PaketScope release

- Test the GUI, polkit cancellation, failure recovery, and package operations on a real Debian 13 desktop or disposable VM.
- Review the resolved dependency audit and all findings, including false positives or unfixable transitive dependencies.
- Verify checksums, signatures/provenance, package metadata, and the actual release source.
- Keep the app labelled a development preview until desktop validation and independent review are complete.
