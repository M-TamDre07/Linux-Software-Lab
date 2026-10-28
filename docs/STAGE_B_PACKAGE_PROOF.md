# Stage B — Package proof and acceptance criteria

The Software Center package workflow is a build-and-test pipeline, not a release publisher. It must prove that the source tests pass, the wheel contains required runtime/catalogue files, the Debian package has expected metadata and entry points, and the candidate can be installed, smoke-tested, and purged in a Debian 13 container.

## What the workflow proves

- Ruff, Python compilation, and the Software Center test suite pass before packaging.
- The wheel contains the CLI, GUI, shared catalogue/installer code, bundled catalogue/index, and icon assets.
- The generated `.deb` contains package metadata, CLI/GUI entry points, desktop integration, and icon assets.
- Debian 13 can install the candidate and satisfy declared runtime dependencies; the installed CLI starts, the GUI module imports in offscreen mode, and package purge removes the package.
- SHA-256 values are generated for the candidate wheel and `.deb`; the workflow artifact is retained for 14 days.

## What it does not prove

- The package is not a stable release, signed artifact, or public download.
- A GUI module import is not an end-to-end visual test on a real desktop session.
- Testing on Debian 13 does not establish compatibility with every Debian derivative, Ubuntu release, Fedora, Arch, or other distributions.
- A green build does not authorize publishing or updating catalogue lifecycle to `released`.

## Acceptance gate

Do not publish the package until the workflow is green, the artifact and checksum are inspected, version/lifecycle metadata is reviewed, and a maintainer explicitly approves the release. Vercel deployment and Supabase writes are outside this stage.
