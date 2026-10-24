# Sorot 0.5.0 Beta — release readiness

## Current disposition

**Do not promote the current artifacts to a stable release.** Keep the published catalog status at `testing` and keep `releaseUrl` empty until the release gates below have current evidence. This document intentionally separates checks performed during this review from tests reported by the supplied project.

## Independently verified in the current review

- The uploaded Debian package is a valid `.deb` archive and reports package name `sorot`, version `0.5.0`, architecture `all`.
- The uploaded `.deb` SHA-256 and the uploaded ZIP SHA-256 match the repository's existing `SHA256SUMS` manifest exactly.
- All MD5 checksums recorded inside the Debian package match the extracted payload.
- The Python source in the ZIP compiles under Python 3.13.
- Targeted test groups passed, including API service/config/CLI tests, rclone/path handling, extension discovery and archive extraction checks, script/file utilities, and platform metadata tests after the maintained Qt-plugin patch was applied.
- The unpatched source failed `test_plugin_with_missing_dependency_is_not_offered` in an environment without PySide6: arbitrary non-ELF files named `libq*.so` were treated as loadable because the probe fallback returned `True`. Patch `patches/0001-validate-qt-plugin-elf.patch` rejects files without the ELF magic before falling back to the optional Qt loader probe.
- Supabase RLS and effective table privileges were checked separately as part of the website integration: anonymous clients have SELECT and do not have INSERT, UPDATE, or DELETE access.

## Still required before a stable release

1. **Source CI:** the maintained source patch and full test/build workflow must pass across Python 3.11, 3.12, and 3.13. The local audit environment did not have PySide6 installed and did not complete a full desktop test suite.
2. **Clean installation:** install and remove the newly built package on clean Debian 13 and a supported Ubuntu release in disposable virtual machines. Verify dependency resolution, launcher, icons, configuration preservation, and upgrade/uninstall behavior.
3. **Real desktop sessions:** test overlay transparency, position, click-through, multi-monitor, fullscreen, suspend/resume, and compositor variations on actual X11/XWayland and Wayland sessions. Offscreen tests are not evidence of compositor behavior.
4. **Optional integrations:** run opt-in tests against a user-configured OpenAI-compatible endpoint and rclone/Google Drive test remote; document that these integrations are external and user-configured.
5. **Accessibility:** validate keyboard navigation, focus order, zoom, contrast, and screen-reader behavior with the actual desktop application.
6. **Maintainer metadata:** the supplied `.deb` currently uses `maintainer@sorot.invalid`. Replace this placeholder with the project-approved support/maintainer contact before building a distributable release; do not invent a contact address.
7. **Release integrity:** bump the application version, regenerate the artifacts intentionally, verify reproducible builds and SHA-256 sums, inspect the package with Lintian, publish release notes and checksums, and only then set the website catalog to `released`.

## Security boundary

Sorot code extensions execute in a separate process but are **not a security sandbox**. They run with the current user's permissions. Keep explicit approval, invalidate approval when extension code changes, and never describe the process boundary as containment against malicious code. Do not enable automatic extension execution from untrusted sources.

## Artifact immutability

This review did not modify the supplied `.deb`, ZIP, tarball, or the existing checksums. The maintained patch is applied only to a temporary source extraction for tests and future controlled builds. A future versioned package must be reviewed and published separately.
