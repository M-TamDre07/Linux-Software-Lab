# Supabase Edge Functions — local development

The `feedback-create` function is implemented as an **un-deployed development artifact**. It is not wired into the public website yet and cannot accept production feedback until the schema, secrets, tests, and client integration are completed.

## Function: `feedback-create`

Responsibilities:
- Accepts JSON only from the production website origin, validates field lengths, and rejects oversized payloads.
- Verifies Cloudflare Turnstile server-side.
- Uses AES-256-GCM to encrypt subject, message, and optional contact before database storage.
- Uses a separate HMAC key to create a lookup hash for optional contact matching.
- Stores a ticket in Supabase and forwards a minimal copy (without contact details) to Formspree.
- Reports whether the database write succeeded and whether Formspree accepted the notification.
- Logs hashed IP identifiers and minimal security metadata, not raw contact values or message bodies.

### Required local-only environment variables

Create an ignored local env file for local testing; never commit it or paste its contents into chat.

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TURNSTILE_SECRET_KEY`
- `FEEDBACK_ENCRYPTION_KEY`: base64 encoding of exactly 32 random bytes.
- `FEEDBACK_LOOKUP_HMAC_KEY`: base64 encoding of at least 32 random bytes.

Generate distinct random keys locally on Linux, for example:

```bash
openssl rand -base64 32
openssl rand -base64 32
```

Run locally only after a local Supabase stack has the reviewed migration applied:

```bash
supabase functions serve feedback-create --env-file supabase/.env.local
```

The env file must be excluded from Git. Never use the production service-role key for local experiments. Do not run `supabase db push`, apply the migration to production, or deploy this function as part of local validation.

## Important limitations before public release

- Rate limiting currently uses a read-then-log event pattern. It is not atomic under concurrency; replace it with a database RPC/token-bucket or another trusted atomic limiter before exposing the endpoint publicly.
- CORS origin checks are defense-in-depth, not authentication; direct non-browser callers still require CAPTCHA and rate limiting.
- The current implementation forwards the message and subject to Formspree, but intentionally omits contact details. Confirm Formspree's retention and account access settings before production use.
- A ticket can be saved even if Formspree fails. The response marks this partial failure; a durable retry queue and admin retry control are still needed.
- Encryption key rotation and a tested decryption/admin reply path are not implemented yet. Do not deploy until key backup/rotation and authorized decryption are designed and tested.
- The feedback form in the public website and the admin ticket/reply interface are not yet connected to this endpoint.
- Admin CAPTCHA, server-enforced Telegram OTP, and a gateway replacing direct dashboard reads are separate unfinished work. This function does not complete those controls.
