# PaketScope 2

PaketScope is a local-first desktop inventory for Debian-family Linux systems. Version 2 starts with a safety-oriented scope: discover installed APT/dpkg and Flatpak applications, search and filter the inventory, check updates only when requested, and export the inventory.

> Development preview: this source is not yet a signed or packaged release. Run it from source and review the code before use.

## Current scope

- Read-only inventory using dpkg-query and flatpak list.
- A Qt desktop interface with searchable, sortable table data.
- On-demand update checks. APT is checked against local package-list metadata; Flatpak checks can contact configured remotes.
- CSV export and password-encrypted JSON backup (AES-256-GCM with a scrypt-derived key).
- No account, analytics, telemetry, background updater, or remote backend.
- No root privileges, no sudo, no shell-string command execution, and no package install/remove actions.

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
- All subprocess calls pass an argument list with shell=False, use timeouts, and run as the current user.
- Encrypted backup contents use AES-GCM authenticated encryption. A random salt and nonce are generated for every backup; scrypt derives the key from the passphrase.
- The application does not store passwords or passphrases. Plain CSV/JSON exports are intentionally not encrypted; choose the encrypted backup option for portable protected copies.
- CSV values that resemble spreadsheet formulas are neutralized during export. Export files and decrypted JSON are atomically written with owner-only POSIX permissions (`0600`); still treat them as sensitive data.
- Do not run this project with elevated privileges. Report security problems privately to the maintainer before making them public.

## Roadmap (not yet implemented)

Signed release builds, desktop sandboxing, broader package-source support, integration tests on clean Debian 13/Flatpak systems, reproducible builds, and a documented security review.
