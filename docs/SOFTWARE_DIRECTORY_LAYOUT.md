# Software directory and release layout

Linux Software Lab separates the **website** from each **software product**.

## Repository map

```text
repository/
├── public/                         # Only website output deployed to Vercel
│   ├── index.html
│   ├── assets/
│   ├── data/software.json          # Catalogue source of truth
│   └── software/
│       ├── index.html
│       ├── paketscope.html         # Public product information
│       └── sorot.html
├── apps/                           # Source projects, isolated per application
│   ├── README.md
│   ├── paketscope/                 # Native desktop software, active v3 branch
│   │   ├── README.md
│   │   ├── LICENSE
│   │   ├── pyproject.toml
│   │   ├── paketscope/
│   │   ├── tests/
│   │   └── docs/
│   └── sorot/                          # Sorot 0.5.0 Beta distribution artifacts and docs
│       └── README.md
├── scripts/                        # Website/catalog validators
├── tests/                          # Website regression tests
├── docs/                           # Repository-level project/deployment guides
└── vercel.json                     # Serves public/ only
```

PaketScope 3 source is present in the default branch and the website catalogue currently labels version 3.0.0.dev4 as testing. It remains a development preview, not a stable release.

## Rules for adding an application

- Use a stable lowercase product slug for `apps/<slug>/` and `public/software/<slug>.html`.
- Keep each product's code, tests, docs, license, dependencies, changelog, and packaging files inside its own directory wherever possible.
- Do not reuse a license file from another product without an explicit licensing decision.
- Keep public catalogue content in `public/data/software.json`; do not hard-code product cards into website JavaScript.
- Keep Vercel's static output set to `public/`. Application source, packaging metadata, tests, and private maintainer notes must not be published as site assets.
- Mark planned, testing, released, and archived status honestly. A release URL must point to a real, verified release artifact.

## Debian package directory

When PaketScope is ready for distribution as a Debian package, a `debian/` directory will be prepared within `apps/paketscope/`. Depending on the chosen packaging method, this normally includes a valid `control` file, `changelog`, `copyright`, executable `rules`, and `source/format`, plus any applicable install/service/desktop metadata. Those files must be written against the actual package structure, dependency policy, target distributions, and lifecycle requirements—not copied as untested boilerplate.

Before advertising a `.deb`:
1. Build it in a clean Debian-compatible environment.
2. Inspect package metadata and contents.
3. Test install, launch, upgrade, and uninstall in a disposable environment.
4. Verify dependencies and that no application state is removed unexpectedly.
5. Publish SHA-256 checksums and a clear versioned changelog.
6. Define a trusted signing/repository plan before publishing an APT repository.

The website should display installation commands only after the corresponding artifact and instructions pass those checks.
