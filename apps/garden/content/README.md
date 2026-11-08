# apps/garden/content/

> ⛔ **Do NOT edit files here by hand.**
> This directory is **generated** from `vault/60-permanent/` by the CI workflow
> [.github/workflows/publish-garden.yml](../../../.github/workflows/publish-garden.yml).
> Only notes with `publish: true` in YAML frontmatter are copied here.

## Pipeline (ADR-0009 — default-deny)

```
vault/60-permanent/*.md           (private repo, all notes)
   │
   ▼  CI filter: parse frontmatter, keep only `publish: true`
apps/garden/content/*.md          (still in private repo, public-bound subset)
   │
   ▼  Quartz build
public/                           (static HTML, deployed to GitHub Pages)
```

## Why this split?

- **Default-deny**: a note is private unless the author explicitly flips
  `publish: true`. Mistakes in the filter still can't leak a note that was
  never explicitly opted in.
- **Defense in depth**: even if `apps/garden/content/` gets polluted
  (e.g. by a stray copy), the canary-test in CI catches it before deploy.
- **History isolation**: the public repo never inherits the full private
  git history — only the filtered subset is exported.

## Negative test

`vault/90-meta/canary-secret.md` contains the marker string
`__CANARY__do_not_publish__` and has **no** `publish: true` flag. CI asserts
this string does NOT appear in `apps/garden/content/` after the filter step.
If it does, the workflow fails fast and deploy is blocked.

## Manual rebuild

```bash
# In apps/garden/:
pnpm install                    # bootstraps ./quartz/
pnpm run build                  # builds content/ → public/
pnpm run serve                  # local preview at http://localhost:8080
```
