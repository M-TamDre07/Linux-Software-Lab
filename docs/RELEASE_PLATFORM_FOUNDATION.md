# Release platform foundation and audit

**Status: implementation contract / audit findings.** This document records the current repository boundaries and the gates that must be satisfied before Linux Software Lab can offer end-to-end application publishing. It is not a claim that uploads, signed releases, or multi-distro packages already exist.

## Decisions

1. Keep `public/data/software.json` as the canonical public catalogue source. Generated catalogue copies and Supabase are mirrors, not competing authoring surfaces.
2. Keep the current `/admin/` dashboard read-only. A URL, signed-in session, or client-side role label must never be enough to publish or upload an artifact.
3. Reuse the existing application scaffold, manifest validator, distribution manifest schema, release-index synchronizer, catalogue validator, and Supabase synchronizer. Do not introduce a second schema or a second catalogue source.
4. Treat application lifecycle, release channel, artifact publication, and distribution compatibility as separate facts. A stable channel does not prove that an artifact has been published or that every Linux distribution has been tested.
5. Build and test artifacts in CI before publication. An uploaded file must not become an installable release merely because an administrator selected it.
6. Keep product-specific build systems where necessary. The shared platform standardizes inputs, evidence, integrity metadata, and publication gates; it does not force every app into the same runtime or packaging technology.

## Current-state audit (repository snapshot, 2026-10-27)

| Area | Existing foundation | Gap / release gate |
| --- | --- | --- |
| App template | `templates/application/`, `scripts/scaffold_app.py`, `scripts/validate_app_manifest.py` | The scaffold intentionally does not create app code, register a launcher entry, add catalogue content, or publish packages. |
| Public catalogue | `public/data/software.json` and `public/data/software.schema.json` | Every generated page, launcher catalogue, and database mirror must remain consistent with this source. |
| Distribution metadata | `docs/schemas/distribution-manifest.schema.json`, Sorot release index, `scripts/sync_distribution_index.py` | A manifest is evidence about named artifacts, not proof that those files are hosted or that the target OS has been tested. |
| Supabase mirror | `scripts/sync_supabase_catalog.py` and `supabase/migrations/` | Continue to sync from the canonical catalogue. Do not let the public browser write the mirror directly. |
| Admin | `public/admin/`, `docs/ADMIN_DASHBOARD.md` | Current dashboard is read-only. Upload and publication APIs are not an approved capability yet. |
| Launcher package | `.github/workflows/software-center-package.yml` on the PR branch | Build artifacts are review candidates until tests, clean-install checks, and publication gates pass. |
| PaketScope | `.github/workflows/paketscope-build.yml`, `apps/paketscope/debian/`, Python tests | Current Debian package version is `3.0.0~dev4`; the workflow labels tagged builds as development previews. Do not promote it to stable based on a successful build alone. |
| Sorot | `apps/sorot/releases/`, release-index workflow, site and launcher metadata | Version/channel, lifecycle, verified download URL, checksums, and tested distro support must agree. Do not weaken validation to hide missing evidence. |

## Canonical publication flow

```text
Application source + app manifest
            |
            v
      Pull request review
            |
            v
   Static validation + unit tests
            |
            v
 Product-specific reproducible build
            |
            v
 Install / launch / uninstall tests
            |
            v
 Artifact inspection + SHA-256
            |
            v
 Release manifest + release notes
            |
            v
 Verified immutable release storage
            |
            v
 Generated catalogue / distribution index
            |
            v
 Website + launcher + Supabase mirror
```

The pipeline must fail closed: if an earlier gate fails, later publication steps do not run. Sync jobs should be idempotent, report the exact source revision, and verify that the mirror matches the expected catalogue rows.

## Release record and artifact rules

- Every product has one stable slug and one canonical source directory: `apps/<slug>/`.
- App-level metadata describes the product and its supported runtime/OS matrix. Versioned distribution metadata describes a specific build and its actual artifacts.
- Every downloadable artifact needs an explicit format, version, architecture where applicable, target compatibility, SHA-256, and a verified HTTPS download URL.
- A source archive is not a native installer. A `.deb` does not establish support for Fedora, Arch, or every Debian-derived distribution.
- Never infer compatibility from a package-manager family alone. Record the exact OS/release and test environment used.
- `released` catalogue status requires a real, reachable HTTPS release URL as enforced by the catalogue validator. Until publication exists, use a non-released lifecycle even if the maintainer has selected a stable channel for the product.
- A checksum detects accidental or malicious artifact changes relative to the published checksum; it does not by itself authenticate the publisher. Signing and provenance are separate future controls.

## Admin upload security boundary

Do not add a direct browser-to-public-storage upload flow. When upload support is implemented, the server-side path must:

1. Authenticate the user and verify active administrator authorization from trusted database state; never authorize from user-editable profile metadata.
2. Accept only an explicit allowlist of artifact types and bounded file sizes. Reject path traversal, unexpected filenames, archives with unsafe paths, duplicate version/architecture tuples, and mismatched product IDs.
3. Store uploads in a private quarantine location, not the public download path.
4. Inspect metadata and calculate SHA-256 server-side. Never trust a checksum supplied by the browser.
5. Run required tests/build verification in a controlled CI or worker environment. Do not execute uploaded binaries or arbitrary scripts on the web server.
6. Require an explicit review/publish action before moving immutable artifacts into public release storage.
7. Write the release manifest and update the canonical catalogue through a reviewed, auditable workflow. The browser must not receive GitHub write tokens, Supabase service-role keys, or other server secrets.
8. Record actor, source revision, artifact digest, version, test evidence, and publication time. Provide a safe rollback path that does not silently replace an artifact at the same immutable URL.

The first implementation should keep publication gated behind GitHub Actions and reviewed pull requests. A direct admin publishing API should be considered only after the repository pipeline and permissions model are proven.

## Required quality gates

### Gate A — source and metadata
- Scaffold and manifest validator pass.
- Catalogue schema and link checks pass.
- IDs, slugs, version, channel, lifecycle, compatibility notes, and release URL agree.
- Generated files are regenerated by scripts rather than hand-edited where a generator exists.

### Gate B — artifact
- Build is performed from a reviewed commit/tag in CI.
- Package metadata and file list are inspected.
- SHA-256 is generated from the final artifact.
- Package installs and launches in a clean supported environment.
- Uninstall/purge leaves no package-owned executable, desktop entry, or installed module behind.
- No install command is generated from arbitrary manifest shell text.

### Gate C — security and supply chain
- Dependencies are pinned or locked where appropriate and audited.
- GitHub Actions permissions are least-privilege; third-party actions are pinned to reviewed immutable references.
- Secrets never enter public bundles, artifacts, logs, or client-side environment variables.
- Admin actions require server-side authorization and are auditable.
- No automatic execution of uploaded application code on the publishing host.

### Gate D — publication and mirrors
- The release URL is reachable over HTTPS and points to the intended version.
- The release manifest refers only to existing published artifacts with matching checksums.
- Website catalogue, launcher catalogue, generated distribution index, and Supabase mirror agree on product ID/version/status.
- The sync workflow verifies the resulting mirror and fails on drift.
- A rollback/recovery procedure is documented and tested.

## Implementation sequence

1. **Stabilize the current PR and CI:** resolve existing validator and GUI-test failures without weakening validation rules.
2. **Prove PaketScope packaging:** run the existing Debian 13 build/install/purge workflow, review failures and artifacts, then test the real desktop launch path. Keep the development-preview label until the release criteria are met.
3. **Prove the launcher package candidate:** pass core/GUI tests, inspect the generated `.deb` and wheel, and install/launch on a clean Debian/Ubuntu test environment.
4. **Make the contract executable:** add CI checks for cross-file consistency and artifact-manifest integrity using the existing schemas and scripts.
5. **Standardize app release manifests:** migrate Sorot and PaketScope one at a time, documenting product-specific exceptions instead of hiding them.
6. **Only then add upload quarantine and admin review:** the admin page remains read-only until server-side authorization, storage isolation, verification, and audit logging are implemented and tested.
7. **Deploy the accumulated website changes to Vercel after the current usage limit resets:** deployment is the final delivery step, not a substitute for passing repository checks.

## Definition of done for automated publishing

The feature is not complete until a maintainer can create a product from the scaffold, submit a reviewed version, build and verify the supported package, publish immutable artifacts with checksums, and see consistent metadata on the website, launcher, and Supabase—without manually editing multiple copies or granting the browser privileged credentials.


## Live Supabase read-only audit (2026-10-27)

The connected Linux Software Lab Supabase project was inspected without changing its schema or data:

- Security advisor returned **no findings** at the time of inspection.
- Performance advisor returned one informational `unused_index` notice for `software_catalog_published_order_idx`. With only two catalogue rows, this is not evidence of a performance problem; re-check after realistic usage before removing the index.
- The public schema currently contains `software_catalog` and `lsl_admin_users`, both with RLS enabled.
- The admin registry currently contains **zero active admin rows**. This may be intentional during setup, but the dashboard cannot grant admin access until the maintainer provisions an Auth user and adds the corresponding registry row through the trusted Supabase Dashboard/SQL Editor process documented in `docs/ADMIN_DASHBOARD.md`.
- The catalogue mirror currently has two published records (`paketscope` and `sorot`), both with lifecycle `testing` and empty `release_url` values. This matches the rule that publication status must not be elevated before a verified release URL exists.

These are point-in-time observations, not a permanent health guarantee. Re-run the advisors and read-only catalogue checks after relevant schema, policy, or sync changes. No migration or live data mutation was performed as part of this audit.
