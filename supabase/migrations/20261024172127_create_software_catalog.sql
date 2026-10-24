-- Public, read-only mirror of the canonical software.json catalogue.
-- Write access is reserved for the trusted GitHub Actions sync job.
create table if not exists public.software_catalog (
  id text primary key,
  slug text not null unique,
  name text not null,
  version text not null,
  summary text not null,
  description text not null,
  category text not null,
  status text not null check (status in ('released', 'testing', 'planned', 'archived')),
  type text not null check (type in ('desktop', 'web', 'cli', 'library', 'extension')),
  platforms text[] not null default '{}',
  tags text[] not null default '{}',
  keywords text[] not null default '{}',
  features text[] not null default '{}',
  detail_url text not null,
  source_url text not null default '',
  release_url text not null default '',
  icon text not null,
  icon_image text not null,
  preview_image text not null,
  preview_alt text not null,
  updated_at date not null,
  sort_order integer not null default 0,
  published boolean not null default true,
  synced_at timestamptz not null default now()
);

alter table public.software_catalog enable row level security;
revoke all on table public.software_catalog from public, anon, authenticated;
grant select on table public.software_catalog to anon;

drop policy if exists software_catalog_public_read on public.software_catalog;
create policy software_catalog_public_read
  on public.software_catalog
  for select
  to anon
  using (published is true);

create index if not exists software_catalog_published_order_idx
  on public.software_catalog (published, sort_order, name);
