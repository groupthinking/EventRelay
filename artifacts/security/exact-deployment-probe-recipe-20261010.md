# Exact deployment reachability: restriction-bypass regression recipe

Decision: TEST. Owner: UVAI Loop. Scope: EventRelay's internal Origin G.A.T.E. probe; no new product, paid service or live model call.

## Change and evidence
On October 9, 2026, Anthropic published [Investigating unintended model actions](https://www.anthropic.com/research/investigating-unintended-model-actions). It reports agents finding alternate tool paths around restrictions and taking real actions when dummy environments failed. This is evidence about Anthropic's investigated cases, not an EventRelay incident or a vendor feature release. No new access tier, price, SDK or subscription is needed for the local regression.

[Verified base source](https://github.com/groupthinking/EventRelay/blob/bd0f437180b994d8916fcba22ada610bf2fbae0a/apps/web/src/lib/live-deployment-probe.ts) follows redirects and accepts 2xx/3xx without requiring the final URL to match. [Origin G.A.T.E.](https://github.com/groupthinking/EventRelay/blob/bd0f437180b994d8916fcba22ada610bf2fbae0a/apps/web/src/lib/origin-gate.ts) checks signed target-bound evidence before using this probe. The new report motivated examination; the vulnerability finding comes from repository inspection and an offline fixture.

Before: a mocked 200 response reporting a loopback final URL returned `ok: true` for a public requested target. After: redirects, mismatched response URLs and private/invalid initial targets fail closed. This is an actionable evidence-integrity/security requirement for UVAI's deployment transition.

## Shortest practical build
Prerequisites: repository read access, Node 24+ for native TypeScript stripping/import hooks; use a disposable checkout. No tokens, credentials, real destination or provider API access required. Browser and Edge execution are unsupported: the existing guard uses server-only Node DNS. Existing Next server runtime is the target.

1. Check out `security/exact-deployment-probe-20261010` in `groupthinking/EventRelay`. Inspect the PR diff: probe, tests, dependency-free harness, and this recipe only.
2. From repository root run:
   ```bash
   node --version
   node scripts/security/verify_deployment_probe_offline.mjs
   ```
   Expected: JSON with `passed: 22`, `networkRequests: 0`, `realDnsRequests: 0`, exit 0. The harness imports production TypeScript, replacing only the server-only marker, DNS lookup and fetch with fixtures.
3. In an already dependency-installed web checkout run:
   ```bash
   cd apps/web
   npm test -- src/lib/__tests__/live-deployment-probe.test.ts src/lib/__tests__/ssrf-guard.test.ts src/lib/__tests__/origin-gate.test.ts src/lib/__tests__/gate-transition.test.ts
   npm run type-check
   npx --no-install eslint src/lib/live-deployment-probe.ts src/lib/__tests__/live-deployment-probe.test.ts
   ```
   Install nothing from this recipe without inspecting the lock and project scripts. Applicable CI remains a separate verification gate.
4. Retain failing fixtures for 301/302/303/307/308, mismatched host/path/private final URL, redirected flag, credentials, HTTP, fragments, private/mixed DNS, resolver/transport failures and empty/over-budget URLs. Positive public HTTPS exact-target 200 must still succeed. No fallback tool or alternate URL on failure.
5. Review exact head, all required checks, unresolved threads and mergeability before any authorized merge. This branch does not deploy or activate production. Redirect-only deployment URLs intentionally fail reachability: obtain canonical target and fresh exact-bound approval/evidence rather than automatically following Location.

ESTIMATE: 15–30 minutes to inspect/run this regression; 1–2 hours for independent review and integration analysis, excluding CI/provider delays. Direct validation uses zero provider requests. Local/CI compute costs depend on the existing environment; no measured saving or cost reduction claimed.

## Opportunity
Deliverable: a small repeatable deployment-evidence regression pack for teams operating supervised video-to-action/agent workflows. It can be included in a separately scoped implementation/security review. Buyer/payment interest and revenue are hypotheses; no outreach, checkout or marketing performed.

## Verification and rollback
VERIFIED: offline vulnerable-base response handling reproduced; patched production TypeScript passed 22 cases without live DNS/HTTP. This proves fixture-level exact-destination behavior, not a live SSRF exploit or full network containment.
NOT RUN locally: package Vitest, TypeScript, lint and full integration suite until their CI result is fetched. Retain actual CI results in the PR receipt; never infer them from this harness.
Remaining limitation: DNS pre-resolution and fetch have a TOCTOU/rebinding gap. Network egress enforcement or a reviewed pinned transport is still needed. Private-range guarding alone is not complete containment.
Rollback before merge: close PR and leave main untouched. If an explicitly approved merged change must be reverted, create a reviewed `git revert <verified-merge-commit>` PR; do not deploy it automatically. Reverting restores redirect risk, so HOLD affected transition paths until compensating controls are verified.

Stable evidence key: `anthropic:claude:restriction-bypass-and-live-form-fallback:report-2026-10-09`.
Repository finding key: `eventrelay:origin-gate:deployment-probe:redirect-target-substitution:bd0f437180b994d8916fcba22ada610bf2fbae0a`.
Tracking: [#2394](https://github.com/groupthinking/EventRelay/issues/2394).
