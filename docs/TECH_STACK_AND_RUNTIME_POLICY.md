# Technology and runtime policy

This policy records the current boundaries. It is not a mandate to use one framework for every future application.

## Website and search

- **Current stack:** static HTML, shared CSS, vanilla JavaScript, and JSON metadata. Vercel publishes only `public/` from the repository root.
- **Why no SPA framework by default:** the current site is content-oriented and small enough for static publication. Avoid adding a build framework, client router, or dependency graph without a measurable requirement that existing HTML/JS cannot meet.
- **Search model:** the browser builds a searchable index once from the validated catalogue. Search, ranking, filters, sorting, pagination, and URL state remain client-side; user query text is never sent to Supabase.
- **Fallback:** fetch public rows from the Supabase mirror, validate them, and fall back to same-origin `/data/software.json`. Show users a visible status when fallback is active or both sources fail.
- **Security headers:** the Content Security Policy in `vercel.json` intentionally restricts scripts and connections. New external services need a narrowly scoped policy update and review, not a wildcard.

## Native desktop applications

- **Current stack:** Python and PySide6 are used by Linux Software Lab Center and other native applications. Each product owns its own `pyproject.toml`, lock/dependency policy, entry points, tests, and packaging.
- **No shared-runtime assumption:** a product can choose another appropriate technology. Explain that decision, expected footprint, supported OS versions, dependency maintenance, and packaging implications in its architecture guide before implementation.
- **GUI and CLI parity:** where a product has both, use one shared core for parsing, validation, OS detection, compatibility policy, and privileged operations. Presentation code must not re-implement security decisions.
- **Framework gate:** before adding a framework, list the user problem it solves, project impact, licensing, maintenance cadence, upgrade strategy, bundle/runtime size, and test strategy. Keep the current dependency-free static website dependency-free unless evidence justifies a change.

## Rust adoption

Rust is an approved option for focused systems components, not a blanket replacement for Python, PySide6, or the website stack. Existing applications retain their current implementation unless a documented requirement and measurable benefit justify a bounded Rust component.

The proposed first candidate is an isolated platform-core pilot for Linux Software Lab Center, covering deterministic OS/architecture detection and compatibility decisions only after the existing Python behavior has contract tests. The pilot must preserve one metadata source of truth, use a versioned interface, and prove parity before any production integration. It must not introduce a second package-manager implementation or bypass Polkit.

Keep Rust out of the production runtime until its stable toolchain, MSRV, dependencies, security tests, Debian packaging, and target architecture matrix are documented. The target sequence is Debian 13 amd64 first, then Debian 13 arm64; other distributions require separate native adapter and lifecycle evidence.

See [Rust Adoption Strategy](RUST_ADOPTION_STRATEGY.md) for the phased plan, interface constraints, test gates, and explicit non-goals.

## Operating-system support contract

- Read the real machine's OS identity locally. On Linux, use `/etc/os-release` for distro ID, version, and ID_LIKE; use the OS runtime identity separately so a missing file does not mean "not Linux".
- Normalise CPU architecture aliases but preserve unknown values so packages fail closed if no matching artifact exists.
- Use a reviewed distribution-family adapter map. A recognised family is not the same as a supported installer: each package adapter must have implementation, unit tests, and clean install/upgrade/removal validation before it can be enabled.
- Never infer an exact Linux distro from browser user-agent or offer a package from a different family as a fallback.
- When detection is incomplete, say what was detected and what could not be determined, then disable unsafe installation rather than guessing.

## Backend and data access

- **Source of truth:** reviewed GitHub files and immutable release artifacts.
- **Supabase:** public catalogue mirror with explicit table grants and Row Level Security; admin access is a separate authenticated membership policy. The public browser uses only the publishable key.
- **SQL:** migrations are versioned in Git. Never concatenate arbitrary user input into SQL. Use PostgREST query parameters with validated identifiers, database parameters, least privilege, and row policies. Treat browser-side validation as usability, not an authorization boundary.
- **Vercel:** static output only for the website. Native desktop application directories must never be published as a website root or treated as a server application.

## Quality gates for any app or stack change

1. Record the architecture, runtime, OS/architecture support, data flow, and trust boundaries.
2. Include unit, integration, and security regression tests that exercise invalid input and failure recovery.
3. Pin runtime/dependencies or commit the lockfile, use a supported runtime, and audit dependencies that actually exist.
4. Build and package from a clean environment. Test on the declared OS/distro and verify checksums/signatures only according to a real documented process.
5. Check the application manifest, catalogue schema, product page, navigation, canonical URLs, sitemap, and accessibility/error states.
6. Run relevant GitHub Actions and review Vercel/Supabase status separately; green unit tests do not prove that the remote service or deployment is healthy. Before a catalogue release, also run `python scripts/check_live_integrations.py` or the `Live integration integrity` workflow to compare production Vercel and Supabase with the canonical GitHub source.
