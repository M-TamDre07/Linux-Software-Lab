# Sorot 1.0.23 — QA and stable release record

**Release decision:** PASS — stable
**Version:** 1.0.23
**Artifacts:** Debian package (.deb) and Python wheel
**Release date:** 24 November 2026

## Maintainer sign-off

The project maintainer confirmed that the final Sorot 1.0.23 build completed functional testing and a release-suitability review, and approved this version for the stable channel.

This report records that release decision. It does not claim that every Linux distribution, desktop environment, architecture, or optional third-party integration has been tested. No universal compatibility guarantee is made.

## Published artifact integrity

| Artifact | SHA-256 |
| --- | --- |
| `sorot_1.0.23_all.deb` | `bb2c19c958ee419e676f2b29e6d7813761c54f8869706fcef9ab3051235765e3` |
| `sorot-1.0.23-py3-none-any.whl` | `8541aff413fb494d96bd84cac3ca8a603355aafb85f2ef80ccaf446b87ea4320` |

The same digests are recorded in `release.json` and `SHA256SUMS`. The repository release validator checks that each declared artifact exists and that its SHA-256 matches both metadata files.

## Repository validation

The release workflow runs these checks before publication:

- `python apps/sorot/validate_releases.py` — manifest, artifact, and checksum consistency.
- `python -m unittest discover -s tests -p 'test_sorot_distribution_integration.py' -v` — release-index, generated distribution metadata, mirror, and website integration.
- `python scripts/sync_distribution_index.py --check` — generated public and offline launcher indexes.
- Sorot source-quality CI — automated source tests and reproducible package-build checks for the workflow's configured Python versions.

These automated checks complement, but do not replace, the maintainer's functional review.

## Supported artifact boundaries

- **Debian package:** intended for compatible Debian/Ubuntu-family distributions. Confirm the actual OS version and dependencies before installation.
- **Python wheel:** requires a compatible Python interpreter, dependencies, and environment.
- **Arch Linux:** planned only; no validated `.pkg.tar.zst` artifact is published for 1.0.23.
- **RPM, AppImage, and Flatpak:** no 1.0.23 release artifact is published in these formats.

Verify downloads with `sha256sum -c SHA256SUMS`. A matching checksum confirms file consistency with the repository metadata; it is not a cryptographic publisher signature.
