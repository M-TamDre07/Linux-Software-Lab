# Sorot installer and release index

`index.json` enumerates versions that actually exist in `releases/<version>/`. Keep the list in release order, oldest first and newest last. Do not add future versions until their real release directory and manifest have been created.

The terminal helper uses this file to list versions and to find the newest compatible package for the detected distro. The website uses the separate `public/data/sorot-downloads.json` data file; CI checks that both records agree with each version's `release.json`.

`planned_targets` is informational only. It must never be read as proof that a package can be downloaded. For example, Arch Linux / Sorot 0.6.0 is currently a planned target, not an available package.
