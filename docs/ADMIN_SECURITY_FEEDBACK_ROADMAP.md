# Admin security, feedback, and live support plan

Status: **foundation only — not active in production**. The migration paired with this document is a draft schema. It has not been applied to Supabase, no Edge Functions have been deployed, and the website/admin UI has not yet been wired to these tables.

## Intended user experience

- Public visitors can send feedback about the website, launcher, or an application.
- A trusted server-side endpoint stores the ticket in Supabase and forwards a notification copy to Formspree at `https://formspree.io/f/xjyyokow`. The browser must not write directly to the database. Delivery status must be tracked independently: database success plus Formspree failure is a partial success and should be retried safely.
- Admins can review, categorize, assign status, reply in a ticket thread, and see whether an admin is actively accepting chats.
- Public content settings are draft/publish records. Any setting that affects the static site needs a deliberate read path and preview/rollback behavior; changing a database row alone will not alter HTML that is hard-coded in the static site.
- CAPTCHA, email/password authentication, and Telegram OTP are distinct controls. OTP must be enforced server-side on every protected admin operation, not just by hiding the dashboard.
- Repeated suspicious requests should trigger rate limiting and a temporary block, with an audit event. Use progressive backoff and a bounded lockout to avoid giving attackers an easy permanent denial-of-service against the real admin. Do not automatically block a whole shared IP indefinitely.

## Security architecture

1. **Public feedback endpoint**: verify a server-validated CAPTCHA token, validate and bound all fields, apply rate limits, create an opaque ticket code, encrypt message/contact fields with authenticated encryption, insert the ticket, then forward the notification copy to Formspree from the server. Never expose encryption keys or privileged Supabase keys in browser assets.
2. **Admin sign-in**: use Supabase Auth and active membership from `lsl_admin_users`. Add a server-validated CAPTCHA to the sign-in flow. Do not log passwords or auth tokens.
3. **Telegram OTP**: issue a short-lived one-time code, store only a cryptographic verifier, limit attempts, bind it to the authenticated admin, and consume it atomically. Send via a server-side Telegram bot secret. Confirm the intended admin's Telegram numeric user ID separately from the bot ID. Do not assume that a bot ID is the admin user's ID.
4. **Authorization gateway**: protected ticket/content/security APIs must check current Auth identity, active admin membership, and recent verified second-factor state on every request. The current dashboard has direct Supabase Data API calls; therefore OTP is **not effective yet** until protected direct reads are removed/restricted or moved behind a trusted server-side gateway and bypass tests pass.
5. **Encryption**: use authenticated field-level encryption (e.g. AES-256-GCM) in Edge Functions with a randomly generated key stored only as an Edge Function secret. Store ciphertext, nonce/IV, and authentication tag together or in explicit columns; version the envelope for future key rotation. Hash lookup identifiers with a separate keyed HMAC secret. Never store raw OTPs, contact details, or message bodies in logs. Encryption does not protect data after a compromised application has access to decryption keys, and it does not replace access control or backups.
6. **Audit and blocks**: record only sanitized event types, timestamps, keyed hashes, and minimal non-sensitive metadata. Avoid storing raw IPs unless a documented need and retention period are approved. Use server-side rate limits, temporary blocks, and an admin-visible security event list.
7. **Website content management**: keep the current GitHub/static files as source of truth until a safe publishing workflow is implemented. A database draft must not silently overwrite the live website. Publishing should validate a strict allowlist of editable fields, support preview/rollback, and record who published what.
8. **Live chat/presence**: presence is advisory and expires automatically. If no admin is online/accepting chats, offer a ticket form instead. Do not expose admin private details to visitors.

## Migration and rollout gates

The SQL migration is intentionally not applied. Before it can be used:

- Inspect the live schema/migration history and reconcile naming/constraints.
- Implement Edge Functions for feedback create/reply/list/status, CAPTCHA verification, OTP request/verify, content draft/publish, presence heartbeat, and security event review.
- Configure free CAPTCHA provider keys and Supabase Edge Function secrets directly in the provider dashboards. Do not send secrets in chat or commit them.
- Confirm the actual admin Telegram numeric user ID and private-chat delivery. A Telegram bot ID is not the same as a Telegram user ID.
- Decide whether Formspree receives the full feedback content or only a ticket notification; default recommendation is to send only the minimum needed and avoid transmitting sensitive contact/message content unnecessarily.
- Add automated tests for RLS/grants, unauthorized direct Data API calls, CAPTCHA replay/invalid tokens, OTP expiry/replay/attempt caps, encryption round trips/key rotation, duplicate submissions, Formspree failure/retry, rate-limit reset, and ticket ownership.
- Run Supabase security advisors and verify with live requests in a non-production environment before any production migration.
- Keep the current website design unchanged; add functionality without redesigning the established UI.

## Current limitations and dependencies

- This repository currently has a static website and a read-only admin dashboard; the dashboard does not yet implement feedback management, content publishing, CAPTCHA, Telegram OTP, or live chat.
- The current admin dashboard directly reads catalog tables from Supabase. That path must be hardened before claiming that OTP protects all admin data.
- The configured Formspree endpoint is a destination only; its field mapping, spam behavior, retention, and response workflow have not been tested.
- No production database migration, Vercel deployment, Telegram message, or Formspree submission has been performed as part of this foundation change.
