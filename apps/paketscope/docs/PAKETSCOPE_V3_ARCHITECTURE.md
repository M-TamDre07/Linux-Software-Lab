# PaketScope 3 — native architecture

Status: development proposal / active refactor. This document describes the intended architecture and distinguishes implemented foundations from later work.

## Product boundary

PaketScope is a native Linux desktop application for Debian-family systems, with Debian and Ubuntu as the initial target. It is not a web application and must not be wrapped in a browser view. PySide6/Qt Widgets provides the desktop frontend, keyboard navigation, native window behaviour, dialogs, and accessibility hooks. The product may adopt familiar visual conventions from Windows and macOS without pretending to be either platform or copying proprietary assets.

The companion Linux Software Lab website is a separate static catalogue. It documents the software and provides verified release links; it does not host or execute the desktop application as a Python web function.

## Layers

```text
Qt Widgets frontend (views, input, dialogs, presentation)
                    |
                    v
Application services (use cases, orchestration, UI-independent validation)
                    |
           +--------+---------+
           v                  v
Domain models & rules     Local file workflows
(normalized records,      (CSV, encrypted backup,
snapshots, parsers)       explicit JSON restore)
           |
           v
Operating-system adapters
(APT/dpkg, Flatpak, command runner, diagnostics)
           |
           v
Debian / Ubuntu user session and package metadata
```

### Frontend

- Keep widgets, event handlers, progress, accessible names, and dialog state in the Qt layer.
- No HTML/WebView/Electron shell is used for PaketScope's desktop interface.
- Work-intensive reads run off the GUI thread, with results delivered back to the UI thread.
- The presentation can be refreshed independently of the service and domain layers.

### Local backend and application services

- `paketscope/services.py` is the use-case boundary consumed by the Qt frontend.
- Services coordinate inventory scanning, explicit update checks, CSV export, encrypted backup creation, and user-requested backup restoration.
- Services do not accept arbitrary shell strings, add sudo, mutate package state, or send inventory data to a remote API.
- Domain parsing and OS command invocation remain separate modules; tests can exercise the service layer without opening a GUI.

### OS adapters

- `commands.py` resolves executables, passes argument arrays with `shell=False`, sets a timeout and stable locale, and returns structured results.
- `collectors.py` reads supported APT/dpkg and Flatpak inventory.
- `updates.py` runs only when a user requests it. Flatpak remote checks can make network requests, so the UI must communicate this before starting.
- Unsupported sources should produce a diagnostic rather than a fabricated empty result.

### Local data and privacy

- Inventory scans and package names remain local. There is no remote application backend, user account, analytics, or telemetry.
- Exported inventory can contain package names and versions; exports use owner-only permissions on POSIX and atomic replacement.
- Encrypted backup uses authenticated encryption. A restored JSON file is deliberately unencrypted and must require an explicit save action.
- Persistent scan history or preferences must be designed as a separate, documented local-storage feature. History must not be enabled silently; retention and delete controls are required before adding it.

## Distribution boundary

Vercel publishes only the static website in `public/`. It is not a build or release channel for the Qt executable. Keep PaketScope desktop builds separate from the web project's deployment pipeline. The Vercel project named `paketscope` currently fails with `PYTHON_ENTRYPOINT_NOT_FOUND` because it is configured as a Python web-function project; it should not be treated as the desktop-app distribution target.

For the desktop release path, select and test formats deliberately (for example, a Debian package and/or Flatpak). Before calling any build a release, define supported Debian/Ubuntu versions, verify install/launch/uninstall on clean systems, test permissions and update behaviour, publish checksums and provenance, and document upgrade/recovery steps. Signed builds, sandboxing, and reproducibility are release gates, not assumptions.

## Implementation stages

1. **Service boundary** — move use-case orchestration and file operations behind a UI-independent service facade; add service-level tests.
2. **Native UX** — evolve the Qt dashboard, navigation, detail view, progress/cancellation and empty/error states without coupling widgets to subprocess details.
3. **Reliability** — expand adapter contract tests, malformed-command-output tests, accessibility checks, and integration tests on supported Debian/Ubuntu releases.
4. **Packaging** — build and verify the selected native package formats in isolated CI; do not point Vercel at the desktop source.
5. **Public release review** — dependency/security review, privacy review, documentation, release notes, checksums, and a clear support/reporting process.

## Current limits

This branch begins stage 1 and some visual refinement. It is not yet a stable PaketScope 3 release. Do not change the public catalogue's release status or publish an installer until the remaining stages are verified.
