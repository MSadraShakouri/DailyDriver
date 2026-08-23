# Wiki Sync (planned)

The `docs/` folder is the single source of truth for DailyDriver's
documentation. It is authored to also read well as a GitHub Wiki.

## Goal

Automatically publish `docs/` to the repository's GitHub Wiki so readers get a
navigable Wiki UI, while docs stay:

- **PR-reviewable** — changes go through normal pull requests;
- **versioned with the code** — docs live in the same repo and history;
- **single-source** — the Wiki is generated, never edited directly.

## Approach (TODO — not yet implemented)

A GitHub Actions workflow triggered on pushes to the default branch that touch
`docs/**` would:

1. Check out the repo and the `<repo>.wiki` Git repository.
2. Copy/transform `docs/**` into the wiki working copy (flattening paths and
   rewriting relative links to Wiki page names as needed).
3. Commit and push the wiki repo when there are changes.

This is intentionally **out of scope** for the current work; it is captured here
and in the [roadmap](roadmap.md) as a one-time future setup. Until then, read
the docs here in the repository.
