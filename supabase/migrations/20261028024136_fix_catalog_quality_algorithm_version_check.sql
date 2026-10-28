alter table public.catalog_quality_runs
  drop constraint if exists catalog_quality_runs_algorithm_version_check;
alter table public.catalog_quality_runs
  add constraint catalog_quality_runs_algorithm_version_check
  check (algorithm_version ~ '^lsl-catalog-health-v[0-9]+$');
