# Sorot distribution integration

This file describes the integration contract between the Sorot application team, the versioned release archive, the terminal installer, and the public download selector. It does not claim that planned packages exist.

## Current confirmed archive

Sorot 0.5.0 Beta is the only version currently indexed. Its version manifest declares three real artifacts: Debian package `.deb`, source `.tar.gz`, and source `.zip`. The Debian package is Beta/testing; the current test report does not confirm a clean Debian 13 installation. No Arch, RPM, AppImage, or official package repository is currently published.

The helper at `apps/sorot/install.sh` is separate from the desktop application. It reads `releases/index.json`, inspects the versioned `release.json`, selects only a matching package format, downloads the artifact, checks SHA-256, asks before installing a testing build, and calls the detected native package manager. It must never install a `.deb` file on Arch Linux as a fallback.

## Distro detection limits

The terminal helper reads `/etc/os-release` and can identify a distribution family locally. The website cannot read that local file from a normal browser. It identifies the general operating-system family when possible, then asks the visitor to select their Linux distribution before revealing compatible package formats. That is intentional: the web page must not guess a distro-specific binary.

## Target for Sorot 0.6.0 — Arch Linux

Arch support is a planned target only. The version archive does not currently contain an Arch build. Before enabling the Arch option as available, the Sorot application team must choose and build a real Arch artifact, define its dependencies and package metadata, and test a clean installation in an Arch Linux environment.

For a direct package hand-off, the release manifest should declare an actual `.pkg.tar.zst` artifact with `kind: arch-package`, `format: pkg.tar.zst`, a valid architecture value such as `any`, and the real file's SHA-256. The installer can then verify the package and call `pacman -U`. Do not publish `pacman -S sorot` instructions until Sorot is actually present in an official or configured Arch repository.

The maintainers may additionally publish a `PKGBUILD` for building from source with `makepkg -si`; that is a different distribution path and must be reviewed and tested before the website presents it as an installation option. The current source archives do not imply that a PKGBUILD exists.

## Adding a later version

For each real release, the application team should:

1. Keep every older version directory unchanged.
2. Build only the formats actually supported and tested for the release.
3. Add the real package/source files, a version-specific `release.json`, `SHA256SUMS`, release notes, and the relevant test report to the new directory.
4. Add the version and its actually available formats to `releases/index.json`.
5. Update `public/data/sorot-downloads.json` and verify that its artifact names, formats, and hashes exactly match the version manifest.
6. Run the release validator, website tests, terminal installer checks, and a clean install test for every claimed distro.

A planned format must not be listed as an available artifact. An artifact's presence in Git does not, by itself, prove distro compatibility or stable-release readiness.

## Terminal usage

From a downloaded checkout of the repository:

```bash
bash apps/sorot/install.sh --detect
bash apps/sorot/install.sh --list
bash apps/sorot/install.sh --version 0.5.0
```

The third command selects the current Beta only on a distro that has a compatible native artifact. On Arch, the installer deliberately stops because no Arch package is published yet. The helper fetches version manifests and packages over HTTPS and validates SHA-256 values against the manifest; the current archive does not provide a signed repository or cryptographic package signature, so a checksum should not be described as a publisher signature.
