# Software projects

Every product maintained by Linux Software Lab has its own directory under `apps/`. Source code, tests, documentation, licenses, and release packaging for different products must not be mixed together.

## Current projects

- `paketscope/` — native Python/PySide6 desktop application for Linux. The active v3 work lives on the dedicated `feature/paketscope-v3-native` branch until its code and release checks are ready to merge.
- `sorot/` — **Sorot 0.5.0 Beta**, a Linux desktop teleprompter. The folder contains beta distribution archives, a Debian package, checksums, test results, and extension documentation. It is not a stable release; see [`sorot/README.md`](sorot/README.md). Rebranding/documentation updates must not rewrite the existing package artifacts or application payload.

## Expected structure for an implemented application

Each application should keep its project-specific material together, with the actual folders introduced as they are needed:

```text
apps/<application-slug>/
├── README.md          # purpose, install/run instructions, requirements, limitations
├── LICENSE            # license text for this application
├── CHANGELOG.md       # version history, including unreleased changes
├── pyproject.toml     # Python package metadata and dependencies, when applicable
├── <package>/         # application source
├── tests/             # unit and integration tests
├── docs/              # architecture, security, user and developer guides
├── packaging/         # optional project-neutral release helpers
└── debian/            # Debian source-package metadata when .deb packaging is ready
    ├── control
    ├── changelog
    ├── copyright
    ├── rules
    ├── source/format
    └── <other required Debian packaging files>
```

Do not add empty template files merely to make a tree look complete. Add packaging metadata only when it can be validated against the actual project and dependencies. Never present a directory layout as proof that an installable package exists.

## Relationship to the website

The public website lives separately in `public/`. Product pages and catalogue entries describe a project and link to source/releases; the website does not execute or publish the contents of `apps/`. Vercel's `outputDirectory` remains `public`.

New products should have a directory in `apps/`, a detail page under `public/software/`, a metadata entry in `public/data/software.json`, and a sitemap entry. See `docs/SOFTWARE_DIRECTORY_LAYOUT.md` and `docs/ADDING_SOFTWARE.md`.
