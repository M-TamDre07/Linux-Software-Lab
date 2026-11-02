# Linux Software Lab Center — development preview

Linux Software Lab Center is the planned desktop launcher for people moving to Linux. It pairs a click-friendly Qt catalogue with a lightweight CLI that shares the same metadata reader, distro detector, artifact selector, integrity checks, and package-installation policy.

**Status: 0.1.0.dev1, development preview.** This is source code for testing, not a published, signed, distro-native launcher package. Only the Debian .deb installation adapter is implemented. RPM, Arch, Flatpak, AppImage, signed release metadata, package signing, unattended installation, and automatic upgrades are not yet enabled.

## Arti “container” pada launcher

Linux Software Lab Center berfungsi sebagai pusat katalog dan pengelolaan aplikasi: ia menunjukkan aplikasi, versi, kompatibilitas distro, sumber GitHub/website, dan tindakan instalasi atau menjalankan aplikasi. **MVP ini bukan container runtime dan bukan sandbox** yang menyalin semua aplikasi ke dalam satu file atau menjalankan aplikasi secara terisolasi. Paket yang dipasang tetap menjadi paket sistem/user sesuai mekanisme native distro, dan peluncuran aplikasi dijalankan sebagai pengguna biasa.

Pendekatan ini disengaja untuk migrasi dari Windows: pengguna pemula mendapat antarmuka klik, sementara pengguna profesional tetap mendapat CLI yang memakai core dan aturan kompatibilitas yang sama. Isolasi per aplikasi (misalnya melalui Flatpak) adalah format distribusi tersendiri dan hanya boleh ditampilkan saat paket/runtime serta integrasinya benar-benar tersedia dan diuji.

## What works in this MVP

- Offline-first catalogue for PaketScope and Sorot; bundled metadata is checked against the website's distribution index and version manifests by regression tests.
- Local distribution detection using /etc/os-release, including Debian/Ubuntu, Arch derivatives, Fedora/RHEL, and openSUSE/SUSE family hints.
- CPU architecture normalization such as x86_64/amd64 and aarch64/arm64.
- A shared artifact-selection policy for the GUI and CLI. Sorot's real 0.5.0 Beta .deb, .tar.gz, and .zip artifacts are listed; PaketScope is not falsely marked installable because it has no public release artifact in the catalogue.
- Download verification against the shared GitHub distribution index, the per-version release.json and SHA256SUMS, and the selected artifact SHA-256.
- A Debian installation adapter that first simulates APT, rejects transactions indicating removals, uses --no-remove and --no-install-recommends, and then invokes APT through Polkit only after explicit user confirmation.
- A GUI catalogue that follows the established Linux Software Lab contrast, spacing, status, and product-list patterns. Searching, source links, metadata refresh, and source archive downloads are supported.
- Terminal subcommands for distro detection, listing, metadata, verified download, local-file verification, install review, status, refresh, and diagnostics.

## Develop locally

From the repository root, on a Linux desktop with Python 3.10+:

~~~bash
cd apps/software-center
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui,test]'
~~~

Run the GUI:

~~~bash
lsl-center
~~~

Run the CLI:

~~~bash
lsl detect
lsl list
lsl info sorot
lsl download sorot --format zip
lsl ecosystem
lsl ecosystem --json
lsl doctor
~~~

`lsl ecosystem` reports the canonical GitHub, website and launcher portal links, the active local catalogue source, detected system profile, reviewed local integration IDs, and enabled installation adapters. `--json` provides the same local facts for scripts and support diagnostics. This command deliberately performs no network health probe and does not make changes to the system. `lsl --version` prints the installed launcher version.

Refresh the user's local metadata cache from the official repository:

~~~bash
lsl refresh
~~~

The refresh command prompts for the exact confirmation word REFRESH before downloading. Both documents and every referenced release manifest must validate before the cache snapshot is activated. When the network is unavailable or a manifest is invalid, the previous verified snapshot or bundled catalogue remains available.

The desktop GUI also checks catalogue metadata on launch and every 15 minutes while it is open. This is metadata refresh only: it does not install a new application build, change APT packages, or upgrade the operating system. Users still start package operations manually, review the APT simulation, and confirm the privileged transaction.

## Install behavior and limitations

The launcher never substitutes another distro's package. The current PaketScope 3.0.0.dev5 and Sorot 0.7.1–0.7.3 builds have .deb artifacts whose manifests require Debian 13 specifically; Ubuntu 24.04 and other Debian-family derivatives are not considered compatible with those artifacts. Compatibility is evaluated from the manifest's distribution and minimum-OS metadata, CPU architecture, and installed package-manager tools. The app status remains Beta/testing; SHA-256 verifies bytes against release metadata, **not the publisher's cryptographic signature**. The package manager simulation and a separate confirmation are required before the privileged operation.

Do not run the entire launcher with sudo. Start it as a normal user so the system can request package-manager authorization at the installation boundary.

The current source archive does not contain a publisher-signed release manifest. This preview is intended for review and testing, preferably inside a recoverable virtual machine. Do not broadly recommend one-click installation until the project has signed release metadata/artifacts, signature/key-rotation rules, clean-install tests for each supported distribution, and reviewed privilege handling.

### Current artifact availability

- Sorot 0.7.3 Beta/testing: Debian 13 .deb, source tar.gz, ZIP, and Python wheel are indexed. Earlier versions remain archived.
- PaketScope 3.0.0.dev5 testing: Debian 13 .deb, source tar.gz, Python wheel, and a source patch are indexed. The patch is source material, never an installable package.
- Arch Linux remains planned for Sorot; no validated .pkg.tar.zst is published. PaketScope Arch/Fedora package recipes are experimental and unsupported.
- Fedora/RHEL, SUSE, Flatpak, AppImage: no native installation adapter is enabled in this MVP.

The app catalogue never treats a planned format as a download. Each family adapter must be implemented and tested before the product card can show installation as available.

## Extending the app container safely

The catalogue can grow from the shared GitHub metadata without granting remote records permission to execute local commands. Local launch targets live in `lsl_center/integrations.py`, a reviewed allowlist used by the GUI and CLI. A product without a local integration remains visible with its website/source links; the launcher does not guess a command from the product name.

The source-of-truth flow, local integration boundary, new-product checklist, and release-readiness limits are documented in [APP_CONTAINER_AND_INTEGRATIONS.md](../../docs/APP_CONTAINER_AND_INTEGRATIONS.md).

## Tests

From this directory:

~~~bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
ruff check lsl_center tests
python -m compileall -q lsl_center
~~~

The tests cover distro and architecture detection, shared selector behavior, manifest/checksum agreement, fail-closed package selection, the CLI's machine-readable output, metadata cache validation, and an offscreen GUI smoke test. They do not replace real package installation tests in disposable Debian, Fedora, SUSE, and Arch virtual machines.

## Design boundary

The catalogue/detail-page visual standard is documented at ../../docs/PRODUCT_UI_STANDARD.md. This product uses the established card hierarchy and design tokens rather than defining an unrelated visual system. The shared GUI/CLI and packaging architecture is described in ../../docs/LAUNCHER_AND_DISTRIBUTION_ARCHITECTURE.md.

The repository's static website is still published only from public/. This native application lives under apps/software-center/ and must not be imported as a separate Vercel website.
