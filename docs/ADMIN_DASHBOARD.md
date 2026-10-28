# Linux Software Lab — Admin dashboard

The static dashboard is available at `/admin/`. It is intentionally `noindex` and does not grant access just because the URL is known. Its client uses the public Supabase publishable key only, authenticates with Supabase Auth, then checks the authenticated UUID against `public.lsl_admin_users` before querying `public.software_catalog`.

## Current scope

- Sign in with an existing Supabase Auth user.
- Require an active row in `public.lsl_admin_users`; an authenticated account by itself is not an admin.
- Read the catalogue mirror, publication status, version, metadata update date, and sync timestamp.
- Search/filter the records and inspect a small health summary.
- Store access/refresh tokens in browser `localStorage` to survive reloads and browser restarts, with a hard client-side reauthentication cutoff seven days after password login; access tokens are refreshed only within that window. Logout requests local-session revocation and clears browser-held tokens even if the network call fails. API requests omit cookies. Because browser storage is readable by same-origin JavaScript, strict Content Security Policy and XSS prevention remain essential; this client-side cutoff is not a substitute for server-enforced session lifetime.
- Make no catalogue mutations and do not query other users, secrets, Auth administration endpoints, or private server settings.

This is a read-only operational dashboard, not a full management interface. `public/data/software.json` remains the catalogue source of truth. The maintainer currently works directly on `main` by explicit project decision, so each change must pass the repository's automated quality checks after the push and any failure must be corrected before further rollout. The GitHub Actions sync updates Supabase from the canonical source. Do not write directly to the read-only mirror from the browser.

## Administrator provisioning and verification

The current database check confirms one active row in `public.lsl_admin_users` for the intended maintainer UUID. This verifies allowlist provisioning only; it does not prove that the corresponding Supabase Auth user exists, can sign in, or is correctly authorized end-to-end.

To verify safely:

1. In Supabase Dashboard → Authentication → Users, confirm the intended maintainer Auth user exists and copy its UUID.
2. In SQL Editor, run this read-only check, replacing the placeholder with the UUID copied from the intended Auth user:

   ```sql
   SELECT user_id, active, note, created_at
   FROM public.lsl_admin_users
   WHERE user_id = 'REPLACE_WITH_AUTH_USER_UUID'::uuid;
   ```

3. Open `/admin/` and test sign-in with the intended account once the environment is available.
4. Test a normal authenticated account that has no active row; it must be denied access.
5. To revoke dashboard access, set the matching row's `active` to `false` or remove it from the trusted SQL Editor.

Never create an anonymous policy that allows users to insert or update `lsl_admin_users`. Do not use editable `user_metadata` as an authorization source. The authorization check must stay anchored to the server-managed row and RLS.

## Browser session regression checks

The client-side session parser now rejects and clears stored session data when any required token is empty, the expiry/authentication timestamps are not finite numbers, the authentication timestamp is in the future, or the seven-day reauthentication cutoff has elapsed. This is defensive browser-state handling only; it does not make localStorage trusted and does not enforce server-side session lifetime.

Before treating the dashboard as release-ready, verify these cases in a browser test environment:

- A valid session within the seven-day window proceeds to server-side identity and active-admin checks.
- Missing, malformed, or structurally incomplete JSON in the session key is cleared and the login panel remains available.
- Empty access/refresh tokens, non-finite timestamps, future-dated authentication time, and an authentication time older than seven days are rejected.
- An expired access token may refresh only when the refresh token is accepted by Supabase Auth and the original seven-day cutoff has not elapsed.
- A revoked/invalid refresh token results in local session clearing and no catalog data being shown.
- A normal authenticated user without an active admin row is denied, even if they manually create or alter localStorage.
- Logout clears browser-held tokens even when the network request fails; successful server-side revocation must be verified separately.
- Direct Data API requests are tested independently of the dashboard UI. A hidden panel or client-side state is not an authorization boundary.

Do not mark these cases as passing until they have actually been exercised. The current code hardening has been committed, but these are acceptance checks, not a claim that automated browser tests already exist or have passed.

## Live RLS and grants audit

A read-only query of the current database confirms RLS is enabled on all four dashboard-related tables: `lsl_admin_users`, `software_catalog`, `catalog_quality_runs`, and `catalog_quality_findings`.

- `lsl_admin_users`: authenticated users can SELECT only their own row; no INSERT/UPDATE/DELETE grants were found for `anon` or `authenticated`.
- `software_catalog`: anonymous SELECT is granted, but the anonymous RLS policy restricts results to rows where `published IS TRUE`. Authenticated catalogue reads require an active admin row. No mutation grants were found for `anon` or `authenticated`.
- `catalog_quality_runs` and `catalog_quality_findings`: authenticated SELECT is granted with policies requiring an active admin row. No mutation grants were found for `anon` or `authenticated`.

This is a policy/grant inspection, not a live request test. It does not prove the admin Auth login works end-to-end, and it does not establish a Telegram second factor. Recheck policies and grants after any migration or auth change.

## Password and session security

- The latest live Supabase Security Advisor check reports **Leaked Password Protection Disabled**. Enable leaked-password protection in the project's Auth password/security settings and verify the advisor finding clears before production rollout.
- The browser session is retained for at most seven days from successful password authentication, including across reloads. This is a client-side cutoff; it does not terminate a stolen token server-side at the exact seven-day mark. Supabase's server-enforced maximum session lifetime is a separate Auth setting and availability may depend on plan.
- Do not claim that CAPTCHA, Telegram OTP, or server-enforced seven-day session expiry is active until each is configured and tested.

## CAPTCHA and Telegram OTP status

- CAPTCHA is **not active yet**. It requires selecting a supported provider (for example Cloudflare Turnstile or hCaptcha), registering the exact site hostname, configuring the provider secret in Supabase Auth, and passing the provider token from the login form. Merely adding a visual checkbox does not protect the Auth endpoint.
- Telegram OTP is **not active yet**. A live inventory check found no deployed Supabase Edge Functions in this project. OTP needs a trusted server-side endpoint (a Supabase Edge Function is suitable), a Telegram bot token stored as a server secret, a fixed allowed group ID, an explicit mapping from each Supabase Auth UUID to that person's Telegram numeric user ID, group-membership verification via Telegram `getChatMember`, short-lived hashed OTP challenges, rate limits, and one-time consumption. The bot must be able to check membership (normally make it an administrator in the group) and each admin must start a private chat with the bot before it can DM them. Never send the bot token to the browser or commit it. LISO LAB's intended identifiers are group `-1004361361948` and bot `8258093251`; these are separate from the Tama Andrea Studio project. See [TELEGRAM_OTP_SECURITY_DESIGN.md](TELEGRAM_OTP_SECURITY_DESIGN.md) for design requirements.

## Security model and limitations

- The browser key is publishable and is not a secret; **RLS and SQL grants enforce access**.
- Never place an `sb_secret_` key or service-role key in HTML, JavaScript, Vercel public environment variables, local storage, or a public commit.
- The dashboard's `noindex` metadata reduces indexing but is not an access control. Auth and RLS are required.
- Admins can read only the tables and rows allowed by the current Supabase policies. This page does not expose the Supabase project, database credentials, all Auth users, logs, or every table.
- The current dashboard does not create catalog edits or GitHub commits. A future editor must use a trusted server-side GitHub App or another narrowly scoped authenticated service to create a reviewed change through a pull request; do not expose a GitHub personal access token in the browser.
- The static dashboard assumes the existing site's Content Security Policy allows connections to the configured Supabase project. Keep this origin exact; avoid broad wildcard `connect-src` rules. If enabling a hosted CAPTCHA widget, explicitly review CSP `script-src` and `frame-src` for that provider instead of weakening CSP globally.

## Verification

From the repository root:

```bash
python scripts/check_site_links.py
python -m unittest discover -s tests -v
node --check public/assets/js/admin.js
```

After changes to tables or policies, inspect Supabase Security Advisor and re-check RLS policies/grants. Login should be tested first with an authorized account and then with an ordinary Auth account, which must be denied admin access.
