# LISO LAB — Telegram OTP readiness design

Status: planning only. Telegram OTP is not implemented, and no Supabase Edge Functions are currently deployed.

## Security requirements

- Authenticate the user through Supabase Auth and derive the user UUID from a validated token, never from request JSON.
- Maintain a trusted server-side mapping from Auth UUID to Telegram numeric user ID. The mapping must be confirmed by the maintainer; do not guess it.
- Use the LISO LAB group ID `-1004361361948` and bot ID `8258093251`. Keep the bot token in Supabase Edge Function secrets only; never commit or expose it in browser code.
- Check group membership server-side. The bot needs suitable group permissions for reliable membership checks, and each admin must start a private chat with the bot.
- Store only a secure verifier for each short-lived code, not the raw code. Bind each challenge to the authenticated user, limit attempts, expire quickly, and consume it atomically so it cannot be replayed.
- Rate-limit challenge creation and verification. Return generic errors that do not reveal whether an account or Telegram ID is registered.
- Never log passwords, access/refresh tokens, bot tokens, or one-time codes.

## Critical enforcement rule

A browser-side flag or localStorage value is not authorization. An authenticated user may call Supabase Data API endpoints directly. Before OTP is considered an effective second factor, protected admin data access must be enforced by a trusted server-side gateway or another server-validated authorization mechanism, and direct REST requests must be tested for bypass.

## Implementation sequence

1. Confirm each intended admin's Telegram numeric user ID and record the mapping in a server-managed location.
2. Configure the bot token as an Edge Function secret; do not send the token in chat.
3. Implement and test the trusted challenge creation and verification flow, including membership checks, expiry, rate limits, and one-time use.
4. Enforce second-factor state for every protected admin data request; do not rely on UI-only gating.
5. Test ordinary accounts, group non-members, revoked membership, delivery failures, expired/reused codes, throttling, and direct Data API access.
6. Review RLS, grants, and Security Advisor. Do not deploy to Vercel until the maintainer explicitly approves.

## Current blockers

- The intended admin Telegram numeric user ID mapping has not been confirmed.
- No Edge Functions are deployed in the project at the latest inventory check.
- Supabase Security Advisor reports leaked-password protection disabled; enable it in Auth settings and verify the warning clears.
- End-to-end admin login and server-enforced second-factor access have not been tested.
