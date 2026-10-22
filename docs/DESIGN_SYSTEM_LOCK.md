# Permanent UI/UX and Art Direction Lock

**Status:** mandatory maintainer rule  
**Applies to:** all public website pages, catalogue pages, product pages, product previews, and desktop application interfaces in this repository.  
**Visual reference:** https://getartcraft.com/  
**Implementation:** this project uses an original, ArtCraft-inspired editorial system. It must not copy ArtCraft's source code, proprietary assets, logos, or exact branded content.

## Non-negotiable rule

The visual identity is locked. Routine feature work, bug fixes, security patches, dependency updates, refactors, database/API changes, packaging changes, and release automation must not independently redesign the interface. Preserve the established composition, typography, palette, borders, spacing, controls, motion language, and interaction patterns.

A visual redesign or change to this design contract requires explicit maintainer approval. If a technical change appears to require a visual change, explain the reason and propose the smallest compatible adjustment first; do not silently replace the design.

## Visual language

- Editorial, technical, restrained, grid-based layout with clear section boundaries.
- Warm off-white/light surfaces and near-black ink in light mode; near-black surfaces and warm light text in dark mode.
- Thin, low-contrast rules and square corners. Avoid rounded-pill controls, oversized radii, gratuitous gradients, glow effects, and generic floating-card layouts.
- Compact uppercase monospace labels for navigation, metadata, status, and technical annotations.
- Large, tightly tracked sans-serif headings; readable body copy and clear hierarchy.
- High-contrast, direct primary actions; quiet outlined secondary actions.
- Motion is purposeful and subtle: short transitions, restrained reveal/hover effects, no decorative motion that competes with content.
- Respect `prefers-reduced-motion`, keyboard navigation, visible focus, semantic HTML, responsive layouts, and adequate contrast.
- Keep Linux Software Lab and PaketScope's own names, logos, copy, product information, and functionality. The reference informs art direction, not brand identity.

## Source-of-truth files

- Website design tokens and visual overrides: `public/assets/css/experience.css`
- Base website styling: `public/assets/css/site.css` (maintain compatibility; do not reintroduce conflicting visual patterns)
- Website interactions and motion: `public/assets/js/site.js`
- PaketScope desktop theme: `apps/paketscope/paketscope/ui/theme.py`
- Website and repository architecture: `docs/ARCHITECTURE.md`

Before introducing a new component, reuse the established tokens and patterns. Avoid per-page styling exceptions unless required for accessibility or product-specific functionality.

## Change and review protocol

Every pull request or maintenance task that touches the interface must:

1. Preserve the design language above and keep existing routes and core workflows working.
2. Check desktop and mobile layouts, light and dark themes where supported, keyboard focus, and reduced-motion behavior.
3. Run the repository's site-quality checks and relevant application tests.
4. Include a concise note confirming that the visual lock was preserved, or identify an explicitly approved exception.
5. Never replace product screenshots with concept art without clearly labelling it; never claim an unreleased feature is available.

When a future maintainer or AI coding assistant is asked to update this repository, this document is a mandatory constraint—not an optional suggestion. Improve the product's function without inventing a new visual identity.
