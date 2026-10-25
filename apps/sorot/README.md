# Sorot

Sorot is a native Linux desktop teleprompter. Its existing interface, text workflow, playback behavior, and extension ecosystem are maintained incrementally; this repository does not treat a new release as a reason to redesign the UI/UX.

## Current archived version

The repository currently contains **Sorot 0.5.0 Beta** as an immutable audit/release candidate. It is not a stable release.

- [Release notes and status](releases/0.5.0/RELEASE-NOTES.md)
- [Debian package](releases/0.5.0/sorot_0.5.0_all.deb)
- [Source archive (tar.gz)](releases/0.5.0/sorot-0.5.0.tar.gz)
- [Source archive (ZIP)](releases/0.5.0/sorot-0.5.0.zip)
- [SHA-256 checksum file](releases/0.5.0/SHA256SUMS)
- [Machine-readable version manifest](releases/0.5.0/release.json)
- [Version-specific test report](releases/0.5.0/TEST-REPORT.md)
- [Version-specific release readiness report](releases/0.5.0/RELEASE_READINESS.md)

See [the version archive index](releases/README.md) for how versions are kept side-by-side and how to verify their artifacts.

## What Sorot provides

Based on the included 0.5.0 Beta test report and extension documentation, the archived beta includes:

- Script editing, opening/saving, undo, drafts, and local snapshots.
- A floating teleprompter overlay with playback controls, pause, speed controls, and duration-oriented playback.
- Script markup for notes and pause cues.
- Declarative extensions for themes, overlay presets, AI tasks, and templates.
- Code extensions that require explicit approval and run in a separate process.
- Optional AI and cloud-storage integrations.

The separate process used for code extensions protects application stability; **it is not a security sandbox**. Approved extension code runs with the user's account permissions and may access files, networks, or subprocesses. Install extensions only from sources you trust.

## Installation

Download the Debian package for the version you intend to use, then install it with APT so dependencies can be resolved. For example, from a downloaded 0.5.0 package file:

~~~bash
sudo apt install ./sorot_0.5.0_all.deb
~~~

For a move back to an older version, first select that version's directory, verify its SHA-256 checksums, back up scripts and other important data, and install its package. If APT blocks a downgrade, use the explicit downgrade option:

~~~bash
sudo apt install --allow-downgrades ./sorot_0.5.8_all.deb
~~~

The name 0.5.8 in this example illustrates a possible future version; it is not currently included in this archive. Avoid removing user configuration with package purge commands when the intent is only to change application versions.

The source tar.gz and ZIP archives are version-specific snapshots for reviewing or building the application source. They are not guaranteed to include maintenance changes made after the archived version was built.

## Test status and limitations

The report for version 0.5.0 records 378 automated tests passed on Ubuntu 24.04 x86_64, Python 3.12.3, and PySide6 6.12.0, along with reproducible artifacts from two consecutive builds. This is the project's recorded report, not a universal compatibility guarantee.

The following have not been confirmed by that report:

- Clean installation and dependency resolution on Debian 13.
- Actual compositor behavior in real KDE Plasma Wayland/XWayland or X11 sessions, including always-on-top, click-through, dragging, multi-monitor, and fullscreen behavior.
- Real AI provider, rclone/Google Drive, and keyring integration.
- Third-party extension compatibility and screen-reader accessibility.

See the [0.5.0 test report](releases/0.5.0/TEST-REPORT.md) for the test scope and known limitations.

## Integrity and maintenance

Verify the artifacts in a version folder by running:

~~~bash
cd apps/sorot/releases/0.5.0
sha256sum -c SHA256SUMS
~~~

The release validator also checks that each version's release.json, SHA256SUMS, and actual artifact files agree:

~~~bash
python apps/sorot/validate_releases.py
~~~

The repository's **Sorot source quality** workflow extracts the selected version's source ZIP into a temporary directory, applies maintained test/build overlays, runs Ruff, mypy, and pytest on Python 3.11–3.13, and performs a reproducible package build without publishing it. These CI-only maintenance overlays must not be represented as modifications to already archived package binaries.

For maintainer-approved contributions and attribution expectations, see the repository-level [CONTRIBUTING.md](../../CONTRIBUTING.md). Shared extension API documentation is available in [EXTENSIONS.md](EXTENSIONS.md).
