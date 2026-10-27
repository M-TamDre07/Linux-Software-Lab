# Security regression tests

Keep fixed regression cases for untrusted input, path traversal, command construction, SQL/NoSQL injection boundaries where applicable, unsafe redirects, secret leakage, privilege transitions, and permissions.

Use non-destructive test fixtures. Do not include actual credentials, customer data, destructive payloads against production, or tests that rely on weakening a protection to pass.
