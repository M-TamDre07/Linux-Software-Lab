# LISO LAB — Telegram OTP readiness and rollout

Status: implementation is prepared in draft PR #40's branch; it is **not active in production** until the migration, Telegram ID mapping, environment configuration, and end-to-end tests are completed.

## Flow

1. Supabase Auth validates the administrator's email/password.
2. A Vercel server-side endpoint verifies the Auth token and active row in `public.lsl_admin_users`.
3. The endpoint resolves the trusted Auth UUID → Telegram numeric user ID mapping in `public.lsl_admin_telegram_users`.
4. The bot checks the mapped user is currently in group `-1004361361948` using Telegram `getChatMember`.
5. The bot posts a six-digit OTP and login-audit notice to the **restricted admin group**. The notice includes account email, server timestamp, coarse device/browser class, Vercel-provided approximate location when available, and a masked IP. The group must contain only trusted admins because members can see the OTP.
6. A five-minute challenge stores only an HMAC verifier. Verification attempts are limited to five, and a database function locks and consumes the challenge atomically.
7. Success sets an eight-hour, Secure, HttpOnly, SameSite=Strict cookie. Admin catalog and quality data are fetched through server-side API routes which validate both the Supabase user and OTP session.
8. The migration revokes direct `authenticated` SELECT on the protected catalog and quality tables, so a modified browser cannot bypass OTP by calling those Data API tables directly. Anonymous public reads of published catalog rows remain governed by the existing RLS policy.

## Server environment

The Vercel server functions expect these server-side variables:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` (or the existing `SUPABASE_ANON_KEY`)
- `SUPABASE_SECRET_KEY` (preferred modern server-only secret) or `SUPABASE_SERVICE_ROLE_KEY` (legacy server-only key); never use a `NEXT_PUBLIC_` name
- `TELEGRAM_BOT_TOKEN` (server-only secret)
- Optional `TELEGRAM_GROUP_ID`, defaulting to `-1004361361948`

Do not paste credentials into GitHub, chat, or frontend code. Production-only environment variables are not automatically available to Vercel Preview deployments; configure a dedicated preview secret through Vercel's environment-variable UI before testing the preview.

## Required maintainer setup

1. Review and apply `supabase/migrations/20261028120000_add_telegram_otp_admin_gate.sql` in a non-production Supabase environment first. Do not apply it to production until the PR and direct-REST bypass tests are reviewed.
2. Confirm the administrator's numeric Telegram user ID through a trusted method. Do not infer it from a Telegram username.
3. Ensure the bot is a member with permission to post in the exact LISO LAB group. The group should be private/restricted and contain only trusted administrators.
4. After the migration is applied to the test database, insert the confirmed mapping using trusted SQL Editor tooling. Replace both placeholders; never expose this operation to anonymous/browser users:

   ```sql
   INSERT INTO public.lsl_admin_telegram_users (auth_user_id, telegram_user_id, active, note)
   VALUES (
     'REPLACE_WITH_SUPABASE_AUTH_USER_UUID'::uuid,
     REPLACE_WITH_NUMERIC_TELEGRAM_USER_ID,
     true,
     'LISO LAB admin OTP mapping'
   );
   ```

5. Confirm the Vercel server environment contains the required variables for **Preview** and Production. Keep bot and service-role secrets server-only.
6. Run the preview workflow and test OTP delivery, wrong code, expired code, reuse, five failed attempts, request throttling, Telegram group-delivery failure, non-member/revoked-member denial, disabled admin denial, expired session cookie, logout revocation, and direct Data API access as an authenticated admin.
7. Verify the existing public website can still read published catalog rows and the admin gateway can read the private rows.
8. Only after review and successful tests, merge the PR and separately approve a production migration/deployment.

## Current blockers

- The administrator's numeric Telegram user ID has not been confirmed, so no mapping can be seeded.
- The migration has not been applied to any database by this code change.
- OTP secrets and database state have not been tested by sending a real Telegram group message from this environment.
- The Vercel production environment variable list includes a Telegram bot-token entry, but secret values were not read. Presence of a variable name does not prove the value is valid or that the bot can post to the configured group.
- No production Supabase write or Vercel production deployment has been performed.

## Security notes

- OTP is posted to the restricted admin group by design. Because all group members can see it, group membership is part of the security boundary; the OTP is still bound to the authenticated Supabase user, expires in five minutes, is single-use, and is limited to five attempts.
- Challenges store an HMAC verifier rather than the plaintext code; code is never logged.
- The SQL consume function locks the challenge row and enforces one-time use and attempt limits.
- The server gateway checks the bearer token against Supabase Auth on each request and checks active admin allowlisting and the OTP session cookie.
- The browser's localStorage session is not considered proof of OTP.
- This is not considered active until the migration and mapping exist and direct REST bypass is tested.
