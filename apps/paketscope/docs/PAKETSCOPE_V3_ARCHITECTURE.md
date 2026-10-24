# PaketScope 3 — native architecture

Status: active development refactor. This document records the current design
and separates implemented foundations from work that remains before a stable
release.

## Product boundary

PaketScope is a native Linux desktop application. Debian 13 (Trixie) is the
currently CI-validated native package target. Other Debian derivatives are not
automatically considered supported until dedicated packaging and installation
tests pass. Arch Linux, Fedora/RPM, openSUSE, and Alpine remain future work.

The Qt Widgets frontend is independent from the Linux Software Lab static
website. The website documents the software and can link to verified releases;
it does not host or run the desktop application as a web function.

## Layers

```text
Application startup (app.py)
          |
          v
Qt UI (ui/main_window.py + focused action modules)
          |
          v
Application services (services.py)
          |
          +---------------------------+
          |                           |
          v                           v
Domain types/parsers             Local file workflows
(domain.py)                      (backup.py, exporting.py)
          |
          v
Read-only source providers and OS adapters
(providers.py, collectors.py, updates.py, commands.py, package_manager.py, application_details.py)
          |
          v
Debian 13 user session and local package metadata
```

## Module responsibilities

- `app.py` creates the Qt application, applies the shared theme, and starts the
  event loop. It should remain a small entry point.
- `ui/main_window.py` constructs the main window and coordinates asynchronous
  tasks and shared UI state.
- `ui/models.py` owns the Qt inventory table model and search/source filtering.
- `ui/package_actions.py` presents APT search and transaction confirmation.
- `ui/application_details_dialog.py` shows metadata-backed function, package type, source/provenance notes, and Flatpak declared permissions without executing app code.
- `ui/inventory_actions.py` refreshes inventory and presents update/diagnostic
  results.
- `ui/data_actions.py` handles user-initiated CSV export and backup/restore
  dialogs.
- `ui/theme.py` owns column labels and the Qt stylesheet; `ui/workers.py`
  supplies a bounded background-task wrapper and result/error signals.
- `services.py` coordinates application use cases without owning widget layout
  or raw package-manager command strings.
- `domain.py` contains normalized records and pure parsers.
- `providers.py` defines the explicit read-only provider contract; `collectors.py` registers built-in APT/dpkg and Flatpak sources. Custom providers can be injected by a custom build, but are not discovered/imported automatically.
- `application_details.py` reads source-attributed details. APT policy data is described only as a currently available repository for the exact installed version, not proof of historical installation origin.
- `commands.py`, `collectors.py`, `updates.py`, and `package_manager.py`
  encapsulate OS command execution and Debian/Flatpak integration.
- `backup.py` and `exporting.py` implement local file/backup behaviour.

Preserve the dependency direction: presentation calls services or focused
adapters; parsers and domain rules should not import Qt widgets. Do not couple
core models to APT-specific command syntax. A future package backend should
implement its own adapter and tests while reusing domain/UI interfaces where
appropriate.

## Inventory provider extension contract

A provider returns normalized, read-only inventory through `InventoryProvider`
and `ProviderResult`. `PaketScopeService` accepts an explicit iterable of
providers, and the GUI source filter is populated from the available sources.
This is a source-level extension point, not an unrestricted runtime plugin
loader. Inventory providers must not mutate packages, execute discovered files,
or make undisclosed network requests. A provider that adds install/remove
functionality needs a separately reviewed mutation and privilege design.

## System and privilege boundary

Inventory collection is local and read-only. Read commands use argument arrays,
explicit timeouts, stable locale handling, and no shell. APT mutation is limited
to one selected package, validates its identifier, simulates first, shows the
proposed changes for confirmation, and delegates the fixed operation through
polkit. The interface itself must run as the regular user. Essential/Protected and required/important packages are blocked from remove/purge, transactions that would remove additional packages are refused, and the approved APT plan is rechecked immediately before privileged execution. Flatpak mutation,
remote inventory, accounts, telemetry, and background package changes remain
out of scope.

The user-triggered Flatpak update check can contact configured remotes. The APT
update display uses cached local metadata and does not run `apt update` for the
user. Exported package information can be sensitive; backups are encrypted but
CSV and decrypted JSON are intentionally plaintext.

## Implementation status

- [x] Introduce a UI-independent application-service boundary and service tests.
- [x] Separate the application entry point, main window, UI models, theme,
      background worker, and feature-specific action handlers.
- [x] Add guarded APT install/remove/purge flows with simulation, confirmation,
      validated identifiers, and polkit authorization.
- [x] Add Python tests, import/undefined-name checks, and Debian 13 CI that builds
      the `.deb`, installs it in a clean container, checks the installed module
      and launcher, purges it, and checks package-owned paths are removed.
- [x] Document module responsibilities, test commands, contribution practices,
      and current package compatibility.
- [ ] Exercise the graphical application on a real Debian 13 desktop, including
      cancellation, failure, accessibility, and display/session behaviours.
- [ ] Validate Ubuntu, Linux Mint, and any other planned derivative separately.
- [ ] Complete dependency/security review and independent security assessment.
- [ ] Define stable release signing, provenance, upgrade/recovery guidance, and
      public support/reporting expectations.

CI results do not replace real desktop tests or an independent security review.
Do not claim stable status or advertise the development artifact as a final
release until the remaining release gates are complete.
