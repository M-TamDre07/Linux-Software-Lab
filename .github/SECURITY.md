# Security policy

Linux Software Lab is an independent project. The website is a static site; PaketScope is a local Linux desktop application.

## Reporting a suspected vulnerability

Please do not publish exploit details, credentials, package inventories, or personal data in a public issue.

If GitHub's private vulnerability reporting is available for this repository, use **Security → Advisories → Report a vulnerability**. If it is not available, contact the maintainer privately through GitHub and include only the minimum information needed to reproduce the issue safely.

Please include the affected commit or version, the component involved, expected versus observed behaviour, and a minimal reproduction that does not access another person's data or damage a system. Do not include real passwords, tokens, private backups, or system inventory dumps.

## Scope and response

The repository's website is delivered as static files through Vercel; the repository does not implement a PHP server runtime. PaketScope runs locally as a Python/Qt application and can request privileged APT operations only through its explicit confirmation and system-authentication flow.

Reports are triaged as promptly as possible, but no response time or security audit is guaranteed. Until a fix is available, keep the details private and avoid using experimental PaketScope package-mutation flows on a daily-use system.
