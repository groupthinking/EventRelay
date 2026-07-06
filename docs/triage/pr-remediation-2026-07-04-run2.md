# PR Remediation Run — 2026-07-04 (run 2)

Authoritative entry-scan + terminal-state disposition of **all open PRs** under the
PR Remediation & Publish Runbook. Supersedes the stale run-1 artifacts (#498/#499),
which described only 10 PRs and predate the 7 Dependabot PRs opened later that day.

- **Surface:** GitHub MCP (PR read + comment + merge), authed as repo owner.
- **Auto-merge policy applied:** merge only the demonstrably-safe, auto-approved,
  CI-only Dependabot action pins; hold everything with a documented breaking change,
  deploy/runtime blast radius, or a branch-protection block for owner sign-off.
- **Deploy safety:** `deploy-cloud-run.yml` is `workflow_dispatch`-only — a merge to
  `main` runs CI but does **not** trigger a production deploy. This is what makes the
  safe subset safe to merge unattended.

## Actions taken this run

- **MERGED #501** — `actions/setup-python` 5 → 6 (squash). Auto-approved, required
  checks green; the only v6 breaking change (Node 24 / runner ≥ v2.327.1) is already
  satisfied by GitHub-hosted runners, and `deploy-cloud-run.yml` already pinned v6.
- **MERGED #503** — `actions/setup-node` 5 → 6 (squash). Auto-approved, required
  checks green; the v6 "npm-only cache" breaking change does not affect this npm
  (Turbo + npm-workspaces) repo.
- **CLOSED #498, #499** — superseded run-1 triage drafts (documentation-only, stale
  10-PR snapshot). Reversible; consolidated into this doc.

## Oldest-first disposition

| PR | Author | Age | Review/CI | Conflicts | Action taken | Terminal state |
|----|--------|-----|-----------|-----------|--------------|----------------|
| #327 | owner | 06-19 | unknown; large (40 files, +5.8k/-1.8k), stale | mergeability unresolved | Left for owner review | HALTED(needs_review) |
| #365 | fork `kk-agent` | 06-21 | unknown; AI Gateway feature | fork branch — outside push scope | Left for owner | HALTED(fork_needs_review) |
| #414 | jules[bot] | 06-25 | unknown; Dockerfile rewrite | prior run flagged conflict | Left for owner | HALTED(needs_review) |
| #433 | jules[bot] | 06-28 | orphaned-history artifact (1547 files, +25.9k/-142k) | inflated diff from `main` rewrite | Recommend close + re-cut clean test branch | HALTED(orphaned_history) |
| #442 | owner | 06-29 | orphaned-history artifact (384 files, +7.3k/-71.7k); dup of #441 | inflated diff | Recommend decide #442 vs #441, close redundant | HALTED(orphaned_history) |
| #474 | owner | 07-03 | unknown; docstrings (23 files) | prior run flagged conflict | Left for owner | HALTED(needs_review) |
| **#478** | owner | 07-03 | **ready; required checks green** except live-E2E gate | `blocked` (needs review + E2E) | **Staged for owner merge** — production GCP-secrets + X-API-Key auth fix | HALTED(awaiting_merge_approval) |
| **#488** | owner | 07-03 | **ready; required checks green** except live-E2E gate | `blocked` (needs review + E2E) | **Staged for owner merge** — Upstash Redis credential resolver | HALTED(awaiting_merge_approval) |
| #494 | owner | 07-03 | draft; implements #487's tests (42 py + 8 fe pass) | — | High-value draft — recommend un-draft | DEFERRED(draft) |
| #495 | Copilot | 07-04 | draft; removes committed API keys, fixes 12 import errors (7231 tests pass) | — | High-value draft — recommend un-draft + rotate leaked keys | DEFERRED(draft) |
| ~~#498~~ | owner | 07-04 | draft triage doc (run 1) | — | **CLOSED** (superseded by this doc) | closed |
| ~~#499~~ | owner | 07-04 | draft triage doc (run 1, exact dup of #498) | — | **CLOSED** (duplicate) | closed |
| **#501** | dependabot | 07-04 | green + auto-approved | none (`unstable`) | **MERGED (squash)** | MERGED |
| #502 | dependabot | 07-04 | green + auto-approved | none | Held — `upload-artifact` 4→7 (3-major, ESM) | HALTED(awaiting_review) |
| **#503** | dependabot | 07-04 | green + auto-approved | none | **MERGED (squash)** | MERGED |
| #504 | dependabot | 07-04 | green + auto-approved | none | Held — `github-script` 7→9 breaks `require('@actions/github')` | HALTED(awaiting_review) |
| #505 | dependabot | 07-04 | green + auto-approved | none | Held — `docker/build-push-action` 6→7 (deploy-path blast radius) | HALTED(awaiting_review) |
| #506 | dependabot | 07-04 | green + auto-approved | none | Held — `opencv-python-headless` 4→5 (major runtime lib; 4→5 migration) | HALTED(awaiting_review) |
| #507 | dependabot | 07-04 | green + auto-approved | none | Held — `@opentelemetry/instrumentation` 0.220 (breaking processor ctor) | HALTED(awaiting_review) |

## Staged commands (owner sign-off required)

**Production fixes — need admin-merge (branch protection + live-E2E infra gate):**
```
# #478 — GCP secret wiring + X-API-Key auth on backend proxy routes
gh pr merge 478 --squash --admin
# #488 — Upstash Redis credential resolver
gh pr merge 488 --squash --admin
```
The only failing check on both is `E2E Pipeline Tests`, which runs against the *live*
Cloud Run deployment (chicken-and-egg: the fix must deploy before the live test can
pass). This is a pre-existing infra gate, not a defect in either diff — hence admin-merge.

**Remaining Dependabot bumps — review each breaking note, then:**
```
gh pr merge 502 --squash   # upload-artifact 4→7 (ESM; verify coverage-upload step)
gh pr merge 504 --squash   # github-script 7→9 (audit workflows for require('@actions/github'))
gh pr merge 505 --squash   # docker/build-push 6→7 (validate a manual deploy afterward)
gh pr merge 507 --squash   # otel 0.220 (breaking BatchLogRecordProcessor ctor)
# opencv 4→5 is a major runtime bump — smoke-test video processing before merging:
gh pr merge 506 --squash
```

**Cleanup:**
```
# #433, #442 are orphaned-history artifacts (inflated diffs from the main rewrite):
gh pr close 433   # then re-cut a clean unit-test branch if still wanted
# decide #442 vs #441 (identical cleanup) and close the redundant one
```

## Is more work needed?

**Yes — but nothing further is safely automatable unattended.** Every remaining open
PR is at a human gate: production auth changes (#478/#488) need admin-merge past the
live-E2E infra gate; the remaining Dependabot bumps carry documented breaking changes;
the stale/large/fork/orphaned PRs (#327, #365, #414, #433, #442, #474) need owner
review or a rebase outside this session's push scope; and #494/#495 are drafts awaiting
un-draft. The two safe merges (#501, #503) and the run-1 dedup (#498/#499) are done.

The loop's automatable work has converged. Re-run when the owner clears a gate.
