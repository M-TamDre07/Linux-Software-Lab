# Stage C — Supabase reporting and catalogue intelligence

## Purpose

Stage C adds a small, deterministic catalogue-health assistant for the LISO LAB website. It helps the maintainer prioritize reviews; it is not a generative AI model, does not infer facts from the internet, and cannot publish or edit software records.

The source of truth remains `public/data/software.json` in Git. The public website and launcher continue to consume the canonical catalogue. Supabase is a read-only mirror for visitors and an admin-only reporting store.

## Components

- `scripts/catalog_intelligence.py`: explainable rule-based scoring; local JSON input/output, no network calls.
- `public/data/software.json`: canonical source data.
- `public.software_catalog`: existing public read-only mirror.
- `public.catalog_quality_runs`: aggregate report per trusted CI run.
- `public.catalog_quality_findings`: individual findings linked to a report.
- `public.lsl_admin_users`: existing server-managed admin allow-list.
- GitHub Actions: validation, report artifact retention, and trusted persistence to Supabase on pushes to `main` only. Pull-request runs never receive the persistence credential.

## Tables and authorization

| Table | Purpose | Public visitor | Active admin | Trusted CI |
|---|---|---|---|---|
| `software_catalog` | Website catalogue mirror | Read published rows | Read rows allowed by RLS | Synchronize |
| `lsl_admin_users` | Server-managed admin allow-list | No access | Read own membership | Provision through trusted owner process |
| `catalog_quality_runs` | Score and summary per analysis | No access | Read | Insert via secret server-side credential |
| `catalog_quality_findings` | Explainable rule findings | No access | Read | Insert via secret server-side credential |

The migrations `20261028024108_add_catalog_quality_reporting.sql` and `20261028024136_fix_catalog_quality_algorithm_version_check.sql` are applied to the Supabase project. Report tables have RLS enabled; authenticated users receive SELECT grants, and policies permit reads only for IDs present as active in `lsl_admin_users`. Browser roles receive no INSERT, UPDATE, or DELETE grants. Trusted GitHub Actions writes using `SUPABASE_SECRET_KEY`; the secret is never sent to browser code. The security advisor returned no findings after the migration.

## Scoring algorithm v1

Each entry starts at 100 points. Rule deductions are capped by a floor of zero:

| Rule | Deduction | Severity |
|---|---:|---|
| Missing search keywords | 8 | warning |
| Missing documented features | 8 | warning |
| Testing entry older than 30 days | 12 | warning |
| Planned entry has a release URL | 25 | error |
| Released entry has no release URL | 30 | error |
| Metadata older than 90 days | 5 | info |

Entry recommendation: score >= 90 = `ready`; 70–89 = `review`; below 70 = `needs_attention`. Overall score is the rounded arithmetic mean of entry scores. Overall recommendation is `needs_attention` if any error exists, otherwise `review` if any warning exists, otherwise `ready`.

This is a heuristic triage score, not a probability or an objectively calibrated quality measurement. The report includes rule codes and explanations so a human can verify every recommendation. The algorithm version is stored with each run so future versions can be compared honestly.

## Commands and expected use

```sh
python scripts/validate_catalog.py
python scripts/sync_supabase_catalog.py --check
python scripts/catalog_intelligence.py
python scripts/catalog_intelligence.py --output /tmp/liso-catalog-health.json
python -m unittest discover -s tests -v
```

Run analysis locally first; no database credentials are required. Report persistence is a later integration step and must only be enabled in trusted GitHub Actions with the secret stored in repository Actions secrets. Never place `SUPABASE_SECRET_KEY` in browser JavaScript, Vercel public variables, or report output.

## Release and safety gates

1. Canonical JSON validates against runtime and schema contracts.
2. Python tests cover scoring, deterministic output, malformed input, and rule findings.
3. Website quality workflow and Stage B package proof remain green.
4. Migration reviewed for least privilege and applied only by an authorized maintainer.
5. CI persistence runs only on pushes to `main`, uses the fixed project URL, never runs on pull requests, and verifies successful inserts; if findings fail to insert, it attempts to delete the incomplete summary row.
6. No automatic publication or source catalogue mutation based solely on the score.

## Current status and limitations

- The first trusted report was written successfully for commit `0ddee6c4af611eac9297debb84a7666c0d8e9a76`: 2 entries, score 100/100, recommendation `ready`, 0 findings. Later main commits also generated report rows.
- The admin page includes a read-only report panel. It uses the signed-in admin session and RLS; it never uses server credentials in the browser.
- The current `lsl_admin_users` table has zero active rows. Until the owner provisions the intended Auth user through a trusted process, no account can pass the dashboard's active-admin gate. There is deliberately no public admin signup or automatic admin provisioning.
- Vercel has not been deployed or reconfigured as part of this stage.
- The branch is not protected by GitHub branch protection. Direct-main workflow is the owner's chosen development mode; CI runs after pushes, so it does not block a bad commit before it reaches main. Review this trade-off with Grok and Claude during the final audit.
