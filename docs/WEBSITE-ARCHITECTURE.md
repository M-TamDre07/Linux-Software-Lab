# Website architecture and Vercel deployment

## Separation of concerns

This repository is a small monorepo. It holds the public catalogue website and source code for desktop applications, but only the website should be published by Vercel.

~~~text
/
├── public/                       # Only this folder is published by Vercel
│   ├── index.html                # Catalogue homepage
│   ├── assets/
│   │   ├── css/site.css          # Design system and responsive styles
│   │   ├── js/site.js            # Search, filters, URL state and pagination
│   │   └── images/               # Original icons and preview concepts
│   ├── data/
│   │   ├── software.json         # Canonical catalogue records
│   │   └── catalog.schema.json   # Versioned catalogue data contract
│   └── software/                 # Detail pages for each application
├── apps/
│   └── paketscope/               # Desktop app source; never served by Vercel
├── scripts/
│   └── validate_catalog.py       # Validates data, pages and local assets
├── docs/
│   └── WEBSITE-ARCHITECTURE.md
├── .github/workflows/
│   └── catalog-checks.yml
├── vercel.json                   # Publishes public/ with security headers
└── README.md
~~~

## Add a software entry

1. Add one object to public/data/software.json.
2. Give it a unique lowercase id, readable name, one-sentence summary, category, status, platforms, tags, keywords, features, detail path, and icon/preview paths.
3. Create its public/software/<id>.html detail page.
4. Add original SVG or optimized web imagery under public/assets/images/.
5. Run python scripts/validate_catalog.py and node --check public/assets/js/site.js.
6. Open a pull request; GitHub Actions validates catalogue records, local links/assets, JavaScript syntax, and Vercel configuration.

The homepage loads the metadata once, then filters locally. Query, status, category, platform, sort, and page state can be shared through the URL. Only 12 cards are rendered at a time. A web-search link appears only when the local catalogue has no matching results and the visitor explicitly clicks it; no external search request runs while typing.

## Vercel: important distinction

PaketScope is a desktop Qt/Python application, not a standalone website. Vercel cannot run its desktop window as a public web app. The catalogue website is what should be deployed; PaketScope source remains under apps/paketscope/.

In Vercel's Import Project screen, select the Git repository M-TamDre07/Portofolio. Do not search for apps/paketscope/ as if it were a separate repository: that path is a subdirectory inside Portofolio.

For this repository, keep Root Directory empty (repository root). The repository-level vercel.json sets outputDirectory to public, which prevents desktop source files, tests, docs, and other repository files from being served publicly.

If creating a Vercel project manually:

1. Select the correct Vercel team/account.
2. Import the Git repository M-TamDre07/Portofolio.
3. Keep Root Directory at the repository root.
4. Select the Other framework preset for a plain static site if the dashboard asks.
5. Leave the Build Command empty when an override is enabled; there is no frontend build step.
6. Deploy. The output directory comes from vercel.json (public).
7. Confirm the deployment and domain under the project's Deployments and Domains sections.

If the repository is missing from Vercel's import list, check that Vercel is connected to the GitHub account that owns the repository and that the GitHub App has permission to access it. Personal-account repositories generally require repository ownership to import or connect. If an import attempt disappears or fails, return to Add New → Project and import the repository again. Importing a repository is different from selecting a folder inside it.

Official reference: https://vercel.com/docs/git/vercel-for-github
Official build settings: https://vercel.com/docs/builds/configure-a-build

## Security and privacy boundaries

- Catalogue search runs in the browser against static JSON data.
- The explicit web-search option opens a search engine only after a visitor clicks it.
- The catalogue site does not send app inventory to a backend and has no analytics endpoint.
- Response headers discourage MIME sniffing, referrer leakage, framing, and unnecessary device permissions.
- Never put secrets, tokens, or private environment data under public/.
