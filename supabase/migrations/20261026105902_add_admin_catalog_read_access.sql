-- Admin access registry for the private control room.
-- Rows can only be provisioned by a trusted owner through SQL/Dashboard tooling.
create table if not exists public.lsl_admin_users (
  user_id uuid primary key references auth.users (id) on delete cascade,
  active boolean not null default true,
  note text not null default '',
  created_at timestamptz not null default now()
);

alter table public.lsl_admin_users enable row level security;
revoke all on table public.lsl_admin_users from public, anon, authenticated;
grant select on table public.lsl_admin_users to authenticated;

drop policy if exists lsl_admin_users_select_self on public.lsl_admin_users;
create policy lsl_admin_users_select_self
  on public.lsl_admin_users
  for select
  to authenticated
  using (user_id = (select auth.uid()));

-- Keep anonymous visitors read-only, and reveal unpublished rows only to active admins.
grant select on table public.software_catalog to authenticated;
drop policy if exists software_catalog_admin_read on public.software_catalog;
create policy software_catalog_admin_read
  on public.software_catalog
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.lsl_admin_users
      where user_id = (select auth.uid())
        and active is true
    )
  );
