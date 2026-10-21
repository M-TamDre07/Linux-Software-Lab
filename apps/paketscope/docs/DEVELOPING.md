# Developing PaketScope

This guide is for people who want to read, test, or contribute to PaketScope 3.
The current target is a native desktop application for Debian 13 (Trixie).
Other Debian derivatives are not considered supported package targets until they
have their own installation tests.

## Before editing

Use a separate checkout or feature branch. Keep changes small enough to review,
and avoid mixing UI changes, package-manager behavior, and release metadata in a
single patch unless they are required for one feature.

From `apps/paketscope/`, prepare a local development environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

Run tests and start the app as your regular desktop user:

```bash
python -m compileall -q paketscope
QT_QPA_PLATFORM=offscreen python -m pytest
python -m paketscope
```

Do not launch the graphical application with `sudo`. The UI requests a reviewed,
single-package APT transaction and delegates only that operation through polkit.

## Where code belongs

```text
paketscope/
  app.py             Application startup and MainWindow event coordination
  domain.py          Plain data models and output parsers
  services.py        Application use cases and local data workflows
  commands.py        Bounded subprocess execution helper
  collectors.py      Read-only APT/dpkg and Flatpak inventory adapters
  updates.py         User-triggered update checks
  package_manager.py APT search, transaction simulation and guarded execution
  backup.py          Encrypted backup format and cryptographic operations
  exporting.py       Private, atomic file writes and CSV-safe values
  ui/
    theme.py         Table headings and Qt stylesheet
    models.py        Qt inventory table and search/filter model
    workers.py       Background task runner and result/error signals
assets/              Desktop visual assets
tests/               Unit tests and offscreen UI import/model tests
debian/              Debian package metadata and build rules
packaging/           Desktop launcher and menu entry
docs/                Architecture, security, and contributor guidance
```

## Data flow

The intended dependency direction is:

1. The Qt UI collects user input and presents progress, previews, confirmations,
   and results.
2. `services.py` coordinates application-level use cases that do not belong in
   widget code.
3. Domain types and focused adapters parse local data, invoke specific operating
   system tools, and report diagnostics.
4. The package-manager boundary validates package identifiers and exposes an
   explicit APT transaction preview before a privileged action is permitted.

Keep UI details out of domain parsing. Keep command strings and subprocess details
out of widgets. Never use shell command strings for package names or user input.
Use argument arrays, bounded timeouts, predictable errors, and tests for failure
paths.

## How to add or change functionality

- **Inventory/parser change:** update a pure parser or focused collector, add tests
  for valid, empty, malformed, and error output, then update the UI only if the
  visible behavior actually changes.
- **New package-manager backend:** introduce a separate adapter with its own
  command validation, inventory parser, transaction-preview behavior, and tests.
  Do not make Debian APT assumptions the responsibility of the entire UI.
- **UI change:** use descriptive control names, accessible labels/tooltips, and
  explicit busy, empty, failure, and cancellation states. Keep long-running reads
  off the GUI thread.
- **File export or backup change:** keep file operations in service/helper modules,
  use atomic writes and owner-only permissions where appropriate, and test damaged
  files, wrong passphrases, and spreadsheet-formula inputs.
- **Dependency or Debian packaging change:** update `pyproject.toml` or Debian
  metadata deliberately and prove that the built package installs, imports the
  installed module, exposes its launcher, and can be purged cleanly.

## Review checklist

Before opening or updating a pull request:

- [ ] Explain the problem and why the proposed change belongs in that module.
- [ ] Run `python -m compileall -q paketscope` and `QT_QPA_PLATFORM=offscreen python -m pytest`.
- [ ] Add regression tests for changed behavior and failure/cancellation paths.
- [ ] Check that package operations still use argument arrays, a simulation,
      an explicit confirmation, and polkit authorization.
- [ ] Keep secrets, user inventory, and generated local backups out of commits.
- [ ] Do not mark the project stable until CI and real Debian desktop checks are complete.

CI success is useful evidence, but it does not replace desktop testing or a security
review. Changes that install, remove, purge, or modify system packages should first
be tested in a disposable Debian virtual machine with a recoverable snapshot.
