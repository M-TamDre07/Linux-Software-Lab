# Deploying Linux Software Lab on Vercel

## Correct project/repository relationship

The website is a static site deployed from `public/`. Its source repository is `M-TamDre07/Linux-Software-Lab`; the public website domain is `https://linux-software-lab.vercel.app/`.

Keep the Vercel project named `linux-software-lab` connected to that GitHub repository. The domain `linux-software-lab.vercel.app` is assigned to this project and was verified by Vercel.

PaketScope is a native Python/Qt desktop application in `apps/paketscope/`, not a web app. It should be distributed later through a verified GitHub Release and the website's download page, not hosted as a Python website on Vercel.

## Recommended settings for the website project

For Vercel project `linux-software-lab`:

1. Open **Settings → Git** and confirm the connected repository is `M-TamDre07/Linux-Software-Lab`.
2. Confirm `main` is the production branch.
3. Under **Settings → Build and Deployment**, keep Root Directory at the repository root (empty/default); do not set it to `apps/paketscope`.
4. Use the Other framework preset for this plain static website, if the dashboard asks.
5. Leave the custom build command empty; the website has no framework build step.
6. Keep Output Directory as `public`, as set in `vercel.json`.
7. After merging a website change into `main`, inspect the new production deployment and confirm the domain is serving that commit.

Important distinction: Root Directory is the repository root; Output Directory is `public/`. They are not the same setting.

## If a separate Vercel project named `paketscope` is building this repository

PaketScope itself is a native desktop application, so that separate web deployment is not required. If the project named `paketscope` is connected to the same repository and causes a failed Vercel check, disconnect only that Vercel project's Git connection:

1. Open Vercel project `paketscope`.
2. Open **Settings → Git**.
3. Under **Connected Git Repository**, choose **Disconnect** and confirm.
4. Leave the GitHub repository and `apps/paketscope/` source code untouched.

Do **not** disconnect the website project `linux-software-lab`, and do not import the native PaketScope source as a second website. A desktop release will be published as a package artifact after the package is ready and tested.

## If the Import list disappears or import fails

An Import dialog is a project-creation flow, not a list of source folders. Do not delete the existing website project or create a duplicate just because the list goes away.

- Return to the Vercel dashboard and check the existing Projects list first.
- If the website project exists, inspect its latest deployment and build logs instead of importing again.
- If the Git repository is missing from Import, confirm the correct Vercel account/team is selected.
- Check that Vercel's GitHub App has permission to access the personal repository. If the repo is not listed, use the GitHub App configuration link in Vercel to review repository access.
- If an error refers to a build limit/rate limit, avoid repeatedly pressing Import or creating duplicate projects; inspect the deployment error and retry after the limit clears.

Official references:
- Git integration: https://vercel.com/docs/git
- GitHub project integration: https://vercel.com/docs/git/vercel-for-github
- Git settings and disconnecting a repository: https://vercel.com/docs/project-configuration/git-settings
- Build and Output Directory settings: https://vercel.com/docs/builds/configure-a-build
- Repository missing from Import: https://vercel.com/kb/guide/unable-to-find-github-repository

## Static output and privacy

`vercel.json` publishes only `public/`. It does not publish application source under `apps/`, test fixtures, repository scripts, or maintainer documents as site files. The site requests its static catalogue JSON from the same origin; it has no backend search API and does not transmit search terms to a third party.


## Supabase catalogue mirror

The Vercel project remains a static deployment from the repository root with output directory public/. Its Content Security Policy permits connections only to the configured Supabase project in addition to same-origin requests. The browser uses the publishable key and reads only rows allowed by Row Level Security; it never receives the CI secret key. Supabase serves a read-only mirror of public/data/software.json, while GitHub remains the source of truth. If the mirror is unavailable, the website falls back to the committed JSON catalogue. See docs/SUPABASE_INTEGRATION.md for secret setup, synchronization, and access policy details.
