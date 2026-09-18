# UVAI — evidence-based build-out roadmap

- **Reviewed:** 2026-09-13
- **Inspected baseline:** `f531f34d` on `main`
- **Authority:** [AGENTS.md](../AGENTS.md)
- **Execution boundary:** Origin G.A.T.E. only; later phases below are proposals, not authorization.

This replaces the June execution board and its stale environment assertions. The [June roadmap remains in Git history](https://github.com/groupthinking/EventRelay/blob/f531f34d/docs/MASTER_ROADMAP.md). This review changes documentation only: it does not promote, deploy, migrate storage, or reopen adjacent product cuts.

## Intended outcome

A user starts with a YouTube URL, inspects a source-grounded Video Pack, approves the intended output, and receives a reproducible artifact with verification evidence. A live claim requires the applicable G.A.T.E. decision and verified receipts, not merely generated files or a completed workflow status.

The existing workspace export is a useful evidence handoff. It must not be sold as proof that the application demonstrated in a video has been recreated.

## What the current source supports

| Capability | Inspected evidence | Limit / remaining work |
| --- | --- | --- |
| One public product and canonical workbench | [`app/page.tsx`](../apps/web/src/app/page.tsx), [`studio/page.tsx`](../apps/web/src/app/studio/page.tsx), [`auth-paths.ts`](../apps/web/src/lib/auth-paths.ts) | `/` enters `/studio`; retired dashboard skins are not a new product |
| Hashed Video Pack extraction and persistence | [`video-pack.ts`](../apps/web/src/lib/video-pack.ts), [`video-pack-extractor.ts`](../apps/web/src/lib/video-pack-extractor.ts), [`video-pack-store.ts`](../apps/web/src/lib/video-pack-store.ts) | Gemini 3.8 Flash via AI Gateway; production pack store remains Upstash REST; stored fields are not automatically verified observations |
| Deterministic App Builder workspace emit | [`emit-app-builder-sandbox.ts`](../apps/web/src/lib/emit-app-builder-sandbox.ts), [`sandbox/route.ts`](../apps/web/src/app/api/video/sandbox/route.ts) | Displays transcript, visual events, and SOP; strips architecture/code snippets at this boundary; does not execute or deploy the bundle |
| Prior two-video emit work | [`app-builder-sandbox-PLAN.md`](../apps/web/src/lib/app-builder-sandbox-PLAN.md) and emitter fixtures/tests | Preserve original fixtures and receipts; old VM smoke and PR status are not freshly reverified here |
| Same-run actions and deployment attempts | [`OneLoopStudio.tsx`](../apps/web/src/components/OneLoopStudio.tsx), [`studio-workflow.ts`](../apps/web/src/lib/studio-workflow.ts) | Backend/provider configuration and authenticated workflows need their own current operational evidence |
| Four-way gate and canonical receipt hash | [`gate-transition.ts`](../apps/web/src/lib/gate-transition.ts), [contract](gate-transition-contract.md) | Client-callable policy; current Studio adapter passes `anonymous` authority and derives its evidence verdict from URL validation; not independent provider/ownership verification |
| Get Pro and locked offers | Root policy; [`app/page.tsx`](../apps/web/src/app/page.tsx) | Workflow Pro $39/mo or $390/yr; Maintain $199/mo per live product; Ship per-job quote. No new checkout promises |

### Verification performed for this review

From the repository root:

```bash
npm exec --workspace=apps/web --no -- vitest run src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/emit-app-builder-sandbox.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/video-pack-store.test.ts src/app/api/video/sandbox/__tests__/route.test.ts
```

Result: **5 files passed; 81 tests passed, 1 skipped**. This is local regression evidence for these five suites only. It is not a full build, complete test run, authenticated browser check, fresh provider verification, or production end-to-end receipt. The Vite config-loader warning does not fail this command and is not a reason to change dependencies in a documentation cleanup.

## Remaining build-out, in dependency order

### 1. Origin G.A.T.E. — next authorized boundary

**Purpose:** close the gap between an outcome-display guard and independently trustworthy transition evidence without weakening the existing contract.

Before implementation, UVAI Loop confirms the exact owned slice and any parked live-URL work. Keep current PASS/HOLD/REJECT/ESCALATE semantics intact while specifying:

- Which server-side principal is allowed to request the consequential transition; a recognized actor string is not authentication or authorization.
- Which trusted receipt proves the artifact/run, provider result, target project, and permitted ownership. URL shape validation alone does not prove any of these.
- How a transition is bound to source/artifact identity, how retries avoid duplicate side effects, and how stale, replayed, mismatched, or missing evidence is handled.
- Who owns any receipt retention. G.A.T.E. itself stays a policy/receipt module, not a project database; do not turn the Video Pack store into a generic gate database by assumption.
- How the UI displays an unavailable backend, denied authority, incomplete run, and verified result without inventing a success message.

**Exit evidence:** scoped contract change; focused tests for all four decisions and hostile/missing evidence; route-level authorization tests for the approved boundary; a reproducible browser receipt for the approved user path. Do not claim independent deployment verification until it actually exists and has been exercised.

**Held:** unrelated `asRecord` / claim changes, Mission Workspace, Agent Factory, ExperienceOS, or reopening the extractor simply to broaden this cut. Details: [NEXT-PHASE.md](NEXT-PHASE.md).

### 2. Source-grounded build specification — requires Loop approval

**Purpose:** distinguish what the video shows from a proposed implementation before using a pack as builder input.

- Attach source references/timestamps to actionable requirements and label inferred choices explicitly.
- Represent unknown behavior, missing credentials, and unsupported capabilities as unresolved requirements, not invented architecture or code.
- Define user acceptance criteria and the supported output class before selecting implementation rails.
- Preserve the emitter's architecture/code-snippet stripping tests; expanding that boundary requires its own evidence and approval.

**Exit evidence:** a reviewed build-spec contract, positive and negative source-grounding fixtures, explicit unsupported cases, and no silent substitution of one video's content for another. Keep `auJzb1D-fag` as the default fixture and preserve the separately recorded emit fixtures.

### 3. Reproducible artifact assembly — requires Loop approval

**Purpose:** move beyond a pack viewer to a supported working artifact without free-form stack invention.

- First inventory existing generation/handoff code; reuse the valid path instead of adding a parallel builder.
- Resolve the approved spec against versioned, compatible implementation rails with declared inputs and outputs.
- Pin dependencies and emit a file/dependency manifest, source identity, and explicit configuration requirements.
- Keep secrets outside generated source and never mark an unsupported feature as implemented.

**Exit evidence:** the approved non-viewer behavior runs; two approved source cases remain distinct; the same locked inputs reproduce the same assembly manifest; no accidental source or credential leakage. A generated directory alone does not pass.

### 4. Isolated execution and repair — requires Loop approval

**Purpose:** turn artifact output into verifiable execution, not a claim based on generation.

- Run install, type-check, relevant tests, build, and browser acceptance inside a bounded disposable environment.
- Limit network/credential access, subprocess permissions, time, output size, and retry budget.
- Bind exit codes, logs, screenshots, artifact identity, and configuration references into receipts.
- Allow repair only from actual failing evidence; stop on unresolved failures instead of fabricating a green run.

**Exit evidence:** a clean-environment replay plus a deliberate failing case that remains held; auditable cleanup and bounded retries. No deployment claim at this stage.

### 5. Authorized shipping and operations — requires Loop approval

**Purpose:** connect a verified artifact to an authorized deployment and retain honest state through retries and failures.

- Reuse the intended deployment adapter and require explicit target/credential authority.
- Bind provider receipts to the verified artifact and run; reconcile failed, pending, rolled-back, and successful results.
- If reachability checks are approved, constrain them against SSRF and distinguish health from ownership and application correctness.
- Require the approved G.A.T.E. policy before a live-success claim; provide rollback and observable failure paths.

**Exit evidence:** an operator-authorized fresh deployment receipt, verification tied to the expected artifact, a rollback/failure exercise, and no live claim without the required evidence. No fabricated URL or stale smoke receipt qualifies.

### 6. Operational acceptance, then held product expansion

**Purpose:** make the approved loop supportable before expanding its product surface.

- Exercise anonymous, signed-in, quota, billing, provider-outage, and retry paths against the actual configured environment.
- Check ownership isolation, bounded costs, observability, and the repeat-run experience on the canonical Studio surface.
- Reconcile plans against merged code and deployment receipts; retire superseded guidance rather than duplicating it.

**Exit evidence:** fresh end-to-end results for the supported flow and explicit unresolved limits. Only a subsequent Loop decision may open Mission Workspace, Agent Factory / Slingshot, or ExperienceOS. FORGE / Workbench / Living Notebook / VIZUL remain UX patterns, not additional products.

## File-management decisions

- Update the root overview, host guides, repository map, goal, and next-phase entry points to agree with locked policy and current source.
- Replace copied `docs/AGENTS.md`, `docs/CLAUDE.md`, and `docs/GEMINI.md` bodies with pointers to the authoritative root guides.
- Mark old architecture/issue maps and completed App Builder plans as historical; preserve their evidence rather than treating them as today's queue.
- Remove only the unreferenced `_writetest.md` containing `# test`; retain substantive exports, fixtures, audit ledgers, and operational records.
- Leave runtime code, manifests, lockfiles, secrets, integrations, deployments, and remote data unchanged in this maintenance cut.

## Decision rule

Every implementation cut needs a bounded owner-approved scope, a failure case, a reproducible acceptance check, and a receipt that identifies what actually ran. A plan, source inspection, passing unit suite, successful build, and live deployment are different evidence levels; never collapse them into a single “done.”
