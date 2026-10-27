# User-facing error and diagnostic standard

This standard applies to the website catalogue, Linux Software Lab Center GUI/CLI, product applications, repository scripts, and future integrations.

## What a useful error must say

Every expected failure should answer three questions in plain Indonesian:

1. **Apa yang gagal?** State the failed operation without jargon where possible.
2. **Apakah sistem berubah?** Make clear whether installation, a write, deletion, or other state change happened. Never imply success if the result is uncertain.
3. **Apa langkah aman berikutnya?** Offer one safe action such as checking a connection, refreshing metadata, reviewing permissions, or reading a diagnostic report.

When useful, include a stable error code and short technical details that do not contain secrets. Example:

> **Katalog belum dapat dimuat (LSL-CAT-001).** Sumber online dan data cadangan tidak bisa dibaca. Tidak ada data yang diubah. Periksa koneksi, lalu muat ulang halaman.

## Separation of user messages, logs, and diagnostics

- User-facing messages must not include raw stack traces, SQL statements, request headers, tokens, signed URLs, database connection strings, secrets, or arbitrary upstream response bodies.
- Logs may include the operation, stable error code, HTTP status, elapsed time, and a correlation ID. Redact authentication headers and secret query/body values before logging.
- Developer diagnostics should be opt-in or offered separately from the simple user message. Include the command to gather diagnostics when it is safe.
- Do not silently swallow an error that changes the meaning of displayed data. For fallback success, tell the user that the mirror is unavailable and the committed local catalogue may be stale.
- Do not claim an installer failed cleanly if the package manager may have partially changed the machine; state the uncertainty and provide a recovery/inspection step.

## Website catalogue

- Prefer the Supabase mirror when its response passes validation.
- If the mirror fails, use the committed same-origin `/data/software.json` fallback and display a visible status message.
- If both sources fail or return invalid schema, display a concise error in an accessible live region and keep the page operable. Do not expose the raw backend error.
- Search/filter terms remain in the browser. Do not send query text to Supabase or append it to a REST filter.
- Render metadata using HTML escaping or DOM `textContent`; treat catalog data as untrusted presentation input even when it is committed in Git.

## Launcher GUI and CLI

- GUI dialogs must say what action stopped (catalogue refresh, download verification, install simulation, or package installation).
- Distinguish “not available for this OS”, “unsupported package format”, “missing dependency”, “network failure”, “integrity mismatch”, “user cancelled”, and “package manager reported an error”.
- Use the same error semantics in GUI and CLI by routing through shared core functions; do not duplicate security decisions across presentation layers.
- Preserve non-zero CLI exit codes on operational failure. For automation, expose stable machine-readable JSON from a dedicated command instead of requiring applications to parse human text.
- Before privileged operations, state what package action will be requested and where users can cancel. Never ask users to run the entire launcher as root.

## Suggested error-code namespace

| Prefix | Area |
| --- | --- |
| `LSL-WEB` | Static website, search, or metadata display |
| `LSL-CAT` | Catalogue/index validation and refresh |
| `LSL-OS` | OS/distro/architecture detection |
| `LSL-DL` | Download, redirect policy, or integrity checks |
| `LSL-INSTALL` | Package simulation, privilege request, or installation |
| `LSL-AUTH` | Authentication and authorization |
| `LSL-SYNC` | GitHub Actions-to-Supabase synchronization |
| `LSL-SCAFFOLD` | Repository scaffold generation and validation |

Codes should be stable once documented. A code identifies the category; it should not encode email addresses, IDs, tokens, or other user data.

## Verification

When modifying error paths, test the success path, each fallback, malformed upstream data, denied access, timeouts, cancellation, and the case where neither primary nor fallback service is available. Assert that the user-facing message remains generic and useful while logs never include secret values.
