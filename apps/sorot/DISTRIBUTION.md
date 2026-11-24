# Sorot distribution integration

This document defines how the versioned Sorot archive, the terminal installer, the web selector, and GitHub Actions fit together. A planned package is never treated as available.

## Indexed versions and current scope

Sorot **1.0.23** is the latest stable release, with a Debian .deb package and Python wheel. The .deb is intended for compatible Debian/Ubuntu-family distributions; the wheel requires a suitable Python environment and dependencies. Versions 0.8.0 and earlier remain Beta/testing according to their manifests, while 0.9.0 is archived. Older version folders remain immutable and available in the version history.

The maintainer has approved Sorot 1.0.23 for the stable channel after functional testing and a release-suitability review; see `apps/sorot/releases/1.0.23/TEST-REPORT.md`. This sign-off applies to the published .deb and Python wheel, and does not imply universal compatibility across all Linux distributions or desktop environments. The 0.8.0 test report is historical evidence for that older build only: it records 652 passing automated tests on Python 3.11 and 3.13, 135 GUI tests passing on X11 virtual (Xvfb + openbox), and 131 passing on headless Wayland (Weston), with four tests skipped because the headless compositor has no seat. Those results were based on Ubuntu 24.04.5 x86_64 in a container. Arch remains a planned target without a native .pkg.tar.zst artifact; no RPM or Flatpak artifact is published for 1.0.23.

The terminal helper at apps/sorot/install.sh and web selector read the version manifests. The web selector reads apps/sorot/releases/index.json from GitHub at runtime for its version list. Once the selector is deployed, adding a validated version to the canonical index and its release manifest makes it available to the website without a second manual download list.

## Distro selection and safety

The terminal helper reads `/etc/os-release` locally. The browser cannot read that file, so the site asks visitors to select the distro manually and only displays compatible native formats found in a release manifest. It must not infer exact distro compatibility from browser user-agent or fall back to installing a Debian package on Arch.

Arch Linux remains a planned target. PKGBUILD files are stored under `apps/sorot/experimental/arch/<version>/` for review only. There is no validated `.pkg.tar.zst`, no completed Arch CI result, and no clean Arch installation test. Do not present `makepkg -si`, `pacman -U`, or a repository installation command as supported for Sorot 1.0.23.

## Release workflow for maintainers

1. Create a new immutable folder, e.g. `apps/sorot/releases/0.8.0/`, with the actual artifacts and a matching `SHA256SUMS`.
2. Add `release.json` with only published artifacts. Its artifact filenames and SHA-256 values must exactly match the real files and `SHA256SUMS`.
3. Append the version to `apps/sorot/releases/index.json` in ascending release order; list the exact formats from its manifest. Put unfinished targets under `planned_targets`.
4. Run `python apps/sorot/validate_releases.py` and `python -m unittest discover -s tests -p 'test_sorot_distribution_integration.py' -v`, then open a PR.
5. GitHub Actions validates the release, verifies website metadata/docs, and automatically synchronizes `public/data/distribution-index.json` after merge. **Do not manually edit the Sorot manifest list in the public distribution index.**

The generated website index is still useful to the launcher and other consumers, but the canonical release list lives in `apps/sorot/releases/index.json`. This avoids a recurring integration task for every version.

## Terminal usage for end users

The installer can be run from an ordinary terminal account. It reads `/etc/os-release`, matches the local distro family and CPU architecture against the release manifest, downloads only a declared native package, verifies SHA-256, and asks for administrator privileges only when the selected package manager must install the package. Do not run the installer itself with `sudo`.

First download and inspect the script from the official repository:

```bash
curl --fail --location --show-error --max-time 30 \
  https://raw.githubusercontent.com/M-TamDre07/Linux-Software-Lab/main/apps/sorot/install.sh \
  --output /tmp/sorot-install.sh

sed -n '1,260p' /tmp/sorot-install.sh
```

Then inspect the detected platform and real published artifacts. The dry run downloads and verifies the package but does not invoke the package manager:

```bash
bash /tmp/sorot-install.sh --detect
bash /tmp/sorot-install.sh --list
bash /tmp/sorot-install.sh --version 1.0.23 --dry-run
```

After confirming the detected distro and successful checksum verification, install:

```bash
bash /tmp/sorot-install.sh --version 1.0.23
```

Optional operations:

```bash
bash /tmp/sorot-install.sh --help
bash /tmp/sorot-install.sh --list
bash /tmp/sorot-install.sh --version 1.0.23 --dry-run
```

**Current compatibility boundary (24 November 2026):**

| Platform family | 1.0.23 artefact | Current state |
| --- | --- | --- |
| Debian / Ubuntu family | `.deb` | Published; Debian 13 is the current CI smoke-test target. Other derivatives still need individual compatibility checks. |
| Arch Linux | `.pkg.tar.zst` | Not published; installer refuses to fall back to `.deb`. |
| Fedora / RHEL | `.rpm` | Not published. |
| openSUSE / SUSE | `.rpm` | Not published. |
| Other Linux | — | No native package-manager artefact declared. |
| Python environments | `.whl` | Published for compatible Python environments; not an OS-native package. |

A `.deb` being available does not establish that every Debian/Ubuntu derivative or desktop environment was tested. Likewise, distro detection identifies a family; it does not prove hardware, Qt platform plugin, Wayland/X11, or desktop compatibility. The script stops when no matching artefact exists. Do not use `pacman -U`, `dnf install`, or `zypper install` for Sorot 1.0.23 until matching packages are actually published.

The helper's checksum check protects against file mismatch against the manifest and `SHA256SUMS`; it is not a cryptographic publisher signature. Back up user scripts/configuration before upgrading. See [installation and compatibility guide](../../docs/INSTALLATION_AND_COMPATIBILITY.md) for the full user workflow and service integration checks.
