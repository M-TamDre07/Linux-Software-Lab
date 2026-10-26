# {{APP_NAME}}

> **Generated scaffold — not a working application or a release.** The maintainer must choose a runtime, licence, dependency policy, application entry point, supported distributions, and release policy before this project can be built or published.

## Identity

- **Stable slug:** `{{APP_SLUG}}`
- **Purpose:** {{APP_DESCRIPTION}}
- **Lifecycle:** planned
- **Canonical source folder:** `apps/{{APP_SLUG}}/`
- **Future catalogue detail route:** `/software/{{APP_SLUG}}.html`

## Standard layout

```text
apps/{{APP_SLUG}}/
├── README.md
├── application.json
├── CHANGELOG.md
├── LICENSE-REQUIRED.md
├── .gitignore
├── src/                      # Runtime-specific implementation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── SECURITY.md
│   └── RELEASES.md
├── assets/
│   ├── icons/
│   ├── screenshots/
│   └── fixtures/
├── packaging/
│   ├── debian/
│   ├── rpm/
│   ├── arch/
│   ├── flatpak/
│   └── appimage/
└── releases/
    └── README.md
```

The `application.json` contract is validated against `application.schema.json` before integration. The top-level layout is shared across products. Technology-specific files belong inside `src/` or the relevant packaging directory. A directory does not claim that its runtime or package format is supported: the included packaging READMEs remain explicit placeholders until a real build and clean-install test exist.

## Getting from scaffold to integrated application

1. Choose a licence and runtime, then document the supported OS families and minimum versions in `application.json` and `docs/ARCHITECTURE.md`.
2. Implement the app in `src/`; add unit, integration, and security regression tests. Do not add secrets, generated environments, local caches, or real user data to Git.
3. Write setup, run, recovery, and troubleshooting instructions in `docs/DEVELOPMENT.md`. Every user-facing error should explain what happened, whether the system changed, and the safe next step.
4. Add a CI workflow that installs pinned dependencies and runs the project's real lint, build, and test commands. The base template intentionally does not invent a framework or fake passing test.
5. Add a product page under `public/software/`, a validated record in `public/data/software.json`, local artwork, and the canonical URL in `public/sitemap.xml`. Keep the GitHub repository as the source of truth.
6. Add actual immutable artifacts under `releases/<version>/`, with a release manifest and SHA-256 file only after the build has completed. A checksum is integrity metadata, not a publisher signature.
7. Add a launcher integration only through the reviewed local allowlist. Never derive a local command from catalogue JSON.
8. Run the repository checks and the app's own tests; submit a pull request for review.

See [Adding software](../../docs/ADDING_SOFTWARE.md), [the directory contract](../../docs/SOFTWARE_DIRECTORY_LAYOUT.md), and [the launcher trust boundary](../../docs/APP_CONTAINER_AND_INTEGRATIONS.md).
