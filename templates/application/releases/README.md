# Immutable releases

There are no release artifacts in a fresh scaffold. When a real version is ready, create `<version>/release.json` and `SHA256SUMS` alongside the actual build outputs. Validate the manifest using `docs/schemas/distribution-manifest.schema.json`.

Never commit example/fake digests as if they described an artifact. Use a new directory for every released version and never mutate an already-published version.
