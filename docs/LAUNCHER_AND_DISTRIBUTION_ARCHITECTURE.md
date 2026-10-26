# Linux Software Lab — unified launcher and distribution architecture

**Status: proposal / implementation contract.** This document guides the launcher and release work. It does not claim that future packages already exist and does not itself publish installers.

## Goal

Make Linux Software Lab approachable to people migrating from Windows while preserving a fast, scriptable workflow for technical users. Every application should appear in the same product catalogue, use the same visual language for its listing, and expose both a graphical installation path and a terminal workflow wherever a compatible package exists.

The planned launcher is a working name, **Linux Software Lab Center**; the final product name can be selected separately. The command-line entry point can be `lsl`. GUI and CLI must call the same metadata, compatibility, download, verification, and install services. They must not maintain separate lists or separate compatibility rules.

## What the uploaded `.flatpak` tells us

The supplied file is a **single-application Flatpak bundle**. Static strings identify app ID `ai.storyteller.artcraft-launcher`, command `artcraft-launcher`, runtime `org.freedesktop.Platform/x86_64/26.08`, a Flathub runtime repository, network/IPC access, X11/Wayland sockets, graphics access, and a `home` filesystem permission. This is useful as an example of a downloadable application bundle, not as a package format that can replace all distro packages.

Flatpak's official documentation says that single-file bundles do not include runtime dependencies or AppStream data and recommends hosting a repository when updates matter. A bundle can be installed using Flatpak, but the machine still needs Flatpak and may need to download the appropriate runtime from a configured repository:
- <https://docs.flatpak.org/en/latest/single-file-bundles.html>
- <https://docs.flatpak.org/en/latest/repositories.html>

The launcher must request only permissions needed for its own function. In particular, don't copy the sample's broad `home` or network permissions without a concrete need. A launcher shipped as a Flatpak is also sandboxed; it must not assume it can run host `apt`, `dnf`, or `pacman` with unrestricted access. Native-package operations need a proper host integration (for example a reviewed PackageKit/polkit adapter) or must be delegated to the host package manager.

## Distribution strategy

Use **native packages plus optional Flatpak delivery**, rather than pretending one file format covers every Linux distribution.

| Distribution family | Native artifact | Installation mechanism |
| --- | --- | --- |
| Debian, Ubuntu and derivatives | `.deb` | APT installs the local package and resolves dependencies |
| Fedora / RHEL family | `.rpm` | DNF installs the local RPM |
| openSUSE / SUSE family | `.rpm` | Zypper installs the local RPM |
| Arch Linux and derivatives | `.pkg.tar.zst` and/or reviewed `PKGBUILD` | Pacman installs a built package; `makepkg` builds a PKGBUILD |
| Desktop-oriented cross-distro option | `.flatpak` or `.flatpakref` when supported by the app and its runtime | Flatpak installs the bundle or reference |
| Portable fallback | `.AppImage` only when the product can safely support it | Download, verify, mark executable, run; do not claim native package-manager integration |
| Source-only / developer path | `.tar.gz` / `.zip` | Document build steps; don't display as a one-click native installer |

Each application may support a different subset of formats. The catalogue must show only artifacts that actually exist, are checksummed, and have been tested for the claim being made. A blank or planned artifact must never generate an install button or terminal install command.

For Sorot, the live state remains 0.5.0 Beta with `.deb`, `.tar.gz`, and `.zip`. Arch Linux for 0.6.0 is a planned target; it must remain labelled **planned** until an actual Arch artifact or reviewed build recipe and its test evidence have been added. PaketScope's source-mode command is not the same thing as a public package release.

## One catalogue; two user experiences

### Graphical launcher

The launcher should provide a searchable catalogue, category/status filters, a product details view, distro compatibility, version and architecture, install scope, release notes, and clear states: `Install`, `Open`, `Update`, `Not available for this distro`, and `Source / Developer options`. A planned package shows its status, not a disabled-looking but fake download.

For a native package install, show the exact package/version and any available transaction plan before asking for authorization. Use the platform's proper privilege mechanism; do not run the entire GUI as root. Provide progress, actionable errors, and a cancel path where the package-manager adapter supports cancellation. Never execute shell text from catalog metadata.

### Terminal client

The CLI uses the same registry, manifest schema, distro detection, checksum verification, and compatibility selection as the GUI. Suggested command shape:

```text
lsl detect
lsl list
lsl info sorot
lsl install sorot
lsl install sorot --version 0.5.0
lsl download sorot
lsl status
lsl doctor
```

These are target commands for the planned launcher, not all current features of a released executable. Unattended/automation mode must be explicit. Use argument arrays, validated artifact identifiers, bounded downloads, timeouts, and clear exit codes. Never allow a catalog field to supply an arbitrary shell command, package-manager executable path, or privilege escalation command.

## Versioned artifact contract

A release manifest lives alongside its real versioned artifacts. The JSON Schema at [`schemas/distribution-manifest.schema.json`](schemas/distribution-manifest.schema.json) defines the shared field contract. Each artifact records:
- a simple filename, exact format, package kind, architecture, HTTPS download URL, and SHA-256;
- an optional signature URL and minimum OS constraint;
- optional install scope where the format supports it.

Install commands are derived from a small trusted adapter map in application code. The manifest cannot carry arbitrary commands. The web catalogue, GUI, CLI, and release validation should all read this same metadata contract.

A SHA-256 digest detects corruption or mismatch against the manifest; **it is not a publisher signature** if the digest and package come from the same mutable source. Before broad public distribution, sign release metadata or artifacts (e.g. with a maintained key or verified signing workflow), define key rotation/revocation, and verify the signature before installation. Keep old version directories immutable for rollback. Never reuse an old directory for a new build.

## Safe installation rules

1. Identify the local distro from `/etc/os-release` in the native launcher/CLI. In a browser, only infer a broad OS family when available and ask the visitor to choose their distro; browser JavaScript cannot reliably inspect the host's `/etc/os-release`.
2. Match the requested product/version to an indexed, non-archived release manifest.
3. Select only a package format explicitly compatible with the distro family and CPU architecture.
4. Validate the manifest, allowlisted HTTPS origin, safe basename, size limit, and SHA-256; verify a publisher signature when signatures are available/required.
5. Clearly show the software name, version/channel, format, source, compatibility status, and any known trust/test caveat before installing.
6. Ask for confirmation. Privileged installation occurs through a narrow host package-manager adapter, never by running the launcher GUI as root.
7. Use the native package manager's normal dependency resolution. Never run `apt autoremove`, bulk-upgrade the system, remove unrelated packages, or silently alter the package set.
8. Report the outcome and where logs/version metadata are stored. Do not declare installation successful until the package manager exits successfully.
9. Treat uninstall, update, rollback, and install as separate operations with their own preview and confirmation.
10. In offline mode, display cached catalogue data with its timestamp, but do not pretend that a stale manifest confirms a current release or revocation status.

## Release and packaging pipeline

A new application needs:
1. an application directory with source, licence, tests, and build metadata;
2. one canonical catalog record and a product detail page using the shared UI pattern in `PRODUCT_UI_STANDARD.md`;
3. a release directory for each version and only the real package formats built for it;
4. platform-specific builds in CI or reproducible build environments;
5. checksum generation and signature verification;
6. tests for installer metadata and clean-install/package-manager behavior on each claimed distro;
7. updates to the shared index and regression checks proving that the website/GUI/CLI all report the same version and availability.

The launcher itself must be packaged and tested on each supported family. Until then, its source should be labelled a development preview, not a downloadable one-click installer.

## Implementation sequence

- **Phase 1 — metadata and product availability:** adopt the schema, keep website metadata in sync with version manifests, and add cross-platform compatibility tests. Current Sorot metadata is the initial real artifact example.
- **Phase 2 — shared CLI core:** distro/architecture detection, list/info, artifact selection, bounded downloads, checksum/signature verification, and clear terminal output.
- **Phase 3 — GUI over the same core:** search/cards/details and install/download actions, with testable state mapping rather than duplicated install logic.
- **Phase 4 — package-manager adapters:** Debian/Ubuntu, Fedora/RHEL, SUSE, and Arch; use per-distro clean-install CI or dedicated test machines. Don't advertise a family before it is verified.
- **Phase 5 — launcher packaging:** publish the launcher itself in supported native formats; consider Flatpak only for the use cases that fit its sandbox/host-integration model.
- **Phase 6 — release readiness:** signed release metadata, update and rollback behavior, accessibility review, and beginner-focused user testing.

## Acceptance criteria

- GUI and CLI show the same available versions, formats, checksums, and distro status.
- Every displayed installation action points to a real artifact in a validated release manifest.
- Unknown distro/architecture results in a clear unsupported/choose-distro message; it never falls back to installing another family's package.
- CI catches catalogue/manifest drift, stale URLs, invalid digests, architecture mismatch, shell-command metadata, and false claims about planned releases.
- The existing approved application-list/card and product detail UI stays consistent as new apps are added.
