# LISO LAB — Telegram OTP

Status: implemented in `feat/admin-telegram-otp`; production rollout is pending the reviewed merge and Vercel deployment.

## Flow

1. The administrator signs in with Supabase Auth.
2. The server verifies the access token with Supabase Auth, checks the active `lsl_admin_users` row, and derives the Auth UUID and session UUID from the validated token.
3. If Telegram is not linked, the admin requests a short-lived deep link. The admin opens the bot's private chat and presses Start. The webhook verifies group membership before linking the Telegram numeric user ID to the Auth UUID.
4. The admin requests a six-digit code. The server checks current group membership and sends the code only to the linked Telegram private chat.
5. The administrator enters the code. The database consumes the challenge atomically and creates an eight-hour verification record bound to that exact Supabase Auth session.
6. RLS on the catalogue and quality-report tables requires both an active admin allowlist row and a current OTP verification record for the JWT session UUID. A browser-side flag or localStorage value cannot bypass this check.
7. When Telegram reports the linked account leaving or being removed from the group, the webhook revokes the verified sessions for that administrator.

## Server configuration

The Vercel Production environment inventory contains these variable names:

- `TELEGRAM_BOT_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`

Values are secret and are never read into browser code, committed, or printed in logs. The endpoint checks the Telegram bot ID against the expected LISO LAB bot ID before sending messages or configuring the webhook. The group ID is fixed server-side as `-1004361361948`.

The webhook URL is `https://linux-software-lab.vercel.app/api/telegram-webhook`. The API sets a Telegram webhook secret derived server-side from the bot token. It refuses to overwrite a webhook URL belonging to another service.

## Security controls

- Telegram bot token and Supabase secret key are server-only.
- The server verifies the Supabase access token against `/auth/v1/user`; it does not trust a client-supplied user ID.
- Telegram account linking uses a random 256-bit, 10-minute pairing token; only its HMAC verifier is stored.
- OTP codes are six digits, valid for five minutes, HMAC-hashed at rest, bound to user and Supabase session, limited to five attempts, and atomically consumed once.
- OTP requests are limited to one per minute and five per 15 minutes per user/session.
- Link requests are limited to three per 15 minutes per user.
- The Telegram bot must be an administrator in the configured group to reliably check membership and receive membership updates.
- Telegram private chat must have been started by the admin before the bot can DM the code.
- RLS protects direct Data API requests; the UI is not the authorization boundary.
- The webhook validates Telegram's `X-Telegram-Bot-Api-Secret-Token` header using a constant-time comparison.
- No password, access token, refresh token, bot token, or OTP value is logged.

## Database objects

The migration creates private tables for Telegram links, pairing challenges, OTP challenges, and verified sessions. All four tables have RLS enabled and no browser grants. Four SECURITY DEFINER RPCs are executable only by `service_role`; they enforce challenge creation, rate limits, one-time pairing, and atomic OTP consumption.

The migration also tightens the existing admin-read policies on `software_catalog`, `catalog_quality_runs`, and `catalog_quality_findings` to require a live session-bound OTP record.

## First-time administrator setup

1. Open `/admin/` and sign in with the already-provisioned Supabase Auth admin account.
2. Select **Buat tautan Telegram**.
3. Open the bot link in Telegram and press **Start** in the private chat.
4. Return to the admin page and select **Saya sudah menekan Start**.
5. Select **Kirim kode OTP**, enter the six-digit code from the bot's private chat, and verify.
6. The dashboard opens only after the database has recorded the second factor.

The intended admin must already be an active member of the LISO LAB Telegram group. The bot must also be an administrator in that group.

## Operational checks before calling this fully active

- Confirm the Vercel Production environment variables above have non-empty values; never print secret values.
- Confirm the bot identity is the expected bot and it is an administrator in group `-1004361361948`.
- Confirm Telegram webhook info points to the production endpoint and includes the configured secret.
- Test a valid admin, an ordinary Auth user, a non-member Telegram account, an expired code, a reused code, five wrong attempts, rate limits, and a removed group member.
- Test direct REST reads of all protected tables before OTP, after OTP, after expiry, and after group removal.
- Confirm the Vercel Production deployment is READY and the browser flow works end-to-end.

A syntax check of the committed JavaScript files is not an end-to-end browser test. Do not mark the live flow fully verified until the operational checks above pass.
