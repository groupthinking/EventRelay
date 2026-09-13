# Next phase — Origin G.A.T.E.

- **Reviewed:** 2026-09-13
- **Authority:** [../AGENTS.md](../AGENTS.md)
- **Plan:** [MASTER_ROADMAP.md](MASTER_ROADMAP.md)

The former P3 “Act on the same run” document described an earlier cut. Same-run actions already exist in `OneLoopStudio`; do not restart that work or use its historical `/` routing as current guidance. `/studio` is the canonical workbench.

## Next owned slice

Origin G.A.T.E. is the only cut authorized by root policy. The requested implementation now covers the `studio.deploy` proposed-to-live acceptance boundary: session-derived identity, scoped independent Ed25519 attestations, exact artifact/run/target binding, signed retained receipts, and atomic replay protection. See the [current contract](gate-transition-contract.md).

**Goal:** make the approved consequential transition depend on trustworthy evidence and authority, without changing the fail-closed decision vocabulary or creating a second product.

Studio distinguishes authoritative server decisions from local diagnostics. A valid HTTPS hostname is no longer upgraded into verified deployment evidence. The legacy deployment kickoff is held because regenerating from a video cannot guarantee the approved artifact bytes.

**Operational acceptance remains pending.** An authorized runtime owner must register real Loop/verifier public keys and supply fresh, actual artifact/provider evidence for an authenticated acceptance run. No production registry, issuer keys, deployment, or later-phase approval is created by the tests or this document. The gate verifies external verifier attestations; provider execution/health verification is not implemented by this cut.

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
npm exec --workspace=apps/web --no -- vitest run src/lib/__tests__/origin-gate.test.ts src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/studio-workflow.test.ts src/lib/__tests__/auth-paths.test.ts src/app/api/gate/transitions/__tests__/route.test.ts src/app/api/workflows/studio-deploy/__tests__/route.test.ts src/components/__tests__/OneLoopStudio.gate.test.tsx
```

Then add checks for the approved implementation boundary; this command alone does not prove server-side authorization or a live deployment.

## Held work

- `asRecord` / claim changes unless this authorized cut specifically requires them.
- Extractor expansion, new storage, or a broader assembly/build system without Loop approval.
- Mission Workspace, Agent Factory / Slingshot, ExperienceOS, or a new FORGE product.
- Replaying old App Builder VM/PR receipts as current evidence, deleting synced external records, or promoting production as “cleanup.”

Use [GOAL.md](GOAL.md) only after the owned slice is confirmed. The later build-out sequence remains proposed in [MASTER_ROADMAP.md](MASTER_ROADMAP.md).
