# Sorot

Sorot is a native Linux desktop teleprompter. Its existing interface, text workflow, playback behavior, and extension ecosystem are maintained incrementally; this repository does not treat a new release as a reason to redesign the UI/UX.

## Current stable release

The latest indexed release is **Sorot 1.0.23 (stable)**. The maintainer approved it after functional testing and a release-suitability review. The published artifacts are:

- [Sorot 1.0.23 Debian package](releases/1.0.23/sorot_1.0.23_all.deb)
- [Sorot 1.0.23 Python wheel](releases/1.0.23/sorot-1.0.23-py3-none-any.whl)
- [Sorot 1.0.23 SHA-256 checksums](releases/1.0.23/SHA256SUMS)
- [Sorot 1.0.23 release manifest](releases/1.0.23/release.json)
- [Sorot 1.0.23 QA and release sign-off](releases/1.0.23/TEST-REPORT.md)
- [Complete version index](releases/index.json)

The .deb is intended for compatible Debian/Ubuntu-family systems. The Python wheel requires a suitable interpreter and dependencies. Arch Linux remains a planned target without a published .pkg.tar.zst artifact. Version 0.9.0 is archived and not recommended for new installations; versions 0.8.0 and earlier remain testing/Beta according to their manifests.

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

Download the Debian package for the version you intend to use, then install it with APT so dependencies can be resolved. For example, from a downloaded 1.0.23 package file:

~~~bash
sudo apt install ./sorot_1.0.23_all.deb
~~~

For a move back to an older version, first select that version's directory, verify its SHA-256 checksums, back up scripts and other important data, and install its package. If APT blocks a downgrade, use the explicit downgrade option:

~~~bash
sudo apt install --allow-downgrades ./sorot_0.5.8_all.deb
~~~

The name 0.5.8 in this example illustrates a possible future version; it is not currently included in this archive. Avoid removing user configuration with package purge commands when the intent is only to change application versions.

The source tar.gz and ZIP archives are version-specific snapshots for reviewing or building the application source. They are not guaranteed to include maintenance changes made after the archived version was built.

## Test status and limitations

### Stable release 1.0.23

The maintainer confirmed that Sorot 1.0.23 passed functional testing and a release-suitability review before being approved for the stable channel. The release-specific QA sign-off, artifact list, and compatibility boundaries are recorded in [the 1.0.23 QA report](releases/1.0.23/TEST-REPORT.md). Repository CI validates release manifests, real artifact files, SHA-256 consistency, distribution-index generation, and website integration. These checks support the release decision but do not certify every Linux distribution, desktop environment, or third-party extension.

The published .deb is intended for compatible Debian/Ubuntu-family systems; the Python wheel requires a compatible Python environment and dependencies. Arch Linux still has no published native package. Do not interpret the stable channel as universal distro support.

### Historical 0.8.0 test record

The 0.8.0 report records **652 passing automated tests** on each of Python 3.11 and 3.13. It also records 135 GUI tests passing on X11 (Xvfb + openbox) and 131 passing on headless Wayland (Weston), with four focus/clipboard tests skipped because the headless compositor has no seat. Linting and reproducible artifact builds were also reported clean.

Those historical results are scoped to Ubuntu 24.04.5 x86_64 in a container. They do not certify a physical GNOME/KDE desktop, Fedora RPM installation, Arch installation, or a built/installed Flatpak. Real AI/cloud integrations, accessibility with screen readers, and third-party extension compatibility still require manual testing.

See the [0.8.0 test report](releases/0.8.0/TEST-REPORT.md) for its exact historical test scope and limitations.

## Integrity and maintenance

Verify the artifacts in a version folder by running:

~~~bash
cd apps/sorot/releases/1.0.23
sha256sum -c SHA256SUMS
~~~

The release validator also checks that each version's release.json, SHA256SUMS, and actual artifact files agree:

~~~bash
python apps/sorot/validate_releases.py
~~~

The repository's **Sorot source quality** workflow extracts the selected version's source ZIP into a temporary directory, applies maintained test/build overlays, runs Ruff, mypy, and pytest on Python 3.11–3.13, and performs a reproducible package build without publishing it. These CI-only maintenance overlays must not be represented as modifications to already archived package binaries.

For maintainer-approved contributions and attribution expectations, see the repository-level [CONTRIBUTING.md](../../CONTRIBUTING.md). Shared extension API documentation is available in [EXTENSIONS.md](EXTENSIONS.md).
