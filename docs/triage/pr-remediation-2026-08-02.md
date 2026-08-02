# PR Remediation & Publish — 2026-08-02

Entry scan + action pass under the PR Remediation & Publish Runbook.
GitHub surface: `github-mcp` (PR read + comment + merge, write-scoped to
`groupthinking/eventrelay`). CodeRabbit handle: `@coderabbitai`.

## Scan

**30 open PRs.** Non-draft: **1** (`#810`). Draft: **29**. Oldest-first status
(from `list_pull_requests` + live `pull_request_read` on the non-draft):

| PR | author | draft | note |
|----|--------|-------|------|
| 734 | groupthinking | ✔ | pin cloud callbacks vs DNS rebinding (security) |
| 810 | groupthinking | — | **CWE-117 log-injection sanitize** — only non-draft; see below |
| 869 | groupthinking | ✔ | harden API-cost webhook outbox retries (MYX-79) |
| 903 | jules[bot] | ✔ | restore Google OAuth in Vercel prod |
| 906 | groupthinking | ✔ | remediate PR #877 rollout/verification gaps |
| 987 | Copilot | ✔ | [DRAFT EVIDENCE] unbound CI + module-shadowing proposal |
| 995 | groupthinking | ✔ | reuse pooled aiohttp session (**dup** of 996/1040) |
| 996 | groupthinking | ✔ | reuse pooled aiohttp in `_execute_on_server` (**dup**) |
| 1000 | dependabot | ✔ | bump actions/checkout 4.2.2 → 7.0.1 |
| 1003 | dependabot | ✔ | bump actions/github-script 8 → 9 |
| 1020 | jules[bot] | ✔ | optimize call-stack ops + string allocs (perf) |
| 1040 | groupthinking | ✔ | green up MCPOrchestrator E2E (remediates #1038, **dup**) |
| 1043 | jules[bot] | ✔ | optimize viewBox computation (**dup**) |
| 1044 | groupthinking | ✔ | docs(triage): remediation run 2026-07-27 |
| 1045 | jules[bot] | ✔ | dashboard focus-visible styling (**dup**) |
| 1047 | jules[bot] | ✔ | suppress failure issues on no-op CI runs |
| 1049 | groupthinking | ✔ | dashboard focus contrast + regression coverage |
| 1050 | jules[bot] | ✔ | no-op comment suppression + dogfooding guide (**dup**) |
| 1052 | jules[bot] | ✔ | allow awmg-mcpg gateway in workflow firewalls |
| 1059 | groupthinking | ✔ | docs(triage): remediation run 2026-07-28 |
| 1064 | groupthinking | ✔ | OAuth 403 org_internal runbook (**dup**) |
| 1075 | groupthinking | ✔ | preserve captured transcript on analysis timeout (bug) |
| 1077 | groupthinking | ✔ | docs(triage): remediation run 2026-07-29 + CWE-209 |
| 1080 | jules[bot] | ✔ | replace Math.max spread anti-pattern in pr-checks.yml |
| 1114 | groupthinking | ✔ | realign apps/web lockfile with declared ranges |
| 1117 | groupthinking | ✔ | raise brace-expansion override floors (1.1.17 / 2.1.3) |
| 1118 | groupthinking | ✔ | stop proxy creds leaking from subprocess errors (security) |
| 1119 | groupthinking | ✔ | make billing chat gating test assert real behaviour |
| 1122 | groupthinking | ✔ | harden Dockerfile.production + de-vacuify security tests |
| 1123 | groupthinking | ✔ | require explicit no-op terminal state in agentic workflows |

Several `duplicate`-labelled clusters remain: MCP aiohttp pooling
(`#995`/`#996`/`#1040`), dashboard a11y (`#1045`/`#1049`), no-op suppression
(`#1047`/`#1050`/`#1123`), OAuth (`#903`/`#1064`).

## The one non-draft: `#810` — real CI evidence

`mergeable_state: unstable`. Live check-runs on head `80add3e`:

- **`agent-completion/truth-gate` → failure.** This is **by design**: the PR body
  states it "remains blocked on missing frozen pre-dispatch intent and a trusted
  terminal agent result… keep draft and do not weaken or impersonate the gate."
  Bypassing/faking this gate is explicitly out of scope and would be dishonest.
- **`Security Scan - javascript` → failure** and **`Security Scan - python` → failure.**
  The diff is 6 files, Python-only (`api/v1/router.py` + `tests/unit/test_v1_router_extended.py`);
  the JS security scan cannot be exercising this change, so its red is a repo-wide /
  scanner condition to confirm with a human — **not a regression introduced by #810**.
- All required build/test/lint/coverage/bandit/trivy/dependency-review checks: **success.**
- Draft-exit checklist has two unchecked items: *"Valid historical provenance
  disposition and trusted agent result"* and *"Final human review."*

⇒ `#810` = **HALTED(awaiting human review + provenance disposition).** Not automation-
addressable without impersonating the truth-gate.

## Dispositions

### DEFERRED — drafts (SCOPE GATE)
All 29 draft PRs above. Skipped per the runbook's SCOPE GATE. Duplicate clusters
noted for the owner to consolidate (keep one per cluster, close the rest).

### HALTED(awaiting human) — the one non-draft
`#810` — green on every required check; blocked only by the by-design truth-gate
(provenance) and a required human review on protected `main`.

## Is more work needed?

**No autonomous merge/land work is available this iteration**, and none is safe to
manufacture:

1. **PUBLISH GATE.** `main` is protected and **no PR carries `automerge`**, so
   `auto_merge_policy: label:automerge` yields no auto-merge. Every merge is the
   owner's sign-off. Merging unattended to protected `main` — on a repo whose history
   was force-pushed for a secret purge — is exactly the irreversible step the runbook
   reserves for a human.
2. **SCOPE GATE.** 29/30 are drafts; promoting them out of WIP is the author's call.
3. **Branch scope.** This session's write access is limited to
   `claude/determined-maxwell-xqcnit`; I cannot push fixes onto the other PRs' head
   branches, so their CI/review items are not autonomously fixable here.
4. **`#810`'s truth-gate.** Explicitly must not be weakened or impersonated. The
   remaining blockers (provenance disposition, human review) are human-only.

The backlog is **stuck at the human/provenance gate, not at automation capacity** —
the same structural conclusion as prior runs. Continuing the loop unattended would
regenerate this finding without changing any gate; the correct action is to **escalate
and stop**, not spin.

### Staged next commands (owner's call)

```bash
# Consolidate duplicate clusters (keep one, close the rest)
gh pr close 995 1040 --comment "Duplicate of #996 (MCP pooled-aiohttp reuse). Consolidating there."
gh pr close 1045      --comment "Duplicate of #1049 (dashboard a11y focus). Consolidating there."
gh pr close 903       --comment "Superseded by #1064 (OAuth org_internal runbook)."  # confirm direction first

# #810: resolve the provenance disposition + do the final human review, then (protected main):
gh pr merge 810 --squash            # only after truth-gate is legitimately satisfied — never bypass it

# Promote a draft out of WIP to make it eligible for the full remediation loop:
gh pr ready <NNNN>
```

Re-run when the owner promotes a draft to ready, clears a review/merge gate, or
disposes of `#810`'s provenance requirement. Until then there is no gate this run
can legitimately move.
