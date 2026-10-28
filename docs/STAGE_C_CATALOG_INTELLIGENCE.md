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
- GitHub Actions: validation first; future report persistence must be a separate trusted job on the protected default branch only.

## Tables and authorization

| Table | Purpose | Public visitor | Active admin | Trusted CI |
|---|---|---|---|---|
| `software_catalog` | Website catalogue mirror | Read published rows | Read rows allowed by RLS | Synchronize |
| `lsl_admin_users` | Server-managed admin allow-list | No access | Read own membership | Provision through trusted owner process |
| `catalog_quality_runs` | Score and summary per analysis | No access | Read | Insert via secret server-side credential |
| `catalog_quality_findings` | Explainable rule findings | No access | Read | Insert via secret server-side credential |

The migration intentionally grants no report-table write access to browser roles. The SQL file is only a repository migration proposal until reviewed and deliberately applied to the Supabase project. No production database was changed by this PR.

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
5. Any future CI persistence job runs only on the protected default branch, uses fixed project URL, never runs on pull requests, and verifies writes before reporting success.
6. No automatic publication or source catalogue mutation based solely on the score.

## Not included yet

This stage defines the tables and local scoring engine. It does not add browser-side editing, call an external AI service, write to Supabase, deploy the website, or merge any pull request. The dashboard integration and trusted CI report persistence require separate tests and explicit review.
