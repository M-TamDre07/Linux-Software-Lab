# Pre-Vercel readiness gate

This is an internal project checklist, not a vendor certification. The Vercel project must remain untouched until the maintainer explicitly authorizes deployment work.

## Current verified state

- [x] Canonical website catalogue is the source of truth; launcher distribution metadata has a deterministic sync/check.
- [x] Website quality workflow and CodeQL were recorded as passing in the last readiness review; re-check current default-branch runs before release.
- [x] Supabase catalogue mirror and CI-generated catalogue quality report are integrated.
- [x] Admin dashboard is read-only and requires a server-managed active-admin row plus RLS.
- [x] The current database query confirmed one active row in `public.lsl_admin_users` for the configured maintainer UUID. This confirms registry provisioning only; it does not prove the matching Auth login works end-to-end.
- [x] Admin browser session survives reloads and has a client-side seven-day reauthentication cutoff.
- [x] Software Center package candidate workflow and proof documentation are on main; the latest reviewed package workflow run was recorded as passing.
- [x] Stale PRs #13, #23, and #32 were reviewed and closed as superseded by the current direct-main implementation. No release/tag was created.
- [x] Supabase Edge Function inventory was checked: no Edge Functions are currently deployed.
- [ ] **New security finding:** Supabase Security Advisor currently reports leaked-password protection disabled. Enable it in Supabase Auth password/security settings and verify the finding clears before production rollout.
- [ ] Current CI/workflow state has not yet been re-verified after this review; inspect latest main-branch results before release.

## Must be complete before Vercel work

- [ ] Test end-to-end admin sign-in using the intended Supabase Auth identity; test a normal authenticated account and confirm it is denied admin access.
- [ ] Enable and verify Supabase leaked-password protection; review password strength and Auth security settings.
- [ ] Select and configure a CAPTCHA provider in Supabase Auth; configure the browser widget, exact production hostname, and Content Security Policy together. CAPTCHA is not active yet.
- [ ] Implement Telegram OTP as a trusted server-side flow, not browser-only JavaScript. LISO LAB identifiers are documented in [TELEGRAM_CONFIGURATION.md](TELEGRAM_CONFIGURATION.md): group ID `-1004361361948` and bot ID `8258093251`. Confirm each admin's Telegram numeric user ID; map Telegram IDs to Auth UUIDs; store the bot token only as a Supabase Edge Function secret; verify group membership server-side; expire and consume OTP challenges once; test revoked/non-member and rate-limit cases. OTP is not active yet.
- [ ] Enforce session lifetime server-side where supported by the Supabase plan/settings; a browser-only seven-day cutoff is not sufficient on its own.
- [ ] Re-run the full website, application, package, and security checks after the final auth implementation.
- [ ] Review CSP, redirect URLs, Supabase Auth settings, RLS/grants, public configuration, and documentation without exposing secrets.
- [ ] Capture a final readiness report and obtain explicit maintainer approval before any Vercel changes.

## Security notes

- The browser only uses the Supabase publishable key. Never expose `sb_secret_` or legacy service-role keys in website assets, browser storage, public commits, or client-side environment variables.
- The browser session stores access/refresh tokens in `localStorage` to support a seven-day remembered session. Any same-origin JavaScript executing through an XSS flaw could access those tokens; keep CSP strict and prevent unsafe HTML injection. Do not store the user's password.
- The CAPTCHA CSP allowlist must be narrow and based on the chosen provider; do not solve integration by broadening script/frame/connect sources to wildcards.
- Telegram Bot API `getChatMember` is only guaranteed for other users when the bot is an administrator in that group. A user must also have started a private conversation with the bot before the bot can DM an OTP. See the [official Telegram Bot API documentation](https://core.telegram.org/bots/api).
- Supabase session controls have plan and configuration constraints; confirm the project's available Auth session settings before relying on server-enforced expiry. See [Supabase session documentation](https://supabase.com/docs/guides/auth/sessions).

## Performance Advisor observation

The previous review recorded four informational unused indexes on new catalogue/quality-report tables with low usage. Recheck the current Performance Advisor before release; do not drop indexes without representative query-traffic evidence.
