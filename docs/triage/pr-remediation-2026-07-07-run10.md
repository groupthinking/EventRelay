# PR Remediation & Publish — Run 10 (2026-07-07)

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.

## Scan

**26 open PRs** — 2 non-draft (`#585`, `#588`), 24 drafts.

Per the **SCOPE GATE**, the 24 drafts (`[WIP]` Claude branches, Copilot feature
drafts, skills/test drafts) → **DEFERRED**. Actionable set: `#585`, `#588`.

Context vs. run 9 (`#589`, branch `claude/determined-maxwell-nbnstz`): run 9 declared
convergence with `#588` still a **draft** in the "Sentry CI-fix cluster." Since then
`#588` was **un-drafted, owner-approved, and re-deployed** — so its state changed and
it re-enters the actionable set. (Run 9's doc `#589` was closed unmerged; `main` HEAD
is still the run-8 doc `ed5f3cd`.)

## #588 — owner-approved but build-breaking → **do not merge**

`fix(web): bump @sentry/nextjs to ^11.0.0` (Copilot, non-draft, **owner APPROVED** on
head `9184fab`). Stated intent: fix "CI failures caused by a `@sentry/nextjs`/Next.js
compatibility break."

**Finding: the change points `@sentry/nextjs` at a version that does not exist**, which
breaks `npm install` for the whole repo. Evidence:

- Vercel build (`dpl_7j5fusq7…`) → `ERROR` at install:
  ```
  npm error notarget No matching version found for @sentry/nextjs@^11.0.0.
  Error: Command "cd ../.. && npm install --legacy-peer-deps" exited with 1
  ```
- npm dist-tags for `@sentry/nextjs`: `latest: 10.63.0`, `v9: 9.47.1`, `v8: 8.55.2`,
  `v7: 7.120.4`. There is **no 11.x**. `^11.0.0` is unresolvable.

**The premise is also false.** `main` already pins `@sentry/nextjs@^10.63.0` (the
current latest) on Next `^16.2.10`, and its production deployment is green
(`191a82f` → `READY`). There is no Sentry/Next-16 build break to fix on `main`, and no
newer Sentry major to move to. Reverting the diff to `^10.63.0` just re-creates `main`
(a no-op) — so `#588` has no valid form in which it does something and is safe.

Posted the finding + evidence as a top-level comment on `#588` (recommend close;
if a genuine Sentry-under-Next-16 hardening is wanted, that is the code-level guard in
draft `#570`, not a version bump). **Did not merge** — merging would break `main`, and
overriding the fresh owner approval by unilaterally closing is left to the owner.

## #585 — redundant run-8 triage doc

`#585` is `docs(triage): PR remediation run 8` (branch
`claude/determined-maxwell-8bpplz`). The run-8 doc already landed on `main` as
`ed5f3cd` via a different branch, so `#585` is a **duplicate whose content is already
merged** → **DEFERRED (redundant; owner may close).**

## Disposition

| PR | Author | Review | CI | Conflicts | Action taken | Terminal state |
|----|--------|--------|----|-----------|--------------|----------------|
| #588 | Copilot | owner APPROVED | ❌ red (unresolvable dep) | none (blocked) | Diagnosed phantom dep; posted evidence + Request-Changes review; not merged[^588] | **HALTED(broken_change_awaiting_owner_close)** |
| #585 | Claude | — | — | — | Redundant run-8 triage doc; content already on `main` (`ed5f3cd`) | **DEFERRED (redundant)** |
| 24 others | — | — | — | — | draft / WIP | **DEFERRED** |

[^588]: `#588` bumps `@sentry/nextjs` to `^11.0.0`, which does not exist on npm
    (`latest` is `10.63.0`); `npm install` fails with `ETARGET` and the Vercel build
    errors, so merging would break `main`. Diagnosis + evidence posted as a top-level
    comment and a formal Request-Changes review on the PR. See the `#588` section above.

## Is more work needed?

**No autonomous engineering work remains.** The one ready code PR (`#588`) is
objectively broken (targets a nonexistent dependency version) and cannot be made to do
anything useful — `main` already runs the latest valid Sentry and builds green. The
remaining decisions are the owner's:

### Staged next commands (owner's call)

```bash
# #588 — recommended: close (nonexistent version target; nothing to upgrade to)
gh pr close 588 --comment "No @sentry/nextjs 11.x exists (latest is 10.63.0, already on main). Closing; use code-level guard (#570) if hardening is wanted."

# #585 — optional cleanup: close the redundant run-8 triage doc
gh pr close 585 --comment "Superseded — run-8 triage doc already landed on main via ed5f3cd."
```

Re-run when the owner clears the `#588` gate or promotes a draft out of WIP.
