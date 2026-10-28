# Pre-Vercel readiness gate

This is an internal project checklist, not a vendor certification. The Vercel project must remain untouched until the maintainer explicitly authorizes deployment work.

## Current verified state

- [x] Canonical website catalogue is the source of truth; launcher distribution metadata has a deterministic sync/check.
- [x] Website quality workflow passes on the current main branch.
- [x] CodeQL passes on the current main branch.
- [x] Supabase Security Advisor reports no security lints at the latest audit.
- [x] Supabase catalogue mirror and CI-generated catalogue quality report are integrated.
- [x] Admin dashboard is read-only and requires a server-managed active-admin row plus RLS.
- [x] Admin browser session survives reloads and is forced to reauthenticate after seven days from successful login.
- [x] Software Center package candidate workflow and proof documentation are on main; latest reviewed package workflow run passed.
- [x] Stale PRs #13, #23, and #32 were reviewed and closed as superseded by the current direct-main implementation. No release/tag was created.

## Must be complete before Vercel work

- [ ] Maintainer creates/validates their Supabase Auth user and adds the matching UUID to `public.lsl_admin_users` through the trusted Supabase Dashboard/SQL Editor.
- [ ] End-to-end admin sign-in is tested with an authorized account and an ordinary Auth account that must be denied. This is blocked until an active admin is provisioned.
- [ ] CAPTCHA provider is selected and configured in Supabase Auth; browser widget, exact hostname, and Content Security Policy are configured together. CAPTCHA is not active yet.
- [ ] Telegram OTP is implemented and deployed as a trusted server-side flow, not browser-only JavaScript. Confirm the group ID and each admin's Telegram numeric user ID; map Telegram IDs to Auth UUIDs; store the bot token only as a Supabase Edge Function secret; verify group membership server-side; expire and consume OTP challenges once; test revoked/non-member and rate-limit cases. OTP is not active yet.
- [ ] Session lifetime is enforced server-side where supported by the Supabase plan/settings, not only by the browser's seven-day cutoff.
- [ ] The current code and package workflows are green after the final auth implementation.
- [ ] Review CSP, redirect URLs, Supabase Auth settings, RLS/grants, public config, and documentation without exposing secrets.
- [ ] Capture the final readiness report and obtain explicit maintainer approval before any Vercel changes.

## Security notes

- The browser only uses the Supabase publishable key. Never expose `sb_secret_` or legacy service-role keys in website assets, browser storage, public commits, or client-side environment variables.
- The browser session stores access/refresh tokens in `localStorage` to support a seven-day remembered session. This is a deliberate usability trade-off: any same-origin JavaScript running through an XSS flaw could access those tokens, so keep CSP strict and prevent unsafe HTML injection. Do not store the user's password.
- The CAPTCHA CSP allowlist must be narrow and based on the chosen provider; do not solve integration by broadening script/frame/connect sources to wildcards.
- Telegram Bot API `getChatMember` is only guaranteed for other users when the bot is an administrator in that group. A user must also have started a private conversation with the bot before the bot can DM an OTP. See the [official Telegram Bot API documentation](https://core.telegram.org/bots/api).
- Supabase's session controls have plan and configuration constraints; confirm the project's available Auth session settings before relying on server-enforced seven-day expiry. See [Supabase session documentation](https://supabase.com/docs/guides/auth/sessions).

## Performance Advisor observation

The latest Supabase Performance Advisor reports four informational unused indexes on the catalogue/quality-report tables. These tables are new and have low usage, so this is not a security finding and does not justify dropping the indexes before there is representative query traffic. Revisit after usage grows.
