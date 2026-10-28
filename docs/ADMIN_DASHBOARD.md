# Linux Software Lab — Admin dashboard

The static dashboard is available at `/admin/`. It is intentionally `noindex` and does not grant access just because the URL is known. Its client uses the public Supabase publishable key only, authenticates with Supabase Auth, then checks the authenticated UUID against `public.lsl_admin_users` before querying `public.software_catalog`.

## Current scope

- Sign in with an existing Supabase Auth user.
- Require an active row in `public.lsl_admin_users`; an authenticated account by itself is not an admin.
- Read the catalogue mirror, publication status, version, metadata update date, and sync timestamp.
- Search/filter the records and inspect a small health summary.
- Store the short-lived access/refresh tokens in tab-scoped `sessionStorage`, request local-session revocation on logout, clear browser-held tokens even if the network call fails, and omit cookies from API requests.
- Make no catalogue mutations and do not query other users, secrets, Auth administration endpoints, or private server settings.

This is a read-only operational dashboard, not a full management interface. `public/data/software.json` remains the catalogue source of truth. The maintainer currently works directly on `main` by explicit project decision, so each change must pass the repository's automated quality checks after the push and any failure must be corrected before further rollout. The GitHub Actions sync updates Supabase from the canonical source. Do not write directly to the read-only mirror from the browser.

## Bootstrap the first administrator

Perform these steps from the trusted Supabase Dashboard, not through the public site:

1. Open the Linux-Software-Lab Supabase project and go to **Authentication → Users**.
2. Create the maintainer's user with an email you control. Use a strong unique password, and confirm the account is ready for password sign-in according to the project's Auth settings.
3. Copy that user's UUID from the user table.
4. In the SQL Editor, run the following only after replacing the placeholder with the UUID of the intended maintainer:

   ```sql
   insert into public.lsl_admin_users (user_id, active, note)
   values ('REPLACE_WITH_AUTH_USER_UUID'::uuid, true, 'Primary maintainer')
   on conflict (user_id) do update
   set active = true,
       note = excluded.note;
   ```

5. Open `/admin/` and sign in with that Auth user.
6. To revoke dashboard access, set that row's `active` to `false` or remove the row from the trusted SQL Editor. The dashboard checks the active row on each page load and data refresh.

Never create an anonymous policy that allows users to insert or update `lsl_admin_users`. Do not use editable `user_metadata` as an authorization source. The authorization check must stay anchored to the server-managed row and RLS.

## Security model and limitations

- The browser key is publishable and is not a secret; **RLS and SQL grants enforce access**.
- Never place an `sb_secret_` key or service-role key in HTML, JavaScript, Vercel public environment variables, local storage, or a public commit.
- The dashboard's `noindex` metadata reduces indexing but is not an access control. Auth and RLS are required.
- Admins can read only the tables and rows allowed by the current Supabase policies. This page does not expose the Supabase project, database credentials, all Auth users, logs, or every table.
- The current dashboard does not create catalog edits or GitHub commits. A future editor must use a trusted server-side GitHub App or another narrowly scoped authenticated service to create a reviewed change; do not expose a GitHub personal access token in the browser.
- The static dashboard assumes the existing site's Content Security Policy allows connections to the configured Supabase project. Keep this origin exact; avoid broad wildcard `connect-src` rules.

## Verification

From the repository root:

```bash
python scripts/check_site_links.py
python -m unittest discover -s tests -v
node --check public/assets/js/admin.js
```

After changes to tables or policies, inspect Supabase Security Advisor and re-check RLS policies/grants. Login should be tested first with an authorized account and then with an ordinary Auth account, which must be denied admin access.
