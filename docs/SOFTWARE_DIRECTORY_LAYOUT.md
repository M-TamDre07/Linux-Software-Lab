# Software directory and release layout

Linux Software Lab separates the **website** from each **software product**.

## Repository map

```text
repository/
├── public/                         # Only website output deployed to Vercel
│   ├── index.html
│   ├── assets/
│   ├── data/software.json          # Catalogue source of truth
│   └── software/
│       ├── index.html
│       ├── paketscope.html         # Public product information
│       └── sorot.html
├── apps/                           # Source projects, isolated per application
│   ├── README.md
│   ├── paketscope/                 # Native desktop software, active v3 branch
│   │   ├── README.md
│   │   ├── LICENSE
│   │   ├── pyproject.toml
│   │   ├── paketscope/
│   │   ├── tests/
│   │   └── docs/
│   └── sorot/                          # Sorot release artifacts and docs, stored per version
│       └── README.md
├── scripts/                        # Website/catalog validators
├── tests/                          # Website regression tests
├── docs/                           # Repository-level project/deployment guides
└── vercel.json                     # Serves public/ only
```

PaketScope 3 source is present in the default branch and the website catalogue currently labels version 3.0.0.dev4 as testing. It remains a development prev���q�^