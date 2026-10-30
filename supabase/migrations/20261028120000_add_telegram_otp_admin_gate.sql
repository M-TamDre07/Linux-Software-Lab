-- Telegram second-factor challenge/session storage and protected admin-data gateway.
-- Reviewed source migration only: do not apply to production until preview and security review pass.

create table if not exists public.lsl_admin_telegram_users (
  auth_user_id uuid primary key references auth.users(id) on delete cascade,
  telegram_user_id bigint not null unique check (telegram_user_id > 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  note text not null default ''
);

create table if not exists public.lsl_admin_telegram_otp_challenges (
  auth_user_id uuid primary key references auth.users(id) on delete cascade,
  code_hash text not null,
  attempts smallint not null default 0 check (attempts between 0 and 5),
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.lsl_admin_telegram_otp_sessions (
  session_hash text primary key check (session_hash ~ '^[0-9a-f]{64}$'),
  auth_user_id uuid not null references auth.users(id) on delete cascade,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists lsl_admin_telegram_sessions_user_idx
  on public.lsl_admin_telegram_otp_sessions (auth_user_id, expires_at desc);

alter table public.lsl_admin_telegram_users enable row level security;
alter table public.lsl_admin_telegram_otp_challenges enable row level security;
alter table public.lsl_admin_telegram_otp_sessions enable row level security;

revoke all on table public.lsl_admin_telegram_users from public, anon, authenticated;
revoke all on table public.lsl_admin_telegram_otp_challenges from public, anon, authenticated;
revoke all on table public.lsl_admin_telegram_otp_sessions from public, anon, authenticated;
grant all on table public.lsl_admin_telegram_users to service_role;
grant all on table public.lsl_admin_telegram_otp_challenges to service_role;
grant all on table public.lsl_admin_telegram_otp_sessions to service_role;

-- Verify and consume a challenge in one transaction, preventing OTP replay and concurrent double-use.
create or replace function public.lsl_consume_admin_telegram_otp(
  p_auth_user_id uuid,
  p_code_hash text,
  p_session_hash text
) returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  challenge public.lsl_admin_telegram_otp_challenges%rowtype;
begin
  select * into challenge
  from public.lsl_admin_telegram_otp_challenges
  where auth_user_id = p_auth_user_id
  for update;

  if not found or challenge.consumed_at is not null
     or challenge.expires_at <= now() or challenge.attempts >= 5 then
    return false;
  end if;

  if challenge.code_hash <> p_code_hash then
    update public.lsl_admin_telegram_otp_challenges
      set attempts = least(attempts + 1, 5)
      where auth_user_id = p_auth_user_id;
    return false;
  end if;

  update public.lsl_admin_telegram_otp_challenges
    set consumed_at = now()
    where auth_user_id = p_auth_user_id;

  insert into public.lsl_admin_telegram_otp_sessions(session_hash, auth_user_id, expires_at)
  values (p_session_hash, p_auth_user_id, now() + interval '8 hours');

  return true;
end;
$$;

revoke all on function public.lsl_consume_admin_telegram_otp(uuid, text, text) from public, anon, authenticated;
grant execute on function public.lsl_consume_admin_telegram_otp(uuid, text, text) to service_role;

-- OTP is only useful if browser-authenticated requests cannot bypass the gateway.
-- Public visitors keep the existing anon policy for published catalogue rows.
revoke select on table public.software_catalog from authenticated;
revoke select on table public.catalog_quality_runs from authenticated;
revoke select on table public.catalog_quality_findings from authenticated;
