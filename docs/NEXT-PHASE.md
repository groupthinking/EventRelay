# Next phase — Origin G.A.T.E.

- **Reviewed:** 2026-09-13
- **Authority:** [../AGENTS.md](../AGENTS.md)
- **Plan:** [MASTER_ROADMAP.md](MASTER_ROADMAP.md)

The former P3 “Act on the same run” document described an earlier cut. Same-run actions already exist in `OneLoopStudio`; do not restart that work or use its historical `/` routing as current guidance. `/studio` is the canonical workbench.

## Next owned slice

Origin G.A.T.E. is the only next cut authorized by root policy. UVAI Loop must confirm the exact slice before implementation, including whether previously parked live-URL verification is in scope. This document is a plan, not a new authorization or a claim that the slice has shipped.

**Goal:** make the approved consequential transition depend on trustworthy evidence and authority, without changing the existing fail-closed decision vocabulary or creating a second product.

The current contract and Studio chip are already implemented. The remaining boundary to resolve is that the Studio caller supplies `anonymous` authority and the adapter treats a validated HTTPS hostname URL as its `real` evidence signal. That is not independently authenticated authority, provider ownership, deployment health, or artifact verification.

## Proposed implementation sequence

1. **Lock the contract slice.** Name the exact transition, caller, required evidence, evidence verifier, and what stays proposed. Preserve compatibility with the existing [gate contract](gate-transition-contract.md).
2. **Bind authority and evidence at the owned server boundary.** Derive authority from the actual trusted context; tie accepted receipts to the expected run/artifact and permitted target. Do not trust browser actor strings as authorization.
3. **Handle retries and negative evidence.** Define idempotency and reject/hold/escalate behavior for stale, replayed, mismatched, unknown, missing, or unavailable results. Keep receipt retention with its approved runtime owner, not inside a new G.A.T.E. database.
4. **Verify the exact user path.** Run focused contract and route tests, then exercise Studio's receipt display, auth denial, missing-backend, pending, and accepted-result paths. Record what was actually verified.

No step authorizes deploying, adding credentials, mutating production data, or weakening the current gate.

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
npm exec --workspace=apps/web --no -- vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/studio-workflow.test.ts src/lib/__tests__/auth-paths.test.ts
```

Then add checks for the approved implementation boundary; this command alone does not prove server-side authorization or a live deployment.

## Held work

- `asRecord` / claim changes unless this authorized cut specifically requires them.
- Extractor expansion, new storage, or a broader assembly/build system without Loop approval.
- Mission Workspace, Agent Factory / Slingshot, ExperienceOS, or a new FORGE product.
- Replaying old App Builder VM/PR receipts as current evidence, deleting synced external records, or promoting production as “cleanup.”

Use [GOAL.md](GOAL.md) only after the owned slice is confirmed. The later build-out sequence remains proposed in [MASTER_ROADMAP.md](MASTER_ROADMAP.md).
