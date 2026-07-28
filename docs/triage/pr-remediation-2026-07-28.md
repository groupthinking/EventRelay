# PR Remediation Run — 2026-07-28

Runbook: PR Remediation & Publish Runbook (RASOR). GitHub surface: `github-mcp`
(PR read + comment + merge). Scan performed against `groupthinking/eventrelay`,
oldest-first. Auto-merge policy: `label:automerge` (no open PR carries it) → every
merge to protected `main` remains a human gate by design.

## Definition-of-done outcome

- **Open PRs scanned:** 33
- **Autonomously mergeable this run:** 0 — the correct, safe outcome, not a failure.
  32 PRs are drafts (scope-gated → `DEFERRED`); the single ready PR (#903) is
  hard-gated on human production-OAuth approval (→ `HALTED`).
- **Action taken:** #903 re-diagnosed (conflict picture corrected — see below);
  all drafts recorded as deferred; no protected-branch merge performed without
  human sign-off, per the runbook publish gate.

## The one ready PR — #903 `fix(auth): restore Google OAuth configuration`

**Terminal state: `HALTED(awaiting_human_production_approval)`**

- `mergeable_state: dirty`. Merging current `main` now yields **three** conflicts
  (the prior run recorded one): `app/login/GoogleSignInButton.tsx`,
  `app/login/page.tsx`, `lib/__tests__/auth-config-source.test.ts`.
- Cause: PR **#1057 "harden google signin"** merged to `main` and independently
  added the same login UI (`GoogleSignInButton.tsx`, `login/page.tsx`). #903's UI
  portion is therefore **superseded by main**; the conflicts are cosmetic
  (default vs named export, styling, an extra Terms/Privacy block).
- #903's only remaining **unique substantive change** is the auth env-name
  precedence flip in `apps/web/src/lib/auth.ts`:
  - `main`: `GOOGLE_OAUTH_CLIENT_ID || GOOGLE_CLIENT_ID` (legacy-first)
  - `#903`: `GOOGLE_CLIENT_ID || GOOGLE_OAUTH_CLIENT_ID` (canonical-first)
- Why it is not merged autonomously:
  1. The repo owner **twice restored this PR to draft** and explicitly reserved
     the merge for a human — the precedence flip must not land before production
     env migration or it risks recreating the `client_id is required` outage;
     production credential + Google callback + real sign-in verification is tracked
     on **#900** and is human-owned.
  2. Conflict resolution is the runbook's "both sides changed the same logic"
     case (main authored its own login UI) → escalate, not blind-resolve.
  3. `agent-completion/truth-gate` CI is red on procedural grounds
     (agent_login / run_id mismatch), tracked in **#898 / #899** — not on the auth
     change itself.
- **Staged human decision / next commands:**
  - *Option A (recommended):* close #903 as superseded by #1057, then port only
    the canonical-first `auth.ts` precedence flip as a small dedicated PR once
    production env migration on #900 is confirmed.
  - *Option B:* resolve the 3 cosmetic conflicts on the app-owned `jules-*`
    branch (keeping main's UI variant + #903's `auth.ts` precedence), complete
    #900 production verification, then merge.
  - Note: direct push to the app-owned `jules-15243187445261469621-ffdb089e`
    branch was rejected in the prior controller context.

## Deferred — drafts (scope gate: draft → `DEFERRED(draft)`)

| PR | Age (d) | Author | Title | Terminal state |
|----|---------|--------|-------|----------------|
| 734 | 16 | groupthinking | fix(security): pin cloud callbacks against DNS rebinding | DEFERRED(draft) |
| 810 | 11 | groupthinking | fix(security): sanitize user-controlled values in API logs | DEFERRED(draft) |
| 831 | 11 | groupthinking | fix(security): restore CWE-209 response protections | DEFERRED(draft) |
| 869 | 10 | groupthinking | fix: harden API-cost webhook outbox retries (MYX-79) | DEFERRED(draft) |
| 906 | 8 | groupthinking | fix(ci): remediate PR #877 rollout and verification gaps | DEFERRED(draft) |
| 961 | 5 | jules[bot] | [DRAFT EVIDENCE] duplicate dashboard accessibility proposal | DEFERRED(draft) |
| 987 | 3 | Copilot | [DRAFT EVIDENCE] unbound CI and module-shadowing proposal | DEFERRED(draft) |
| 995 | 3 | groupthinking | perf(mcp): reuse pooled aiohttp session in orchestrator | DEFERRED(draft) |
| 996 | 3 | groupthinking | fix(mcp): actually reuse pooled aiohttp session | DEFERRED(draft) |
| 997 | 3 | jules[bot] | Bolt: optimize layout boundary in AgentFlowVisualizer | DEFERRED(draft) |
| 999 | 3 | dependabot | build(deps): bump gh-aw-actions/setup 0.82.14→0.83 | DEFERRED(draft) |
| 1000 | 3 | dependabot | build(deps): bump actions/checkout 4.2.2→7.0.1 | DEFERRED(draft) |
| 1001 | 3 | dependabot | build(deps): bump actions/setup-python 6→7 | DEFERRED(draft) |
| 1002 | 3 | dependabot | build(deps-dev): bump locust 2.45.0→2.46.0 | DEFERRED(draft) |
| 1003 | 3 | dependabot | build(deps): bump actions/github-script 8→9 | DEFERRED(draft) |
| 1004 | 3 | dependabot | build(deps): bump @opentelemetry/exporter-trace-otlp-http | DEFERRED(draft) |
| 1005 | 3 | dependabot | build(deps): bump @opentelemetry/core 2.9.0→2.10.0 | DEFERRED(draft) |
| 1006 | 3 | dependabot | build(deps): bump @opentelemetry/instrumentation | DEFERRED(draft) |
| 1007 | 3 | dependabot | build(deps): bump @opentelemetry/resources 2.9.0→2.10.0 | DEFERRED(draft) |
| 1008 | 3 | dependabot | build(deps): bump @opentelemetry/sdk-trace-base | DEFERRED(draft) |
| 1020 | 2 | jules[bot] | perf: optimize call stack operations and string allocations | DEFERRED(draft) |
| 1022 | 2 | jules[bot] | perf(web): optimize bounding box in AgentFlowVisualizer | DEFERRED(draft) |
| 1038 | 1 | jules[bot] | feat: implement MCPOrchestrator._execute_on_server E2E | DEFERRED(draft) |
| 1040 | 1 | groupthinking | fix(mcp): green up MCPOrchestrator._execute_on_server E2E | DEFERRED(draft) |
| 1043 | 1 | jules[bot] | perf(web): optimize viewBox boundary computation | DEFERRED(draft) |
| 1044 | 1 | groupthinking | docs(triage): PR remediation run 2026-07-27 | DEFERRED(draft) |
| 1045 | 1 | jules[bot] | Palette: add keyboard focus-visible styling to dashboard | DEFERRED(draft) |
| 1047 | 1 | jules[bot] | ci: suppress failure issues on no-op runs | DEFERRED(draft) |
| 1049 | 1 | groupthinking | fix(a11y): complete dashboard focus contrast + coverage | DEFERRED(draft) |
| 1050 | 1 | jules[bot] | configure agentic workflows no-op comment suppression | DEFERRED(draft) |
| 1052 | 1 | jules[bot] | fix: allow awmg-mcpg gateway in workflow firewalls | DEFERRED(draft) |
| 1055 | 0 | dependabot | build(deps): bump npm-minor-patch group | DEFERRED(draft) |

## Loop decision

**More autonomous work available: no.** Every open PR is either a draft (author must
mark ready) or human-gated (#903 production OAuth). The remediation loop cannot
advance any PR to `MERGED` without a human: draft PRs need their authors to request
review, and #903 needs the owner to (a) decide close-as-superseded vs. resolve-and-merge
and (b) complete the #900 production verification. Recommend the loop idle until a
draft flips to ready or the owner acts on #903.
