-- Ensure the trusted Vercel server credential can operate the private OTP tables.
grant all on table public.lsl_admin_telegram_links to service_role;
grant all on table public.lsl_admin_telegram_link_challenges to service_role;
grant all on table public.lsl_admin_otp_challenges to service_role;
grant all on table public.lsl_admin_otp_verified_sessions to service_role;
