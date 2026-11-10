# Sorot

Sorot is a native Linux desktop teleprompter. Its existing interface, text workflow, playback behavior, and extension ecosystem are maintained incrementally; this repository does not treat a new release as a reason to redesign the UI/UX.

## Current archived versions

The latest indexed build is **Sorot 0.8.0 Beta/testing**. It is not a stable release. The .deb artifact is targeted to Debian 13; a clean Debian 13 installation has not yet been verified. RPM packaging was built with --nodeps on Ubuntu but not installed on Fedora. The Flatpak manifest was validated but the Flatpak package was not built. Arch remains a planned target without a published .pkg.tar.zst artifact.

- [Sorot 0.8.0 Debian package](releases/0.8.0/sorot_0.8.0_all.deb)
- [Sorot 0.8.0 source tar.gz](releases/0.8.0/sorot-0.8.0.tar.gz)
- [Sorot 0.8.0 source ZIP](releases/0.8.0/sorot-0.8.0.zip)
- [Sorot 0.8.0 Python wheel](releases/0.8.0/sorot-0.8.0-py3-none-any.whl)
- [Sorot 0.8.0 SHA-256 checksums](releases/0.8.0/SHA256SUMS)
- [Sorot 0.8.0 manifest](releases/0.8.0/release.json)
- [Sorot 0.8.0 test report](releases/0.8.0/TEST-REPORT.md)
- [Complete version index](releases/index.json)
- [Previous version archive](releases/0.7.3/)

See [the release archive guide](releases/README.md) for the immutable version process. The website and terminal helper read the shared version index; the website catalogue and offline Software Center distribution index are generated from that canonical metadata.

For distro selection, verified download links, and the terminal helper, see [DISTRIBUTION.md](DISTRIBUTION.md).

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

Download the Debian package for the version you intend to use, then install it with APT so dependencies can be resolved. For example, from a downloaded 0.8.0 package file:

~~~bash
sudo apt install ./sorot_0.8.0_all.deb
~~~

For a move back to an older version, first select that version's directory, verify its SHA-256 checksums, back up scripts and other important data, and install its package. If APT blocks a downgrade, use the explicit downgrade option:

~~~bash
sudo apt install --allow-downgrades ./sorot_0.5.8_all.deb
~~~

The name 0.5.8 in this example illustrates a possible future version; it is not currently included in this archive. Avoid removing user configuration with package purge commands when the intent is only to change application versions.

The source tar.gz and ZIP archives are version-specific snapshots for reviewing or building the application source. They are not guaranteed to include maintenance changes made after the archived version was built.

## Test status and limitations

The 0.8.0 report records **652 passing automated tests** on each of Python 3.11 and 3.13. It also records 135 GUI tests passing on X11 (Xvfb + openbox) and 131 passing on headless Wayland (Weston), with four focus/clipboard tests skipped because the headless compositor has no seat. Linting and reproducible artifact builds were also reported clean.

These results are scoped to Ubuntu 24.04.5 x86_64 in a container. They do not certify a physical GNOME/KDE desktop, clean Debian 13 installation, Fedora RPM installation, Arch installation, or a built/installed Flatpak. Real AI/cloud integrations, accessibility with screen readers, and third-party extension compatibility still require manual testing.

See the [0.8.0 test report](releases/0.8.0/TEST-REPORT.md) for the exact test scope and outstanding checks. The report is test evidence, not a universal compatibility guarantee.

## Integrity and maintenance

Verify the artifacts in a version folder by running:

~~~bash
cd apps/sorot/releases/0.8.0
sha256sum -c SHA256SUMS
~~~

The release validator also checks that each version's release.json, SHA256SUMS, and actual artifact files agree:

~~~bash
python apps/sorot/validate_releases.py
~~~

The repository's **Sorot source quality** workflow extracts the selected version's source ZIP into a temporary directory, applies maintained test/build overlays, runs Ruff, mypy, and pytest on Python 3.11–3.13, and performs a reproducible package build without publishing it. These CI-only maintenance overlays must not be represented as modifications to already archived package binaries.

For maintainer-approved contributions and attribution expectations, see the repository-level [CONTRIBUTING.md](../../CONTRIBUTING.md). Shared extension API documentation is available in [EXTENSIONS.md](EXTENSIONS.md).
