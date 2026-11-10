# Sorot distribution integration

This document defines how the versioned Sorot archive, the terminal installer, the web selector, and GitHub Actions fit together. A planned package is never treated as available.

## Indexed versions and current scope

Sorot 0.5.0 through **0.8.0** are indexed as Beta/testing. The current latest version, 0.8.0, publishes four artifacts: a Debian .deb package targeted to Debian 13, source tar.gz, source ZIP, and Python wheel. Older version folders remain immutable and available in the version history.

The 0.8.0 report records 652 passing automated tests on Python 3.11 and 3.13, 135 GUI tests passing on X11 virtual (Xvfb + openbox), and 131 passing on headless Wayland (Weston), with four tests skipped because the headless compositor has no seat. The report is based on Ubuntu 24.04.5 x86_64 in a container. A clean Debian 13 installation, real GNOME/KDE compositor behavior, Fedora installation, Arch installation, and Flatpak build/install have not been verified. RPM was built with --nodeps on Ubuntu only; the Flatpak manifest was validated but the bundle was not built. Keep the public status Beta/testing.

The terminal helper at apps/sorot/install.sh and web selector read the version manifests. The web selector reads apps/sorot/releases/index.json from GitHub at runtime for its version list. Once the selector is deployed, adding a validated version to the canonical index and its release manifest makes it available to the website without a second manual download list.

## Distro selection and safety

The terminal helper reads `/etc/os-release` locally. The browser cannot read that file, so the site asks visitors to select the distro manually and only displays compatible native formats found in a release manifest. It must not infer exact distro compatibility from browser user-agent or fall back to installing a Debian package on Arch.

Arch Linux remains a planned target. PKGBUILD files are stored under `apps/sorot/experimental/arch/<version>/` for review only. There is no validated `.pkg.tar.zst`, no completed Arch CI result, and no clean Arch installation test. Do not present `makepkg -si`, `pacman -U`, or a repository installation command as supported for Sorot 0.8.0.

## Release workflow for maintainers

1. Create a new immutable folder, e.g. `apps/sorot/releases/0.8.0/`, with the actual artifacts and a matching `SHA256SUMS`.
2. Add `release.json` with only published artifacts. Its artifact filenames and SHA-256 values must exactly match the real files and `SHA256SUMS`.
3. Append the version to `apps/sorot/releases/index.json` in ascending release order; list the exact formats from its manifest. Put unfinished targets under `planned_targets`.
4. Run `python apps/sorot/validate_releases.py` and `python -m unittest discover -s tests -p 'test_sorot_distribution_integration.py' -v`, then open a PR.
5. GitHub Actions validates the release, verifies website metadata/docs, and automatically synchronizes `public/data/distribution-index.json` after merge. **Do not manually edit the Sorot manifest list in the public distribution index.**

The generated website index is still useful to the launcher and other consumers, but the canonical release list lives in `apps/sorot/releases/index.json`. This avoids a recurring integration task for every version.

## Terminal usage

~~~
bash apps/sorot/install.sh --detect
bash apps/sorot/install.sh --list
bash apps/sorot/install.sh --version 0.8.0
~~~

The helper verifies SHA-256 and asks before installing testing builds. The archive is not a signed package repository; checksums are not cryptographic publisher signatures. Back up user scripts/configuration before any upgrade. The installer selects only a native artifact declared in the manifest for the detected distro.
