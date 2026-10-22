# Security maintenance checklist

This is an operational checklist, not a claim that the project has passed an independent audit.

## Website and HTTPS

- The Vercel project publishes only `public/`; it is not configured as a PHP application in this repository.
- Vercel manages TLS certificates for assigned, verified domains. Verify the domain is assigned to the intended project and that production deployments are reachable over HTTPS in the Vercel dashboard.
- `vercel.json` sets HSTS, a restrictive Content Security Policy, anti-framing protections, and baseline browser security headers. Do not enable HSTS `includeSubDomains` or `preload` unless every affected subdomain has been checked.
- The site uses external Google Fonts stylesheets, but no inline script or inline style is required. CI guards this assumption before the CSP is tightened.

## Dependency and source scanning

- The PaketScope CI workflow runs unit tests, Ruff checks, compilation, and `pip-audit --strict` against the resolved Python environment.
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
