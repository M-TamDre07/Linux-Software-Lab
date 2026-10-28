# Catalogue single-source contract

## Canonical source

`public/data/software.json` is the canonical source for public application metadata. The Software Center catalogue at `apps/software-center/lsl_center/data/catalog.json` is a generated mirror and must not be maintained independently.

The Sorot display version is derived from `apps/sorot/releases/index.json`; it is a generated label, not an independent release declaration. The release index and version manifests remain the source for Sorot version/channel/status/artifact metadata.

## Regeneration

From the repository root, run:

```bash
python scripts/sync_distribution_index.py --write
```

This regenerates the website and launcher distribution indexes from the Sorot release index and regenerates both catalogue files from the canonical website catalogue. Review the diff before committing.

## Validation

Run:

```bash
python scripts/sync_distribution_index.py --check
node --test tests/test_catalog_contract.cjs
python scripts/validate_catalog.py
python scripts/sync_supabase_catalog.py --check
```

The parity test fails when the launcher catalogue drifts from the canonical website catalogue. CI must fail on drift; do not weaken the check or silently overwrite the canonical catalogue. Supabase is a publication mirror, not the source of truth. Database writes remain a separate, explicitly reviewed operation.

## Change workflow

1. Edit the canonical website catalogue only when adding or updating public app metadata.
2. Update the product source/release manifest separately when changing an actual version or artifact.
3. Run the generator, inspect all generated diffs, and run the validation suite.
4. Open a pull request with test evidence. Do not mark a product released until its artifact URL is verified and its package checks pass.
