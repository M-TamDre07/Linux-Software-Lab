# App Publishing Factory

**Status:** architecture and rollout plan only. The admin uploader, server-side GitHub integration, and automated package builder are not implemented yet. This document defines their boundaries so the repository does not ship a misleading or unsafe partial feature.

## Decision: a hybrid workflow

Automate repetitive setup, metadata validation, website integration, release indexing, checksum generation, and catalogue synchronization. Keep application-specific source code, runtime choices, build profiles, and release approvals as deliberate engineering work.

There should be one standard application directory contract, but not one universal build command that converts arbitrary code into every Linux package. A Python GUI, CLI tool, library, static website, and custom runtime have different build and installation requirements.

## Current implementation boundary

The repository already has:

- `templates/application/` and `scripts/scaffold_app.py` for creating a safe, non-overwriting project scaffold;
- `scripts/validate_app_manifest.py`, `scripts/validate_catalog.py`, and website/link/SEO regression checks;
- GitHub Actions for website quality, Software Center quality, CodeQL, Sorot manifest/checksum validation, and Supabase catalogue synchronization;
- immutable versioned Sorot artifacts and a canonical Sorot release index;
- an authenticated but read-only `/admin/` dashboard.

The scaffold currently creates `apps/<slug>/` only. It does not create a website page, upload source archives, build packages, register launcher commands, or publish releases. The current public catalogue remains `public/data/software.json`; the admin dashboard does not mutate it.

## Target publishing flow

### 1. Create a draft

A future admin wizard and the CLI developer workflow should use the same validation and scaffold rules. The intake should capture the stable slug, display name, accurate summary, type/category, platforms, licence decision, runtime/build profile, supported architectures, assets, and release intent.

The initial state must be `planned`. A template must never invent a licence, working source code, package, checksum, or supported distribution.

### 2. Stage uploads privately

Source archives and artwork, if uploaded, must first enter a private staging area—not `public/`, a public bucket, or the production catalogue.

A trusted server-side process must enforce upload size limits, allowed file types, archive entry and expanded-size limits, path-traversal protection, and a policy for symlinks/special files. Reject secrets such as `.env`, generated environments/caches, and uploaded GitHub Actions workflows. Record provenance and a content digest. Retries must be idempotent and must not silently overwrite an earlier submission.

Uploading a pre-built binary is a separate reviewed path; it is not proof that source is reproducible or that a package is compatible with a distro.

### 3. Use a trusted backend to open a GitHub PR

The current dashboard is read-only. A future publishing endpoint must:

1. authenticate the Supabase Auth session and verify an active row in `public.lsl_admin_users`;
2. validate all fields against strict schemas and allowlists;
3. use a dedicated GitHub App installation token stored only in backend secrets;
4. create an isolated branch and a pull request against `main`;
5. include the app scaffold, reviewed source/assets, and generated website metadata in that PR;
6. show the PR URL and workflow status in `/admin/`.

The browser must never receive a GitHub personal access token, GitHub App private key, Supabase secret key, or service-role key. The GitHub App should receive only the repository permissions required for content changes and pull requests, not workflow-file write permission for ordinary submissions.

Never write a submission directly to `main`, mutate the catalogue mirror from the browser, or bypass review/CI.

### 4. Validate before building

Pull-request checks should validate the application manifest, slug and path boundaries, licence decision, supported profile, dependency metadata, tests/docs, assets, website metadata and canonical URL, sitemap, release index, and checksum consistency.

Uploaded source is untrusted. Do not execute it in a web request handler. Validation jobs must not receive publishing credentials or signing keys. Never use a privileged `pull_request_target` workflow to check out and execute submitted code. Release signing/publishing must remain separate from validation of unreviewed changes.

### 5. Use explicit build profiles

The directory structure is universal; build adapters are not. Start with a small, reviewed set:

| Profile | Initial target | Boundary |
|---|---|---|
| Python / PySide6 desktop | Source archive and wheel; Debian package only when packaging metadata and install tests exist | Desktop integration and system dependencies must be declared and tested |
| Python CLI | Source archive and wheel; native packages only after validation | A wheel is not a standalone OS installer |
| Static web app | Product page/assets or versioned source archive | Do not show a desktop install button for web-only software |
| Custom runtime | No automatic build until a reviewed adapter exists | Build commands need code review and controlled runners |

The manifest may choose a known profile ID; it must not supply arbitrary shell commands, package-manager paths, privilege commands, or workflow YAML. Only formats actually built and tested in CI may be advertised as available.

### 6. Build immutable release artifacts

Build approved source in a controlled runner. Inspect package contents, run tests, and perform install/launch/uninstall checks in disposable environments appropriate to each advertised format. Generate the version manifest, `SHA256SUMS`, test report, and an SBOM where supported. Publish artifacts to a versioned GitHub Release or another explicitly approved artifact store.

Never overwrite a published version directory or its checksums. SHA-256 detects byte mismatches but does not authenticate a publisher if the artifact and digest come from the same mutable source. Signing, key rotation/revocation, and signature verification remain separate release-readiness requirements until implemented and tested.

### 7. Generate website, database, and launcher metadata

The intended integration pipeline keeps these outputs aligned:

- `apps/<slug>/application.json`: per-app technical contract;
- `apps/<slug>/releases/<version>/release.json` plus a canonical version index: actual version-specific artifact metadata;
- `public/data/software.json`: website catalogue record;
- `public/software/<slug>.html`: product page using the approved shared UI;
- `public/sitemap.xml`: canonical page discovery;
- `public/data/distribution-index.json` and the launcher index: pointers to real release manifests;
- `public/assets/images/`: reviewed, accurately labelled assets;
- launcher executable allowlist: only if a local target has been reviewed in application code.

Implementation must be additive and must not silently migrate the existing Sorot/PaketScope data model. A legacy migration should be a separate change with regression coverage.

After a reviewed PR is merged, GitHub remains the source repository. The existing workflow mirrors catalogue rows to Supabase. Supabase is not the package builder and must not become a source of shell commands. Vercel continues to publish only `public/`; application source and private staging objects must not be exposed by the static website.

### 8. Show truthful status in the website and terminal

Public statuses remain `planned`, `testing`, `released`, and `archived`. Internal workflow states (draft, submitted, validation failed, needs changes, approved, building, release candidate, published) must be separate from those public statuses. A green CI run alone does not mean a release is published.

The launcher may install only a real compatible artifact through a reviewed adapter for the detected distro family. The current launcher implements the APT/`.deb` path; RPM, Arch, Flatpak, AppImage, and signed-metadata support remain unavailable until each path is implemented and validated. Remote JSON must never supply executable commands.

## Rollout plan

1. **Foundation:** retain the shared template and strict validators; formalize the intake and release contract.
2. **Integration automation:** generate a draft product page/catalogue entry/sitemap update from validated per-app metadata and add drift checks.
3. **Admin intake:** implement private staging and a server-side GitHub App endpoint that creates PRs, not direct production changes.
4. **Build adapters:** begin with a proven profile and real versioned artifacts; add package formats only after clean install tests.
5. **Release assurance:** add provenance, SBOM, signing/key management, accessibility review, and tested upgrade/rollback behaviour.

Each phase must be independently testable and reversible. Do not present publishing as enabled in `/admin/` until its backend credentials and authorization flow are configured and tested.

## Acceptance criteria

The factory is ready for broad use when an authorized maintainer can create a draft in `/admin/`, receive a reviewable GitHub PR, see validation/build status, approve an immutable versioned release, and verify that the website, Supabase mirror, and launcher agree—without exposing secrets, executing unreviewed source with publishing credentials, overwriting a release, or advertising an artifact that was not actually built and tested.
