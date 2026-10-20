# Deploying Linux Software Lab on Vercel

## Important distinction

This repository contains two kinds of files:

- The website is a static HTML/CSS/JavaScript site at the **repository root**.
- PaketScope is a Python/Qt desktop application under `apps/paketscope/`. It is not a browser website and must not be imported as a separate Vercel web project.

The existing Vercel website should remain connected to `M-TamDre07/Portofolio` with the repository root as the website root directory. This catalog update does not require importing a second project.

## Recommended settings

For an existing website project:

1. Open the project already serving the public Linux Software Lab domain.
2. Open **Settings → Build and Deployment**.
3. Confirm the Git repository is `M-TamDre07/Portofolio` and the production branch is `main`.
4. Keep the Root Directory at the repository root (`.` / blank root setting). Do not set it to `apps/paketscope`.
5. This site has no build step. Use the static/Other preset and no custom build command unless Vercel's existing project settings already deploy correctly.
6. Pushes merged into `main` should trigger production deployments when Git integration is connected. Check the deployment entry and build logs if a deployment fails.

Do not delete the existing project just because an import dialog fails or disappears. Leaving the dialog or returning to the dashboard does not imply the GitHub repository was deleted.

## If GitHub does not appear in Import

Vercel's GitHub App needs permission to access the repository. Check that Vercel is authorized for this personal repository and that the correct Vercel account/team is selected. Review Vercel's Git integration settings before granting any additional access.

Official guidance:
- https://vercel.com/docs/git
- https://vercel.com/docs/builds/configure-a-build
- https://vercel.com/kb/guide/unable-to-find-github-repository

## If the import list disappears

The import list is part of the project-creation flow, not a permanent list of local source folders. Return to the dashboard and check the existing Projects list. Do not create duplicate projects for a desktop app. If this project's existing deployment is still serving the site, use that project and inspect its deployment/build logs instead of importing it again.

If the project was never created and the repository is not offered, inspect GitHub App repository permissions and the currently selected Vercel team/account.
