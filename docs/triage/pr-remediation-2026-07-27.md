# PR Remediation & Publish — 2026-07-27

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge). CodeRabbit handle: `@coderabbitai`
(`.coderabbit.yaml` present, `request_changes_workflow: true`, `auto_review.drafts: false`).

## Scan

**38 open PRs** (up from 35 at the 2026-07-17 run). **Draft: 37. Non-draft: 1 (`#1043`).**

The population has shifted decisively toward *draft*: nearly every open PR has been
parked as a draft since the last run, which is the SCOPE-GATE signal (draft = WIP /
deferred) and also matches the repo's own CodeRabbit policy (`auto_review.drafts: false`
— CodeRabbit deliberately does **not** review drafts). Only one PR is `Ready for review`.

### Draft population (37) — by cluster

| Cluster | PRs | Disposition |
|---------|-----|-------------|
| Dependabot bumps | `#980` `#983` `#999`–`#1010` (14) | DEFERRED(draft) — auto-update PRs, human batch-merge |
| Security hardening | `#734` `#810` `#831` `#869` `#929` `#948` | DEFERRED(draft) |
| MCP execution / orchestrator | `#994` `#995` `#996` `#1038` `#1040` | DEFERRED(draft) — `#1040` remediates `#1038` |
| Perf / Bolt (SVG/viewBox/call-stack) | `#973` `#987` `#997` `#1020` `#1022` | DEFERRED(draft) — same AgentFlowVisualizer family as `#1043` |
| a11y (dashboard focus) | `#918` `#961` | DEFERRED(draft) — `#961` is a self-declared duplicate |
| OAuth / portable paths | `#896` `#903` | DEFERRED(draft) |
| CI / governance / audit | `#906` `#990` | DEFERRED(draft) |
| Docs | `#932` | DEFERRED(draft) |

### Non-draft (1)

| PR | author | mergeable_state | CI (real) | review | note |
|----|--------|-----------------|-----------|--------|------|
| 1043 | google-labs-jules[bot] | unstable | ❌ **governance gates red** | none (owner requested) | ⚡ Bolt viewBox O(N) rewrite of `AgentFlowVisualizer.tsx` |

## Dispositions

### DEFERRED — drafts (SCOPE GATE)
All **37** draft PRs. Per the runbook scope gate and the repo's `auto_review.drafts: false`
policy, drafts are WIP and are not reviewed, fixed, or merged by this pass. No CodeRabbit
commands were posted to them (posting to drafts would be noise against the repo's own
configured policy).

### HALTED(awaiting_merge_approval) — `#1043`
The only `Ready` PR. It cannot be driven to `MERGED` autonomously:

1. **Governance gates are red, by design.** `agent-completion/truth-gate` reports
   `invalid_payload` (missing `issue.number`, `policy.agent_login`, `policy.run_id`),
   and `PR Governance` / `Canonical issue and evidence` / `Agent completion enforcement`
   all fail. These gates deliberately require the **originating agent (Jules)** to supply
   a canonical linked issue and agent-completion evidence. Fabricating that payload to
   pass the gate would bypass a deliberate governance control — out of bounds.
2. **PR title is non-conventional** (`⚡ Bolt: …`) → `pr-validation` warns. A conventional
   rename (e.g. `perf(web): …`) would clear that one check but not unblock merge.
3. **Protected `main` + human sign-off.** Owner `@groupthinking` is the requested
   reviewer; there is no `automerge` label. The runbook publish gate (and every prior
   run) leaves merge to `main` for the human.
4. No CodeRabbit findings or review threads exist yet (PR is minutes old at scan time);
   the review-resolution loop has nothing actionable, and the block above is independent
   of CodeRabbit.

**Staged next command (for the owner, once Jules supplies canonical evidence and CI is green):**

```
# after truth-gate passes and required checks are green:
gh pr merge 1043 --squash --repo groupthinking/eventrelay
```

## Terminal-state summary

| State | Count | PRs |
|-------|-------|-----|
| DEFERRED(draft) | 37 | all drafts |
| HALTED(awaiting_merge_approval) | 1 | `#1043` |
| MERGED | 0 | — |

**No autonomous merge work was available this run.** Every open PR is either draft-parked
(deferred) or blocked on a human/originating-bot gate (`#1043`). This is consistent with
the established behavior of this routine: it automates toil up to the irreversible step
and halts at the human merge gate on protected `main`.
