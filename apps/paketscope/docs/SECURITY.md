# PaketScope security notes

## Security boundaries

PaketScope v2 is a local desktop inventory tool, not a system package manager. It uses unprivileged, read-only commands for discovery and does not invoke a shell. It intentionally does not provide install, remove, upgrade, cleanup, or privileged operations.

Package names, IDs, origins, and versions can disclose installed tools or parts of a work environment. Treat plaintext exports as private files. The encrypted backup format uses a per-file random salt, random AES-GCM nonce, authenticated encryption, and a passphrase-derived key using scrypt. A weak passphrase can still be guessed; the application cannot recover a forgotten passphrase.

The Flatpak update check can contact configured remotes, but only after the user presses the update-check button. The app itself has no account, analytics SDK, telemetry endpoint, or background network task.

## Before release

- Test on clean Debian 13 systems with and without Flatpak.
- Verify command behavior across supported Flatpak versions.
- Review dependency advisories and lock or document reproducible release dependencies.
- Build signed packages and verify artifact checksums.
- Add integration tests and complete an independent security review.
- Do not claim a formal audit or guaranteed security until one is completed.

## Reporting

Please report suspected vulnerabilities privately to the project maintainer before public disclosure. Do not include package inventories or personal data unless strictly necessary.
