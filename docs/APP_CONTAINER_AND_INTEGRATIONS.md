# Linux Software Lab Center: app container and integrations

## Launcher portal and local diagnostics

The desktop GUI links to the public `/launcher/` portal so users can move from local application discovery to ecosystem documentation without guessing a URL. The CLI offers `lsl ecosystem` and `lsl ecosystem --json` to report canonical links, the active local catalogue source, local distro/architecture, reviewed local integration IDs, and the adapter availability advertised by the current implementation.

This is a local diagnostic command. It intentionally does not claim that GitHub, Vercel, or Supabase is currently reachable, and it performs no network probe or system mutation. “Detected application” means a registered local executable is found; it does not prove that the app works correctly or is installed by a particular package manager.

## The meaning of “container”

Linux Software Lab Center is an **application hub and catalogue**: it brings the projects in Linux Software Lab into one searchable desktop interface, shows their real release state, and connects each entry to its website page, GitHub source directory, and version manifest.

It is not a Docker/OCI runtime, a virtual machine, or a security sandbox. An installed application remains installed through its own native package manager or its supported distribution mechanism. Flatpak isolation, where a product supports it, remains a separate format and must not be implied by the launcher.

## Shared source of truth

The GitHub repository is the canonical maintained source. The website and launcher consume the same committed metadata, while the website remains a static publication from `public/`.

```text
GitHub main
  ├── public/data/software.json
  │     Product identity, description, status, features, website/source links
  ├── public/data/distribution-index.json
  │     Distribution guidance and pointers to real version manifests
  ├── apps/<slug>/releases/<version>/release.json
  │     Version-specific artifacts and SHA-256 digests
  └── apps/<slug>/
        Application source, tests, docs, and packaging
           │
           ├── Website: product pages and catalogue UI
           └── Launcher: validated snapshot → offline cache → GUI + CLI
```

The launcher refreshes from the canonical GitHub URLs, validates the catalogue/index/manifests, and activates a complete cache snapshot rather than replacing individual metadata files mid-refresh. If refresh fails, the previous valid snapshot remains available. The bundled catalogue supports first launch and offline use.

The product detail page is the human-friendly place to read the overview; the source link points to the project directory; the manifest link provides the version's artifact record. These links are navigation aids, not proof that a release is signed.

## Two trust boundaries

### Remote catalogue data

GitHub JSON may describe product names, categories, features, status, URLs, formats, and digests within a validated contract. It must not contain arbitrary shell commands, executable paths, privilege commands, or package-manager invocations. Install behavior is selected by reviewed application code based on a validated artifact format and the detected local distribution.

SHA-256 verifies that downloaded bytes match the digest in the retrieved metadata. When both are retrieved from the same mutable source, this does **not** prove publisher identity. Signed release metadata/artifacts and key rotation/revocation policy remain release-readiness requirements.

### Local application actions

The launcher uses `lsl_center/integrations.py` as a small allowlist connecting known catalog IDs to executable names that have been reviewed in source code. A GitHub catalog change cannot cause the launcher to execute an arbitrary command. The same local resolver is used by the GUI and CLI to determine whether a known application can be opened.

This creates a deliberate separation:

- **Catalog registry:** which products exist and what the website says about them.
- **Release registry:** which real versioned artifacts are available.
- **Local integration registry:** which local actions (such as opening an installed application) are enabled by reviewed code.
- **Package adapter:** how an approved native artifact is installed on the current distro.

A new product can appear in the catalogue and link to its website/source before a local open integration or install adapter exists. The launcher must show the limitation honestly rather than guessing an executable or package format.

## Adding an application

1. Add or update the product in `public/data/software.json` and keep its detail page, icon, accessibility text, and sitemap entry aligned with the existing website UI contract.
2. Add real versioned artifacts only under `apps/<slug>/releases/<version>/`; validate the release manifest and `SHA256SUMS`. Do not invent formats or reuse old version directories.
3. Add the version-manifest pointer to `public/data/distribution-index.json` only when the manifest exists and passes validation. For Sorot, `apps/sorot/releases/index.json` is the sole manually maintained version list; `scripts/sync_distribution_index.py` derives the displayed version label in both `public/data/software.json` and the launcher's bundled `catalog.json`, alongside the website/launcher distribution indexes.
4. Keep the launcher’s bundled copies and tests synchronized with the website sources. The CI drift checks should fail if the sources disagree.
5. If the product should be opened from the launcher, add a reviewed, fixed executable candidate to `lsl_center/integrations.py` and tests. Never add a `command` or `exec` property to catalog JSON.
6. Enable a new native installer only after implementing its adapter and tests for the relevant distro. Until then, showing the product and linking to its official page/source is valid; pretending it is one-click installable is not.

## Readiness boundary

The current launcher remains a development preview. Successful unit tests and metadata validation do not replace clean-install tests on real/disposable Debian, Fedora, SUSE, and Arch environments. Broad public installation should wait for signed release metadata/artifacts, a reviewed signing-key lifecycle, package integrity/reproducibility checks, and end-to-end installation tests for each distro that is claimed as supported.
