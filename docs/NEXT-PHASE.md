# Next phase — Origin G.A.T.E.

- **Reviewed:** 2026-09-13
- **Authority:** [../AGENTS.md](../AGENTS.md)
- **Plan:** [MASTER_ROADMAP.md](MASTER_ROADMAP.md)

The former P3 “Act on the same run” document described an earlier cut. Same-run actions already exist in `OneLoopStudio`; do not restart that work or use its historical `/` routing as current guidance. `/studio` is the canonical workbench.

## Next owned slice

Origin G.A.T.E. is the only cut authorized by root policy. The requested implementation now covers the `studio.deploy` proposed-to-live acceptance boundary: session-derived identity, scoped independent Ed25519 attestations, exact artifact/run/target binding, signed retained receipts, and atomic replay protection. See the [current contract](gate-transition-contract.md).

**Goal:** make the approved consequential transition depend on trustworthy evidence and authority, without changing the fail-closed decision vocabulary or creating a second product.

Studio distinguishes authoritative server decisions from local diagnostics. A valid HTTPS hostname is no longer upgraded into verified deployment evidence. The legacy deployment kickoff is held because regenerating from a video cannot guarantee the approved artifact bytes.

## Implementation-proof handoff — 2026-09-13

The approved cut verifies the existing implementation rather than restarting it. The [contract evidence record and named-test matrix](gate-transition-contract.md#executable-contract-map) identify the tested baseline/worktree, commands, runtime versions, reports, and limitations.

- **Software-contract verification:** 326 focused tests passed across 9 files, with no failures or skips. Exact binding, both signer roles, decision precedence, cryptographic receipt checks, freshness, replay/retention and consumer behavior are covered. The full web suite passed 1,169 tests across 119 files, with one unrelated opt-in Video Pack test skipped. Web type-check, targeted lint, CI YAML checks and lock consistency passed.
- **Isolated integration verification:** all 26 actual-Lua Redis cases executed, including 16 real route → NextAuth → evaluator → REST adapter → Lua cases. A fake external transport forwards only to disposable Unix-socket Redis, never the connected store. Valid acceptance still cannot start the legacy deployment. Component tests cover all four decisions and stale-selection isolation; a local browser smoke confirmed the explicit preflight-only UI.
- **Production authorization/acceptance not established:** hosted storage, independent operational key ownership, actual provider evidence/health, authenticated browser acceptance, deployed routing and remote CI were not verified. No registry, credentials, production data, deployment, operational PASS or later-phase approval was created. These checks were excluded by the approved scope, not treated as prerequisites for software verification.

The only production change is a regression-proven one-line receipt-consumer guard: envelope reasons/codes must match the receipt before being shown as a server decision. Evaluator, session verification, REST storage, Lua, and deployment execution remain unchanged. CI now opts into the required Redis tests and retains its machine-readable report on success or failure; no remote run/artifact is claimed yet.

**Next ownership decision:** UVAI Loop may separately authorize an operational acceptance exercise or another named cut. Do not request authority records again merely to repeat the offline proof, or interpret test fixtures as that authorization. Do not deploy, add credentials, mutate production data, or weaken the gate.

## Acceptance

- Every scoped decision is exactly PASS, HOLD, REJECT, or ESCALATE.
- Missing/weak required evidence stays HOLD; unreal evidence or an invalid live claim is REJECT; unknown authority/verdict is ESCALATE.
- Known actor labels do not substitute for server authorization.
- A completed workflow or generated bundle without the required receipt never becomes a live-success claim.
- The visible receipt identifies the decision, reason, transition, and canonical hash; it is tied to the current run, not a stale selected video.
- Tests exercise failure paths as well as the accepted case. Any fresh operational PASS cites the actual verification run.

## Starting checks

From repository root:

```bash
npm --workspace=apps/web run test:gate -- --reporter=default --reporter=json --outputFile.json=/tmp/origin-gate-focused.json
```

Use the declared npm 10.8.0 and a local `redis-server` or `redis6-server`. The script enables all required isolated gate cases and fails if Redis is unavailable. It proves the named software boundary with offline fixtures, not production authority or a live deployment; see the contract record for the full regression/static checks and historical observations.

## Held work

- `asRecord` / claim changes unless this authorized cut specifically requires them.
- Extractor expansion, new storage, or a broader assembly/build system without Loop approval.
- Mission Workspace, Agent Factory / Slingshot, ExperienceOS, or a new FORGE product.
- Replaying old App Builder VM/PR receipts as current evidence, deleting synced external records, or promoting production as “cleanup.”

Use [GOAL.md](GOAL.md) only after the owned slice is confirmed. The later build-out sequence remains proposed in [MASTER_ROADMAP.md](MASTER_ROADMAP.md).
