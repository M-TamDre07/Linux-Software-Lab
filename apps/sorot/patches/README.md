# Sorot maintenance patches

The tagged 0.5.0 beta artifacts in this directory are immutable audit inputs. Keep changes for the next source build as a small, ordered patch series until a new versioned source tree and release are intentionally cut.

Patches are applied to a temporary extraction of `sorot-0.5.0.zip` in CI. The archive, Debian package, and existing SHA-256 manifest are not rewritten.

## Current patch series

- `0001-validate-qt-plugin-elf.patch`: reject Qt platform-plugin files that do not begin with the Linux ELF magic bytes before probing them with PySide6. This makes detection deterministic when PySide6 is unavailable and avoids treating arbitrary files named `libq*.so` as valid plugins. It does not claim that a valid ELF plugin can load; when Qt is available, `QLibrary` still checks loadability and dependencies.
- `apply.py`: applies the source-only maintenance overlay after patch 0001. It bounds rclone stdout and stderr capture, terminates the process on overflow/cancellation/timeout, adds regression coverage for oversized output, updates the security-reporting policy, and fills the maintainer contact in Debian control/changelog/copyright metadata and the release checklist. These contact updates are applied only to the temporary source tree used by CI and a future intentional build. The original ZIP, tarball, `.deb`, and `SHA256SUMS` remain unchanged.

## Local verification

From the repository root:

```bash
repo_root="$PWD"
tmp="$(mktemp -d)"
unzip -q apps/sorot/sorot-0.5.0.zip -d "$tmp"
cd "$tmp/sorot-0.5.0"
patch -p0 < "$repo_root/apps/sorot/patches/0001-validate-qt-plugin-elf.patch"
python "$repo_root/apps/sorot/patches/apply.py" "$tmp/sorot-0.5.0"
python -m pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

The source overlay is tested in temporary extractions by `.github/workflows/sorot-quality.yml`. It must not be described as part of the existing 0.5.0 beta binaries. The current `.deb` and source archives still retain their original maintainer placeholder. A revised release artifact requires a deliberate versioned rebuild, review, full test run, new checksums, and explicit publication.
