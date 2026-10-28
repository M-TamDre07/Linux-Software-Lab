# Release evidence and compatibility policy

This document records what the repository currently proves; it is not a substitute for a clean installation matrix. Release status and per-distribution compatibility are independent fields.

## Sorot 0.7.0 as currently recorded

| Target | Status | Evidence | Missing evidence |
|---|---|---|---|
| Debian family | testing | `.deb`, source archives, wheel and SHA256SUMS are present; report describes a dpkg upgrade exercise with `--force-depends` | Clean Debian 13 install via apt, installed launch, normal upgrade, uninstall/purge and dependency checks |
| Ubuntu 24.04 | testing | Report identifies Ubuntu 24.04 x86_64 as the build environment | Clean install, real Qt GUI test, launch and uninstall |
| Arch Linux | unverified | Experimental packaging files only; no validated package artifact declared | `makepkg`, `namcap`, install/launch/upgrade/uninstall in isolated Arch |
| Fedora | unverified | No RPM artifact or Fedora test evidence declared | RPM build/lint, install/launch/upgrade/uninstall in isolated Fedora |
| IGN 26 | unverified | No technical evidence recorded | Identify exact distro/release and run a reproducible package/runtime test matrix |

The existing 0.7.0 test report says the new Qt GUI changes were not tested with real PySide6/pytest in the reported environment. A package build or matching checksum proves neither successful installation nor runtime compatibility.

## Status rules

- `release_status` is the product-version lifecycle state (`testing`, `released`, or `archived`).
- Each distribution has a separate compatibility `status`: `supported`, `testing`, `unverified`, `blocked`, or `planned`.
- Do not mark a version `released` merely because artifacts exist or checksums match.
- Do not mark a distribution `supported` until reproducible evidence exists for installation, launch, upgrade, and uninstall. Real Qt/session testing is also required where relevant.
- Never infer Arch/Fedora support from Debian packages, Python wheels, source archives, or a successful build on Ubuntu.
- IGN 26 remains unverified until its exact OS identity and test environment are documented.

## Reproducible checks

```bash
python apps/sorot/validate_releases.py
python apps/sorot/validate_compatibility.py
python -m unittest discover -s apps/sorot/tests -v
```

The compatibility validator checks metadata shape, duplicate distribution IDs, lifecycle status parity between the compatibility file, release index and per-version manifest, and the minimum evidence gate for a `supported` distribution. It does not perform package installation tests.
