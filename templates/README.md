# Repository templates

Templates provide a consistent starting point while keeping runtime and distribution choices explicit. They are not published website content and do not imply that source code or installers exist.

## Application scaffold

Use the standard template through the repository helper:

```bash
python scripts/scaffold_app.py --slug sample-tool --name "Sample Tool" --description "A short, accurate purpose statement."
```

The helper creates `apps/sample-tool/` only if that path does not already exist. It rejects malformed IDs and never overwrites an existing app. It creates documentation and directory placeholders; it does **not** edit the public catalogue, invent a license, create application code, register a launcher command, or publish a release.

Review each generated placeholder and choose a real runtime, licence, supported OS matrix, dependencies, entry points, tests, and release process before implementation.
