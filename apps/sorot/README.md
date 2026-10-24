# Sorot 0.5.0 Beta

Sorot is a desktop teleprompter for Linux. This directory contains the preserved beta distribution artifacts and documentation. The files are relocated byte-for-byte and are not rebuilt as part of the repository reorganization.

> **Beta notice:** Sorot 0.5.0 is not a stable release. Read the test report and known limitations before installing it. The website rebranding does not modify the Debian package or application archives.

## Available artifacts

| Artifact | Purpose |
| --- | --- |
| [`sorot_0.5.0_all.deb`](sorot_0.5.0_all.deb) | Debian package for testing |
| [`sorot-0.5.0.tar.gz`](sorot-0.5.0.tar.gz) | Source archive |
| [`sorot-0.5.0.zip`](sorot-0.5.0.zip) | ZIP source archive |
| [`SHA256SUMS`](SHA256SUMS) | SHA-256 checksums for the three artifacts |
| [`TEST-REPORT.md`](TEST-REPORT.md) | Test results and outstanding validation |
| [`EXTENSIONS.md`](EXTENSIONS.md) | Extension format, API, installation, and security model |

The project has no published GitHub Release entry at the time this document was prepared. The files above are repository artifacts, not a tagged stable release.

## What Sorot provides

Based on the included test report and extension documentation, the beta includes:

- Script editing, opening/saving, undo, drafts, and local snapshots.
- A floating teleprompter overlay with playback controls, pause, speed controls, and duration-oriented playback.
- Script markup for notes and pause cues.
- Declarative extensions for themes, overlay presets, AI tasks, and templates.
- Code extensions that require explicit approval and run in a separate process.
- Optional AI and cloud-storage integrations.

The separate process used for code extensions protects application stability; **it is not a security sandbox**. Approved extension code runs with the user's account permissions and may access files, networks, or subprocesses. Install extensions only from sources you trust.

## Installation

Download the `.deb` package to a local directory, then install it with APT so dependencies can be resolved:

```bash
cd ~/Downloads
sudo apt install ./sorot_0.5.0_all.deb
```

If the package was downloaded to another directory, change to that directory first or provide the full file path. Review the package and its dependencies before confirming installation. To remove the installed package, use the package name shown by the installed package metadata (the test report records the package as `sorot`).

The clean-install workflow on Debian 13 has **not** been verified in the included test report. Do not treat Debian 13 compatibility as confirmed just because a Debian package is provided.

## Test status and limitations

The report dated 2026-10-18 records the following environment and results:

- Ubuntu 24.04 x86_64, Python 3.12.3, PySide6 6.12.0.
- Ruff checks passed; mypy reported no issues across 43 files.
- Pytest: 378 passed, 0 failed, 0 skipped.
- `desktop-file-validate` was clean; Lintian reported one pedantic note and no errors/warnings.
- Two consecutive builds produced identical checksums for the Debian, tar.gz, and ZIP artifacts.

The same report explicitly marks these areas as **not yet tested**:

- Real desktop sessions on GNOME Wayland, KDE Plasma, Xfce, and Cinnamon, including overlay positioning, click-through, multi-monitor, and fullscreen behaviour.
- A clean Debian 13 installation and dependency resolution.
- Real AI providers, rclone/Google Drive, and a real keyring.
- Third-party extensions and screen-reader accessibility.

These results are the supplied project's report, not an independent audit or a guarantee for every Linux environment. See [`TEST-REPORT.md`](TEST-REPORT.md) for the full scope.

## Integrity checks

From this directory, verify an artifact against the provided checksum file:

```bash
sha256sum -c SHA256SUMS
```

Only run the check with the three matching artifact files present in the same directory.

## Open-source contributions

Please read [`EXTENSIONS.md`](EXTENSIONS.md) before developing or installing extensions. For source changes, include reproducible steps, focused tests, and documentation updates. The public website catalog is maintained separately under `public/`; website-only rebranding should not rewrite application binaries, the Debian packaging files, or source archives.
