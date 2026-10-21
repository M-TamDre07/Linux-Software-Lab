# Deploying Linux Software Lab on Vercel

## Do not import the desktop app as a website

The repository contains a static website and application source code. The website is deployed from public/; PaketScope's Python/Qt source is in apps/paketscope/ and opens as a desktop application. It is not a separate Vercel website.

The existing Vercel project should remain connected to GitHub repository M-TamDre07/Linux-Software-Lab. This update does not require a second project.

## Recommended Vercel settings

For the existing project:

1. Open the project currently serving Linux Software Lab.
2. In Settings → Git, confirm it is connected to M-TamDre07/Linux-Software-Lab and uses main for production.
3. In Settings → Build and Deployment, keep Root Directory at the repository root (empty/default). Do not set it to apps/paketscope.
4. Use the Other framework preset for this plain static website if the dashboard asks.
5. Leave the custom build command empty. The website has no framework build step.
6. vercel.json sets outputDirectory to public; it is the static directory that should be served. Do not override it to the repository root.
7. Keep the existing project/domain, merge code changes to main, then review the resulting deployment and build logs.

Important distinction: Root Directory = repository root; Output Directory = public/. They are not the same setting.

## If the Import list disappears or import fails

An Import dialog is a project-creation flow, not a list of source folders. Do not delete the existing project or create a duplicate just because the list goes away.

- Return to the Vercel dashboard and check the existing Projects list first.
- If the project exists, inspect its latest deployment and build logs rather than importing again.
- If the project never existed or the Git repository is missing from Import, confirm the correct Vercel account/team is selected.
- Check that Vercel's GitHub App has permission to access the personal repository. If the repo is not listed, use the GitHub App configuration link in Vercel to review repository access.
- If the error refers to a build limit/rate limit, avoid repeatedly pressing Import or creating duplicate projects; check deployment error details and retry only after the limit clears.

Official references:
- Git integration: https://vercel.com/docs/git
- GitHub project integration: https://vercel.com/docs/git/vercel-for-github
- Build and Output Directory settings: https://vercel.com/docs/builds/configure-a-build
- Repository missing from Import: https://vercel.com/kb/guide/unable-to-find-github-repository

## Static output and privacy

vercel.json publishes only public/. It does not publish the app source under apps/, test fixtures, repository scripts, or maintainer documents as site files. The site makes a same-origin request for its static catalogue JSON; it has no backend search API and does not transmit search terms to a third party.
