# LISO LAB Telegram configuration

This document records the intended Telegram identifiers for the **Linux Software Lab (LISO LAB)** admin-authentication/OTP integration. It does not mean Telegram OTP is implemented or active yet.

- **Telegram group ID:** `-1004361361948`
- **Telegram bot ID:** `8258093251`
- **Bot API token:** not stored in this repository. The maintainer must add it as a server-side Supabase Edge Function secret named `TELEGRAM_BOT_TOKEN` when the Edge Function is implemented.

## Security and integration requirements

1. Keep this configuration isolated from the separate Tama Andrea Studio project. Tama Andrea Studio uses a different Telegram group and bot; do not copy those IDs into LISO LAB.
2. Do not put the bot token in frontend JavaScript, HTML, public database rows, GitHub commits, or chat messages.
3. Before enabling OTP, implement a server-side Edge Function that verifies membership in the configured group, maps each authorized administrator's numeric Telegram user ID to their Supabase Auth UUID, issues short-lived single-use OTP challenges, and enforces rate limits and attempt caps.
4. The bot must have sufficient group permissions to verify membership reliably. Each administrator must start a private conversation with the bot before it can send them a private OTP.
5. Test valid members, non-members, revoked access, expired/replayed codes, and rate limiting before declaring OTP active.

**Status:** identifiers recorded; server-side OTP implementation and end-to-end tests remain pending.
