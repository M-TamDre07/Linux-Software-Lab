# Stage B — Package proof and acceptance criteria

The Software Center package workflow is a build-and-test pipeline, not a release publisher. It must prove that source tests pass, the wheel contains required runtime/catalogue files, the Debian package has expected metadata and entry points, and the candidate can be installed, smoke-tested, and purged in a Debian 13 container.

## What the workflow proves

- Ruff, Python compilation, and the Software Center test suite pass before packaging.
- The wheel contains the CLI, GUI, shared catalogue/installer code, bundled catalogue/index, and icon assets.
- The generated `.deb` contains package metadata, CLI/GUI entry points, desktop integration, and icon assets.
- Debian 13 can install the candidate and satisfy declared runtime dependencies; the installed CLI starts, the GUI module imports in offscreen mode, and purge removes both the package registration and its installed Python module directory.
- Python bytecode generation is disabled for the packaged CLI/GUI launchers so normal use does not leave untracked cache files that interfere with clean removal.
- SHA-256 values are generated for the candidate wheel and `.deb`, then checked with `sha256sum --check` before artifact upload.
- The workflow uploads the wheel, `.deb`, checksum manifest, and package-content inventory as a GitHub Actions artifact retained for 14 days. This is a CI artifact, not a public release.

## Compatibility status

| Environment | Evidence | Status |
|---|---|---|
| Debian 13 (Trixie), x86-64 CI container | Install, CLI version smoke test, offscreen GUI-module import, purge, and checksum validation | Verified by CI |
| Ubuntu releases | No dedicated install test in this stage | Not yet verified |
| Other Debian derivatives | No dedicated install test in this stage | Not yet verified |
| Fedora/RHEL-family, Arch, and other non-Debian distributions | No native package or install test in this stage | Not supported by this evidence |

“Verified by CI” means the package passed the stated automated checks in the named environment. It is not a claim that the GUI has been visually tested in a live desktop session or that all hardware and desktop environments are covered.

## What it does not prove

- The package is not a stable release, signed artifact, or public download.
- A GUI module import is not an end-to-end visual test on a real desktop session.
- Testing on Debian 13 does not establish compatibility with every Debian derivative, Ubuntu release, Fedora, Arch, or other distributions.
- A green build does not authorize publishing or updating catalogue lifecycle to `released`.

## Acceptance gate

Do not publish the package until the workflow is green, the candidate artifact and checksum manifest have been reviewed, version/lifecycle metadata is reviewed, and a maintainer explicitly approves the release. Vercel deployment and Supabase writes are outside this stage.
