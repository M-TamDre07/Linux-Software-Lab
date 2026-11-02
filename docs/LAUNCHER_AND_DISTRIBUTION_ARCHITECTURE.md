# Linux Software Lab â€” unified launcher and distribution architecture

**Status: proposal / implementation contract.** This document guides the launcher and release work. It does not claim that future packages already exist and does not itself publish installers.

## Goal

Make Linux Software Lab approachable to people migrating from Windows while preserving a fast, scriptable workflow for technical users. Every application should appear in the same product catalogue, use the same visual language for its listing, and expose both a graphical installation path and a terminal workflow wherever a compatible package exists.

The planned launcher is a working name, **Linux Software Lab Center**; the final product name can be selected separately. The command-line entry point can be `lsl`. GUI and CLI must call the same metadata, compatibility, download, verification, and install services. They must not maintain separate lists or separate compatibility rules.

## What the uploaded `.flatpak` tells us

The supplied file is a **single-application Flatpak bundle**. Static strings identify app ID `ai.storyteller.artcraft-launcher`, command `artcraft-launcher`, runtime `org.freedesktop.Platform/x86_64/26.08`, a Flathub runtime repository, network/IPC access, X11/Wayland sockets, graphics access, and a `home` filesystem permission. This is useful as an example of a downloadable application bundle, not as a package format that can replace all distro packages.

Flatpak's official documenta¶»§q«^