-- Telegram second factor for the LISO LAB admin dashboard.
-- All challenge writes and verification are server-only; RLS enforces the factor on every protected read.

create table if not exists public.lsl_admin_telegram_links (
  user_id uuid primary key references auth.users(id) on delete cascade,
  telegram_user_id bigint not null unique check (telegram_user_id > 0),
  linked_at timestamptz not null default now()
);

create table if not exists public.lsl_admin_telegram_link_challenges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  auth_session_id uuid not null,
  token_hash text not null check (token_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '10 minutes'),
  consumed_at timestamptz
);
create index if not exists lsl_admin_link_challenges_user_created_idx
  on public.lsl_admin_telegram_link_challenges(user_id, created_at desc);

create table if not exists public.lsl_admin_otp_challenges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  auth_session_id uuid not null,
  code_hash text not null check (code_hash ~ '^[0-9a-f]{64}$'),
  attempts smallint not null default 0 check (attempts between 0 and 5),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '5 minutes'),
  consumed_at timestamptz
);
create index if not exists lsl_admin_otp_challenges_user_created_idx
  on public.lsl_admin_otp_challenges(user_id, auth_session_id, created_at desc);

create table if not exists public.lsl_admin_otp_verified_sessions (
  user_id uuid not null references auth.users(id) on delete cascade,
  auth_session_id uuid not null,
  verified_at timestamptz not null default now(),
  expires_at timestamptz not null,
  primary key (user_id, auth_session_id)
);

alter table public.lsl_admin_telegram_links enable row level security;
alter table public.lsl_admin_telegram_link_challenges enable row level security;
alter table public.lsl_admin_otp_challenges enable row level security;
alter table public.lsl_admin_otp_verified_sessions enable row level security;

revoke all on public.lsl_admin_telegram_links from public, anon, authenticated;
revoke all on public.lsl_admin_telegram_link_challenges from public, anon, authenticated;
revoke all on public.lsl_admin_otp_challenges from public, anon, authenticated;
revoke all on public.lsl_admin_otp_verified_sessions from public, anon, authenticated;

create or replace function public.issue_lsl_admin_telegram_link(
  p_user_id uuid, p_session_id uuid, p_token_hash text
) returns boolean
language plpgsql security definer
set search_path = pg_catalog, public
as $$
declare
  v_admin boolean;
  v_recent integer;
begin
  if p_user_id is null or p_session_id is null or p_token_hash !~ '^[0-9a-f]{64}$' then
    return false;
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':telegram-link', 0));
  select exists(select 1 from public.lsl_admin_users where user_id=p_user_id and active)
    into v_admin;
  if not v_admin then return false; end if;
  select count(*) into v_recent
    from public.lsl_admin_telegram_link_challenges
    where user_id=p_user_id and created_at > now() - interval '15 minutes';
  if v_recent >= 3 then return false; end if;
  update public.lsl_admin_telegram_link_challenges
    set consumed_at=now()
    where user_id=p_user_id and consumed_at is null;
  insert into public.lsl_admin_telegram_link_challenges
    (user_id,auth_session_id,token_hash)
    values (p_user_id,p_session_id,p_token_hash);
  return true;
end;
$$;

create or replace function public.consume_lsl_admin_telegram_link(
  p_token_hash text, p_telegram_user_id bigint
) returns boolean
language plpgsql security definer
set search_path = pg_catalog, public
as $$
declare
  v_challenge public.lsl_admin_telegram_link_challenges%rowtype;
begin
  if p_token_hash !~ '^[0-9a-f]{64}$' or p_telegram_user_id is null or p_telegram_user_id <= 0 then
    return false;
  end if;
  select * into v_challenge
    from public.lsl_admin_telegram_link_challenges
    where token_hash=p_token_hash and consumed_at is null and expires_at > now()
    order by created_at desc
    limit 1
    for update;
  if not found then return false; end if;
  if not exists(select 1 from public.lsl_admin_users where user_id=v_challenge.user_id and active) then
    update public.lsl_admin_telegram_link_challenges set consumed_at=now() where id=v_challenge.id;
    return false;
  end if;
  if exists(select 1 from public.lsl_admin_telegram_links where telegram_user_id=p_telegram_user_id and user_id<>v_challenge.user_id) then
    update public.lsl_admin_telegram_link_challenges set consumed_at=now() where id=v_challenge.id;
    return false;
  end if;
  insert into public.lsl_admin_telegram_links(user_id,telegram_user_id)
    values(v_challenge.user_id,p_telegram_user_id)
    on conflict(user_id) do update
      set telegram_user_id=excluded.telegram_user_id, linked_at=now();
  update public.lsl_admin_telegram_link_challenges set consumed_at=now() where id=v_challenge.id;
  return true;
end;
$$;

create or replace function public.issue_lsl_admin_otp(
  p_user_id uuid, p_session_id uuid, p_code_hash text
) returns boolean
language plpgsql security definer
set search_path = pg_catalog, public
as $$
declare
  v_admin boolean;
  v_recent integer;
begin
  if p_user_id is null or p_session_id is null or p_code_hash !~ '^[0-9a-f]{64}$' then
    return false;
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_session_id::text || ':otp', 0));
  select exists(select 1 from public.lsl_admin_users where user_id=p_user_id and active)
    into v_admin;
  if not v_admin then return false; end if;
  if not exists(select 1 from public.lsl_admin_telegram_links where user_id=p_user_id) then
    return false;
  end if;
  select count(*) into v_recent
    from public.lsl_admin_otp_challenges
    where user_id=p_user_id and auth_session_id=p_session_id
      and created_at > now() - interval '15 minutes';
  if v_recent >= 5 then return false; end if;
  if exists(select 1 from public.lsl_admin_otp_challenges
      where user_id=p_user_id and auth_session_id=p_session_id
        and created_at > now() - interval '60 seconds') then
    return false;
  end if;
  update public.lsl_admin_otp_challenges
    set consumed_at=now()
    where user_id=p_user_id and auth_session_id=p_session_id and consumed_at is null;
  delete from public.lsl_admin_otp_verified_sessions
    where user_id=p_user_id and auth_session_id=p_session_id;
  insert into public.lsl_admin_otp_challenges(user_id,auth_session_id,code_hash)
    values(p_user_id,p_session_id,p_code_hash);
  return true;
end;
$$;

create or replace function public.consume_lsl_admin_otp(
  p_user_id uuid, p_session_id uuid, p_code_hash text
) returns boolean
language plpgsql security definer
set search_path = pg_catalog, public
as $$
declare
  v_challenge public.lsl_admin_otp_challenges%rowtype;
begin
  if p_user_id is null or p_session_id is null or p_code_hash !~ '^[0-9a-f]{64}$' then
    return false;
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_session_id::text || ':otp', 0));
  select * into v_challenge
    from public.lsl_admin_otp_challenges
    where user_id=p_user_id and auth_session_id=p_session_id
      and consumed_at is null and expires_at > now()
    order by created_at desc limit 1
    for update;
  if not found then return false; end if;
  if v_challenge.attempts >= 5 then
    update public.lsl_admin_otp_challenges set consumed_at=now() where id=v_challenge.id;
    return false;
  end if;
  if v_challenge.code_hash <> p_code_hash then
    update public.lsl_admin_otp_challenges
      set attempts=attempts+1,
          consumed_at=case when attempts+1 >= 5 then now() else null end
      where id=v_challenge.id;
    return false;
  end if;
  update public.lsl_admin_otp_challenges set consumed_at=now() where id=v_challenge.id;
  insert into public.lsl_admin_otp_verified_sessions(user_id,auth_session_id,expires_at)
    values(p_user_id,p_session_id,now()+interval '8 hours')
    on conflict(user_id,auth_session_id) do update
      set verified_at=now(),expires_at=excluded.expires_at;
  return true;
end;
$$;

revoke all on function public.issue_lsl_admin_telegram_link(uuid,uuid,text) from public, anon, authenticated;
revoke all on function public.consume_lsl_admin_telegram_link(text,bigint) from public, anon, authenticated;
revoke all on function public.issue_lsl_admin_otp(uuid,uuid,text) from public, anon, authenticated;
revoke all on function public.consume_lsl_admin_otp(uuid,uuid,text) from public, anon, authenticated;
grant execute on function public.issue_lsl_admin_telegram_link(uuid,uuid,text) to service_role;
grant execute on function public.consume_lsl_admin_telegram_link(text,bigint) to service_role;
grant execute on function public.issue_lsl_admin_otp(uuid,uuid,text) to service_role;
grant execute on function public.consume_lsl_admin_otp(uuid,uuid,text) to service_role;

-- Enforce Telegram second factor at the database boundary, not merely in the browser.
drop policy if exists software_catalog_admin_read on public.software_catalog;
create policy software_catalog_admin_read on public.software_catalog
for select to authenticated
using (
  exists (
    select 1 from public.lsl_admin_users a
    join public.lsl_admin_otp_verified_sessions v on v.user_id=a.user_id
    where a.user_id=(select auth.uid()) and a.active is true
      and v.auth_session_id=((select auth.jwt())->>'session_id')::uuid
      and v.expires_at > now()
  )
);

drop policy if exists catalog_quality_runs_admin_read on public.catalog_quality_runs;
create policy catalog_quality_runs_admin_read on public.catalog_quality_runs
for select to authenticated
using (
  exists (
    select 1 from public.lsl_admin_users a
    join public.lsl_admin_otp_verified_sessions v on v.user_id=a.user_id
    where a.user_id=(select auth.uid()) and a.active is true
      and v.auth_session_id=((select auth.jwt())->>'session_id')::uuid
      and v.expires_at > now()
  )
);

drop policy if exists catalog_quality_findings_admin_read on public.catalog_quality_findings;
create policy catalog_quality_findings_admin_read on public.catalog_quality_findings
for select to authenticated
using (
  exists (
    select 1 from public.lsl_admin_users a
    join public.lsl_admin_otp_verified_sessions v on v.user_id=a.user_id
    where a.user_id=(select auth.uid()) and a.active is true
      and v.auth_session_id=((select auth.jwt())->>'session_id')::uuid
      and v.expires_at > now()
  )
);
