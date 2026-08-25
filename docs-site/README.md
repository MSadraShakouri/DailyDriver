# DailyDriver Docs Site

Astro Starlight site that builds from the simple markdown in `../docs/`.

* **Source of truth**: `../docs/` — plain markdown, GitHub-readable, no frontmatter.
* **This folder**: Astro config, `public/`, `src/content.config.ts`, and a custom sync workflow that creates temp files in `src/content/docs/` at build/dev time.

Published at `https://msadrashakouri.ir/DailyDriver/` via `.github/workflows/docs.yml`.

## How it works

1. `scripts/sync-docs.mjs` copies `../docs/**/*.md` into `src/content/docs/` (temp, gitignored).
2. During copy it:
   - injects frontmatter `title` from `scripts/titles.json` (fallback: first `# Heading` or filename)
   - rewrites GitHub-style links `*.md` -> Starlight clean URLs `*/` (e.g. `commands/logging.md` -> `commands/logging/`)
   - rewrites out-of-docs links like `../CONTRIBUTING.md` -> absolute GitHub blob URLs
3. `astro build` / `astro dev` then runs on the generated files.

Only `src/content/docs/index.md` is committed here — it's the site homepage (overview page). All other pages in `src/content/docs/` are generated and ignored.

## Local dev

```bash
cd docs-site
npm ci
npm run dev      # sync + astro dev (binds 0.0.0.0)
# or
npm run build    # sync + build to dist/
npm run preview
```

The sync is automatic via `dev` and `build` scripts. If you want to clean generated files:

```bash
npm run clean
# or
rm -rf src/content/docs/architecture.md src/content/docs/getting-started.md src/content/docs/roadmap.md src/content/docs/commands src/content/docs/concepts src/content/docs/reference
```

## Files

- `astro.config.mjs` — site, base, Starlight sidebar, editLink points to `../docs/` so "Edit on GitHub" goes to the real source.
- `src/content.config.ts` — Starlight content collection.
- `src/content/docs/index.md` — homepage, not generated.
- `scripts/titles.json` — title injection map.
- `scripts/sync-docs.mjs` — copy + transform.
- `scripts/clean.mjs` — remove generated files.

## Why temp files?

We keep a single set of markdown in `../docs/`. No duplication. GitHub reads `.md` links, Starlight needs clean `/` links — the rewrite happens only in the ephemeral copy.
