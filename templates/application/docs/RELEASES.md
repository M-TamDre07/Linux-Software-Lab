# Releases — {{APP_NAME}}

No release has been published by this scaffold.

For every real version:
1. Build from a reviewed commit in a clean, reproducible environment.
2. Record toolchain/dependency versions, supported OS and architecture, and the exact build commit.
3. Test install, launch, upgrade, uninstall, and rollback where applicable.
4. Store immutable artifacts under `releases/<version>/`; never replace files for a published version.
5. Generate `release.json` and `SHA256SUMS` from the real artifact bytes and validate against the repository manifest schema.
6. State whether publisher signing is implemented. SHA-256 alone does not authenticate the publisher.
7. Update the shared distribution index and website catalogue only after the artifact exists and has passed tests.
8. Keep unavailable package formats marked unavailable; never create fake download links, hashes, or successful-release claims.
