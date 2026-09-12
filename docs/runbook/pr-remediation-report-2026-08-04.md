# PR Remediation & Publish Runbook — Execution Report

**Run date:** 2026-08-04 (scheduled, unattended)
**Surface:** GitHub MCP (read + comment + merge capable)
**Scope:** `groupthinking/eventrelay`, all open PRs, oldest-first
**Parameters as invoked:** `auto_merge_policy: label:automerge`, `merge_method: <unfilled>`, `non_github_hosts: []`

> **Historical as of 2026-08-04. Superseded in part — do not action the gate
> recommendations below.** `agent-completion/truth-gate` and `Agent completion
> enforcement` were retired outright in #1434 (closing #1432), together with
> `agent-completion-enforcement.yml`, `agent_completion_gate.py`, and
> `.github/agent-lock/trusted-publishers.json`. The deadlock this report measures
> was structural, not a payload bug: `PR Governance` requires a linked issue, that
> issue arms the truth gate, and the armed gate then demands an intent snapshot only
> dispatch-originated work can have. The observations below remain an accurate
> record of the queue on the run date; the remedies do not.

---

## Definition of Done — outcome

Per the runbook, a PR is done only at `MERGED`, `DEFERRED(reason)`, or `HALTED(reason)`.
This run drove all 30 open PRs to a terminal state. **Zero were merged**, and that is the
correct outcome — see "Why nothing was merged" below. This is not a reporting-only stop:
every open PR carries a terminal state and, where blocked, a staged next command for a human.

## Headline

- **30 open PRs, every one a draft, all targeting protected `main`.**
- **No PR carries the `automerge` label**, so under `auto_merge_policy: label:automerge`
  none is eligible for autonomous merge. The runbook's Publish Gate is human-by-default.
- The dominant red check is the repo's **own governance gate**
  (`agent-completion/truth-gate/pr-*`), not code defects:
  - **12 PRs** fail only because the gate itself errored with `invalid_payload`
    (a gate-infra bug): #996, #1020, #1040, #1043, #1045, #1049, #1080, #1117, #1123, #1145, #1154, #1155.
  - The rest fail the gate on `draft_pr` / `missing_agent_result` /
    `missing_copilot_current_head_review` / `scope_drift` evidence requirements — all of
    which are functions of the PR being an un-promoted draft, not of the diff.
- **`main` itself is red.** Per #1156's own description, `dependency-review` and `gitleaks`
  fail on `main`, so every open PR inherits red checks no author can fix. Multiple PRs note
  the truth-gate is repo-wide/pre-existing and that #1108, #1103, #1098 were **merged
  regardless** — i.e. the maintainer overrides this gate by hand, per-PR.
- **CodeRabbit review loop could not engage**: CR reports "Review skipped: excluded by label
  configuration" or "rate limited" on almost every PR, so the runbook's step-4 review loop
  has nothing to drive.

## Why nothing was merged (the human gate held, deliberately)

1. **Protected base + no `automerge` label.** Runbook §8: "Do not auto-merge to a protected
   branch." All 30 target `main`; none is labelled `automerge`. Policy result: HALT, not merge.
2. **Every PR is a draft.** Runbook §2 Scope Gate: draft → DEFERRED. The maintainer's
   convention is clearly to keep agent-authored PRs in draft until a human promotes them.
3. **The blocking check is a known-broken governance gate the maintainer overrides manually.**
   Overriding it autonomously — for 30 PRs, unattended — would substitute this run's judgment
   for the human's on an irreversible, protected-branch action. That is exactly the line §8
   forbids crossing.
4. **Even the green-check PRs are not cleanly mergeable.** #1118 is `dirty` (real merge
   conflict vs `main`), #1114 is `unknown`, #1000/#1119/#1156 are `unstable`.

No CodeRabbit comment loops were posted: CR is label-excluded/rate-limited on these PRs, and
blasting 30 threads in an unattended run with no reviewer engagement would be noise, not
remediation.

---

## Oldest-first status table

| PR | Author | Age (d) | Title | Combined CI | Truth-gate | Conflicts | Action taken | Terminal state |
|----|--------|--------:|-------|-------------|-----------|-----------|--------------|----------------|
| #734 | groupthinking | 23 | pin cloud callbacks vs DNS rebinding | failure | draft_pr + evidence | — | observed | DEFERRED(draft) |
| #810 | groupthinking | 18 | sanitize API logs (CWE-117) | failure | scope_drift + draft_pr | — | observed | DEFERRED(draft) |
| #869 | groupthinking | 17 | harden API-cost webhook outbox (MYX-79) | failure | evidence | Vercel canceled | observed | DEFERRED(draft) |
| #903 | jules[bot] | 15 | restore Google OAuth in Vercel prod | failure | draft_pr + missing_test_evidence | Vercel canceled | observed | DEFERRED(draft) |
| #906 | groupthinking | 14 | remediate PR #877 rollout gaps | failure | unresolved_review + scope_drift | Vercel deploy failed | observed | DEFERRED(draft) |
| #996 | groupthinking | 10 | reuse pooled aiohttp session | failure | **invalid_payload** (gate bug) | — | observed | DEFERRED(draft) |
| #1000 | dependabot | 10 | bump actions/checkout 4→7 | **success** | passed | unstable | observed; merge-ready pending human | HALTED(awaiting_merge_approval) |
| #1003 | dependabot | 10 | bump actions/github-script 8→9 | failure | passed | — | observed | DEFERRED(draft) — Vercel deploy failed |
| #1020 | jules[bot] | 9 | optimize call stacks/allocations | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft) |
| #1040 | groupthinking | 8 | green up MCPOrchestrator E2E | failure | **invalid_payload** (gate bug) | — | observed | DEFERRED(draft, dup label) |
| #1043 | jules[bot] | 8 | optimize viewBox computation | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft, dup label) |
| #1045 | jules[bot] | 8 | dashboard focus-visible styling | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft, dup label) |
| #1049 | groupthinking | 8 | dashboard focus contrast + coverage | failure | **invalid_payload** (gate bug) | — | observed | DEFERRED(draft) |
| #1050 | jules[bot] | 8 | no-op comment suppression + guide | failure | evidence + scope | Vercel canceled | observed | DEFERRED(draft, dup label) |
| #1052 | jules[bot] | 8 | allow awmg-mcpg gateway in firewalls | failure | evidence + missing copilot-rabbit label | Vercel canceled | observed | DEFERRED(draft) |
| #1064 | groupthinking | 7 | OAuth 403 org_internal runbook | failure | evidence | Vercel canceled | observed | DEFERRED(draft, dup label) |
| #1075 | groupthinking | 6 | preserve transcript on analysis timeout | failure | scope_drift + draft_pr | Vercel canceled | observed | DEFERRED(draft) |
| #1080 | jules[bot] | 6 | replace Math.max spread in pr-checks | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft) |
| #1114 | groupthinking | 5 | realign apps/web lockfile | **success** | passed | unknown | observed; merge-ready pending human | HALTED(awaiting_merge_approval) |
| #1117 | groupthinking | 5 | raise brace-expansion override floors | failure | **invalid_payload** (gate bug) | — | observed | DEFERRED(draft) |
| #1118 | groupthinking | 4 | stop proxy credentials leaking (security) | **success** | passed | **dirty (conflict)** | observed; conflict staged | HALTED(merge_conflict) |
| #1119 | groupthinking | 4 | billing chat gating test asserts real behaviour | **success** | passed | unstable | observed; merge-ready pending human | HALTED(awaiting_merge_approval) |
| #1122 | groupthinking | 4 | harden Dockerfile.production | failure | passed | Vercel canceled | observed | DEFERRED(draft) — Vercel canceled |
| #1123 | groupthinking | 4 | require explicit noop terminal state (aw) | failure | **invalid_payload** (gate bug) | — | observed | DEFERRED(draft) |
| #1129 | groupthinking | 4 | route transcript clients through proxy | failure | passed | Vercel canceled | observed | DEFERRED(draft) — Vercel canceled |
| #1132 | Copilot | 4 | authenticate task requests before validation (security) | failure | draft_pr + evidence | Vercel canceled | observed | DEFERRED(draft) |
| #1145 | jules[bot] | 3 | fix internal error message leakage (security) | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft) |
| #1154 | groupthinking | 3 | scope agent gate to real dispatch evidence | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft) |
| #1155 | groupthinking | 3 | repair one-click deploy paths/manifests | failure | **invalid_payload** (gate bug) | Vercel canceled | observed | DEFERRED(draft) |
| #1156 | groupthinking | 3 | drop phantom python-jose (security) | **success** | passed | unstable | observed; merge-ready pending human | HALTED(awaiting_merge_approval) |

**Terminal-state tally:** 0 MERGED · 25 DEFERRED(draft) · 5 HALTED (4 awaiting_merge_approval, 1 merge_conflict).

---

## HALTED PRs — blocker + staged next command

These 5 have a **passing truth-gate and all-green (or mergeable) checks**; they are the
prime candidates for a human to promote and merge. All are drafts, so step 1 for each is
"mark ready for review", then merge on the base branch's protection policy.

- **#1118** `HALTED(merge_conflict)` — security fix (proxy credential leak). `mergeable_state: dirty`.
  Next: `git fetch origin && git checkout groupthinking-fix-proxy-credential-leakage-and-vacuous && git rebase origin/main` (resolve conflicts) `&& git push --force-with-lease`. Then promote + merge.
- **#1156** `HALTED(awaiting_merge_approval)` — security fix (drop phantom python-jose; also unblocks `main`'s own red `dependency-review`/`gitleaks`). Mergeable. Next: mark ready → `gh pr merge 1156 --squash` (or via UI).
- **#1114** `HALTED(awaiting_merge_approval)` — apps/web lockfile realignment. `mergeable_state: unknown` (recompute on promote). Next: mark ready → merge.
- **#1119** `HALTED(awaiting_merge_approval)` — de-vacuifies billing-gate test (test-only). Mergeable. Next: mark ready → merge.
- **#1000** `HALTED(awaiting_merge_approval)` — dependabot `actions/checkout` 4→7 (major bump; review breaking-change notes). Mergeable. Next: mark ready → merge.

> Merge method was left unfilled in the run parameters; the maintainer should apply the repo's
> standard method. No merge was performed autonomously because the base is protected and no PR
> is labelled `automerge`.

---

## Systemic findings for the maintainer (higher-leverage than any single PR)

1. **`agent-completion/truth-gate` emits `invalid_payload` on 12 of 30 PRs.** This is the gate
   workflow failing to process, not the PRs failing review. Fixing the gate would flip a large
   fraction of the queue from red to evaluable in one change. Candidate owner: whatever builds
   the gate payload (see #1154 "scope agent gate to real dispatch evidence" and #1155/#1123,
   which appear to target this machinery).
2. **`main` is itself red** (`dependency-review` via the unfixable ecdsa/GHSA-wj6h-64fc-37mp
   advisory, and a `gitleaks` false-positive on a package hash). #1156 fixes both at the root —
   merging it first would clear inherited red checks across the whole queue.
3. **The trusted-publication check (`Agent Lock trusted publication`) was not being published**,
   so `Agent completion enforcement` failed repo-wide. This had been overridden manually on
   prior merges (#1108/#1103/#1098). *Resolved by removal:* #1434 retired the gate rather than
   restoring the publishing App. All three allowlists in `trusted-publishers.json` were empty,
   and the file's own note recorded that an empty allowlist blocks rather than downgrading to
   `not_applicable` — so there was no provisioned trust path to restore.
4. **3 PRs are red only on Vercel** with "Canceled from the Vercel Dashboard" (#1122, #1129) or
   a deploy failure (#1003, #1043-class) — manual/infra cancellations, not code. Re-run the
   Vercel deployment to clear.
5. **Draft-as-default workflow.** All 30 PRs are drafts. If the intent is for this remediation
   loop to advance them, the gating human step is promoting drafts to "ready for review";
   nothing downstream can proceed autonomously until that happens.

## Non-GitHub hosts

`non_github_hosts: []` — no GitLab/Bitbucket/Azure/Gitea sub-agents were spawned. Nothing to route.

## Loop status

Every open PR is at a terminal state. All remaining forward motion requires a **human
decision** — promote drafts to ready, override the known-broken governance gate as the
maintainer already does by hand, resolve #1118's conflict, and approve merges to protected
`main` — or an unsafe unattended mutation this run declined to make. There is therefore **no
further autonomous work** this cycle can complete; the loop's answer is "awaiting human," and
it stops here rather than re-scanning to the same result.
