# PR Remediation & Publish — Run 8 (2026-07-07)

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`.

## Scan

**27 open PRs** — 1 non-draft (`#529`), 26 drafts.

Per the **SCOPE GATE**, all 26 drafts (`[WIP]` Claude branches, Copilot feature drafts,
skills/test drafts, and the run-5/6/7 triage docs `#566`/`#576`/`#583`/`#584`) →
**DEFERRED**. That leaves exactly one actionable PR: **#529**.

## #529 — material change since run 7

Run 7 (`#584`) halted `#529` as **HALT(merge_conflict)** — it was `dirty` on
pre-rewrite orphaned history, and the owner had posted a disposition recommending
**close as superseded**, objecting specifically that the PR re-introduced root
`vercel.json` `functions`/`regions`/redirect overrides that commit `6a89646`
deliberately removed (Vercel Root Directory is `apps/web`, so root-level config is
inert).

Since then the branch **advanced** and now resolves both blockers:

| Gate | Run 7 | Run 8 (now) |
|------|-------|-------------|
| Conflicts | `dirty` (real conflicts) | **resolved** — `14f5f60` merged current `main` in; `mergeable_state` is now `blocked`, not `dirty` |
| Owner's objection (root `vercel.json` overrides) | present | **addressed** — head `43648a3` strips the root `vercel.json` overrides (−63) and moves host redirects to `apps/web/next.config.js` (+20), exactly as the owner asked |
| CI | n/a (conflicted) | **green** — CI, CodeQL, Coverage, Security Scan, Secret Scan, Dependency Review, PR Checks all `success`; E2E/Dependabot `skipped` |
| Vercel | — | preview `Canceled from the Vercel Dashboard` (owner-initiated, not a code failure); required `Vercel Deployments – garv_projects` context = `success` |
| Review | 2× owner `APPROVED` on `8de7c28` | those approvals are **stale** (head moved to `43648a3`); owner's latest action is a `COMMENTED` review on the new head |

## Disposition

| PR | Author | Review | CI | Conflicts | Action taken | Terminal state |
|----|--------|--------|----|-----------|--------------|----------------|
| #529 | Copilot | approved (stale) + owner recommend-close | ✅ green | none (blocked) | Verified rework addresses owner's sole objection; CI now green; no code fix aligns with owner intent (owner leaned close) | **HALTED(awaiting_owner_decision)** |
| 26 others | — | — | — | — | draft / WIP / prior triage docs | **DEFERRED** |

## Is more work needed?

**No — converged.** `#529` is de-conflicted, CI-green, and reworked to remove the
exact overrides the owner objected to. It is now a clean **binary owner decision**,
not an engineering task:

- The remaining block is branch protection (fresh approval required on `43648a3`;
  the prior approvals were on the superseded `8de7c28`) plus the owner-canceled
  Vercel preview.
- Merging against the owner's standing "recommend close as superseded" would not be
  faithful to intent, and auto-merge to protected `main` requires human sign-off
  (PR is not `automerge`-labeled). → **do not auto-merge, do not unilaterally close.**

### Staged next commands (owner's call)

```bash
# Option A — accept the slimmed-down rework: re-approve on 43648a3, then squash-merge
gh pr review 529 --approve
gh pr merge 529 --squash

# Option B — the owner's earlier recommendation: close as superseded by main
gh pr close 529 --comment "Superseded by main; unique pieces already landed via 90ee99a/6a89646."
```

All other open PRs remain owner-authored drafts. Re-run when the owner clears the
`#529` gate or promotes a draft out of WIP.
