# Security — {{APP_NAME}}

## Trust boundaries

List network inputs, local files, process boundaries, credentials, privileged operations, and data leaving the device.

## Required controls

- Validate inputs at each boundary; use parameterised database queries rather than concatenating SQL.
- Use fixed executable allowlists and argument arrays; do not pass remote metadata to a shell.
- Keep secrets out of source, public assets, logs, screenshots, and release archives.
- Use least privilege and require explicit confirmation for privileged operations.
- Keep RLS enabled on exposed Supabase tables and design grants/policies for the exact roles and operations needed.
- Pin dependencies, commit lockfiles, and run the applicable dependency/source scanners.
- Keep release artifacts immutable; publish checksums and publisher signatures only when the actual verification/key-rotation workflow is implemented.

## Security tests and reporting

Add safe regression cases under `tests/security/`. Follow the repository's `.github/SECURITY.md` reporting policy and never test destructive payloads against production.
