# Prompter Overlay

**Status:** planned — project scaffold only.

Prompter Overlay is a proposed native Linux desktop teleprompter for reading a script during presentations, video recording, or calls. The goal is to solve one focused problem: make the speaker's script readable without turning the application into a complicated editor.

## Planned first-use workflow

1. Open or paste a script.
2. Adjust text size, scroll speed, position, and window dimensions.
3. Start, pause, and reset scrolling using clear controls and keyboard shortcuts.
4. Keep the script local unless a future, explicitly documented feature requires otherwise.

These are planning goals, not implemented features. Window transparency, always-on-top behaviour, keyboard shortcuts, Wayland/X11 compatibility, and screen-sharing behaviour need real desktop-environment tests before support is claimed.

## Directory policy

The implementation, tests, documentation, and packaging for this product belong in this directory. When development starts, add the appropriate source package, test suite, a project-specific `LICENSE`, a `CHANGELOG.md`, and packaging metadata. Select and document the license before publishing source code. A Debian `debian/` package directory should be added only after the app's dependencies and install/uninstall behaviour are verified.

There is no install command, release binary, or stable source package at this stage. Do not treat this README as evidence that the application is available.

The website page is `public/software/prompter-overlay.html`.
