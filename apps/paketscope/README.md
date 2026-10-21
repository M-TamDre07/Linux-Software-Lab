# PaketScope 3 — Native desktop (development preview)

PaketScope is a local-first desktop inventory for Debian-family Linux systems. The current v3 development build discovers installed APT/dpkg and Flatpak applications, searches the local APT index, and supports explicitly confirmed APT install, remove, and purge operations. Update checks and exports remain available; Flatpak inventory is visible but is not yet mutable from the app.

> Development preview: this branch is not yet a signed or packaged release. Run it from source and review the code before use.

## Native architecture

PaketScope 3 is a **native Linux desktop application**, not a website or browser wrapper. Its frontend is built with PySide6/Qt Widgets. The Python application-service layer coordinates use cases, domain models hold normalized inventory data, and OS adapters communicate with APT/dpkg and Flatpak through bounded, argument-list subprocess calls. User-selected exports and encrypted backups remain local.

The v3 branch adds a service boundary between the GUI and package operations. It remains a development preview: package changes are limited to APT/dpkg and require an APT simulation, explicit in-app confirmation, and a polkit authentication prompt. Flatpak mutation, a remote API, accounts, telemetry, and background updates remain out of scope.


## Current scope

- Local inventory using dpkg-query and flatpak list; source types are shown separately.
- A Qt desktop interface with searchable, sortable table data.
- On-demand update checks. APT is checked against local package-list metadata; Flatpak checks can contact configured remotes.
- CSV export and password-encrypted JSON backup (AES-256-GCM with a scrypt-derived key).
- No account, analytics, telemetry, background updater, or remote backend.
- The GUI itself runs as the regular user. APT mutation uses pkexec/polkit only after a preview and confirmation; commands use validated package identifiers, argument arrays, and no shell.
- APT installation refuses transactions that would remove other packages. PaketScope does not call autoremove or run bulk upgrades.
- APT remove and purge operate on one selected package at a time. Purge removes dpkg-managed system configuration but does not guarantee that data or settings in the user's home directory are removed.
- Flatpak packages remain read-only in this development build; no install/remove action is offered for them.

Unsupported package formats and user-installed AppImages are deliberately not inferred as managed packages. Missing system tools are shown as diagnostics, not silently treated as an empty inventory.

## Requirements

- Python 3.10+
- Debian 13 or a Debian-family desktop (initial development target)
- PySide6 and cryptography (installed by the project command below)
- Optional system tools: dpkg-query, apt, and flatpak

## Run from source

From this directory:

~~~bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m paketscope
~~~

Package names and versions may be visible in the UI and exported file. Store exports carefully. Encrypted backups cannot be recovered without the passphrase; use a unique, long passphrase and keep it separate from the backup file.

## Tests

~~~bash
python -m pytest
~~~

The test suite covers inventory parsing, command-error handling, encrypted-backup integrity, CSV formula protection, owner-only file permissions on POSIX, and importing the Qt UI module. These checks are not a substitute for testing against real Debian/Flatpak installations or a formal security audit.

## Privacy and security

- Inventory collection is local and read-only. The app does not send package names off the machine.
- The only intentional network-capable workflow is the user-triggered Flatpak remote update check. APT update visibility uses locally cached metadata and does not run apt update.
- Read-only subprocess calls run as the current user with shell=False and timeouts. A selected APT transaction is simulated first; only the specific apt-get operation is delegated via pkexec after an explicit confirmation.
- Installation is constrained with --no-remove and --no-install-recommends. No arbitrary command field, shell text, automatic cleanup, or background package mutation exists.
- Encrypted backup contents use AES-GCM authenticated encryption. A random salt and nonce are generated for every backup; scrypt derives the key from the passphrase.
- The application does not store passwords or passphrases. Plain CSV/JSON exports are intentionally not encrypted; choose the encrypted backup option for portable protected copies.
- CSV values that resemble spreadsheet formulas are neutralized during export. Export files and decrypted JSON are atomically written with owner-only POSIX permissions (`0600`); still treat them as sensitive data.
- Do not run this project with elevated privileges. Report security problems privately to the maintainer before making them public.

## Build the Debian development package

The repository now contains a Debian package definition and a GitHub Actions workflow that runs the Python tests and attempts to build a Debian 13 .deb. A successful workflow stores a short-lived development artifact; it is not a signed stable release and should not be linked as a final public download before the clean-install checks pass.

For a Debian 13 build environment with debhelper installed:

~~~bash
dpkg-buildpackage --build=binary --no-sign
~~~

The generated .deb is written to the parent directory. Install it only on a test system you control; inspect the package and its dependencies first.

## Remaining before a public release

- Test install, remove, and purge against clean Debian 13 systems and representative real systems.
- Add Flatpak install/remove only after the installation-scope behavior and confirmation UX are tested.
- Improve reliable provenance reporting. APT can show its configured repository candidates, but cannot always prove the historical repository from which an installed package originally came.
- Validate package contents, desktop launch behavior, accessibility, and failure/cancel flows.
- Produce a stable tagged release with a checksum and documented compatibility matrix.

Do not announce a stable release until all CI checks, real-system compatibility checks, package installation/uninstallation tests, and a security review have completed.
