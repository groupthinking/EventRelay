# Workflow DevKit undici overrides — AUDIT-012

Root `package.json` pins transitive `undici` versions because `@workflow/world-local` and `@workflow/world-vercel` pull conflicting majors.

## Chain

1. **Root override** — `"@workflow/world-local": { "undici": "^7.29.0" }` and matching `@workflow/world-vercel` entry (see `package.json` `overrides`).
2. **Root devDependency** — `"undici": "^8.10.2"` for tooling that resolves from the workspace root.
3. **Next.js** — `apps/web/next.config.js` wraps config with `withWorkflow()` from `@workflow/world-vercel/next`; that plugin expects the overridden world-local graph.

## Operational notes

- After upgrading `@workflow/*`, re-run `npm ls undici` at repo root and confirm a single effective version per workspace child.
- Do not add ad-hoc `undici` overrides in `apps/web/package.json`; keep overrides centralized in the root lockfile.
