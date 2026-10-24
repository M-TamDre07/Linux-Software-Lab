# Sorot maintenance patches

The tagged 0.5.0 beta artifacts in this directory are immutable audit inputs. Keep changes for the next source build as a small, ordered patch series until a new versioned source tree and release are intentionally cut.

Patches are applied to a temporary extraction of `sorot-0.5.0.zip` in CI. The archive, Debian package, and existing SHA-256 manifest are not rewritten.

## Current patch series

- `0001-validate-qt-plugin-elf.patch`: reject Qt platform-plugin files that do not begin with the Linux ELF magic bytes before probing them with PySide6. This makes detection deterministic when PySide6 is unavailable and avoids treating arbitrary files named `libq*.so` as valid plugins. It does not claim that a valid ELF plugin can load; when Qt is available, `QLibrary` still checks loadability and dependencies.

## Local verification

From the repository root:

```bash
repo_root="$PWD"
tmp="$(mktemp -d)"
unzip -q apps/sorot/sorot-0.5.0.zip -d "$tmp"
cd "$tmp/sorot-0.5.0"
patch -p0 < "$repo_root/apps/sorot/patches/0001-validate-qt-plugin-elf.patch"
python -m pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

The release artifact must not be advertised as containing a maintenance patch until a deliberate versioned rebuild is reviewed, tested, checksummed, and published.
