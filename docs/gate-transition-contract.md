# G.A.T.E. transition contract

Governed Acceptance & Transition Engine. Origin hardgate, not a second product, builder, or project database.

## Split (locked)

| Layer | Question / owner |
| --- | --- |
| **Zero-Sim** | Is the evidence real (`real`, `unverified`, `unreal`)? |
| **G.A.T.E.** | Do verified evidence and authority permit this exact transition? |
| **EventRelay** | Internal runtime and retained, versioned receipts. |

Plane stays **proposed** until config and actual receipts verify. SeeScriptShip lock is not install/run/deploy. An evidence workspace, export, completed workflow, or valid URL is not deployment proof.

## Authorized scope

Only `studio.deploy`, `proposed` → `live`, is implemented here. This cut verifies attestations and retains acceptance decisions. It does not build, run, deploy, roll back, or unlock another phase. Grounded specification and every subsequent roadmap phase still require separate UVAI Loop approval.

Authoritative modules:

- `apps/web/src/lib/origin-gate.ts`: strict input, independent signatures, binding, policy, signed receipts.
- `apps/web/src/lib/origin-gate-store.ts`: existing Upstash REST runtime adapter, atomic receipt/nonce/transition writes.
- `POST /api/gate/transitions`: authenticated acceptance boundary; `200` only for PASS, `409` for other gate decisions.
- `POST /api/workflows/studio-deploy`: authenticated **preflight only**. It cannot start the legacy video-to-job workflow, which would regenerate bytes rather than deploy an approved artifact. No receipt supplied to this route enables execution.

Both routes use the existing Studio owner/session check, same-origin mutation protection, bounded JSON reader, and `Cache-Control: no-store`. HTTP authentication/input failures may return `401`, `403`, `400`, `413`, or `415` before evaluation; unexpected boundary failures return `503`, never authorization.

## Decisions

| Decision | When |
| --- | --- |
| **PASS** | Session subject, exact artifact/run/transition/target binding, scoped Loop approval, independent verifier evidence with Zero-Sim `real`, fresh valid signatures, unchanged trusted policy, and atomic retention all verify. |
| **HOLD** | Required evidence is missing, unverified, stale, or the signing/retention runtime is unavailable. |
| **REJECT** | Evidence is unreal, a live claim has no signed verification receipt, signatures/bindings are mismatched, authority is denied/revoked/out of scope, a nonce or accepted transition is reused, or the request violates the strict contract. |
| **ESCALATE** | Authority, configured verification key, or signed verdict is unknown. |

Missing evidence is not invented. A registered role is not enough without its valid signature. Two different issuer names sharing one cryptographic key are not independent approval and verification. Issuer policy grants **project** scope; environment is bound by each signed target, with no separate issuer environment allowlist. Different ephemeral test keys prove cryptographic separation, not independent human ownership.

Precedence is executable behavior: session/input/signing checks come first; a live URL without evidence rejects before the general missing-evidence hold; policy and approval are checked before deployment evidence; signature/binding precede freshness, which precedes signed verdicts. For example, expired signed denial holds, and unknown approval escalates before unreal deployment evidence is examined.

## Request and attestations

The acceptance request contains:

- `transitionId`, `kind: "studio.deploy"`, `fromState: "proposed"`, `toState: "live"`.
- `runId`, lowercase SHA-256 `artifactHash`.
- `target: { provider: "vercel", projectId, environment: "preview" | "production", liveUrl }` with an HTTPS URL accepted unchanged by `studioVerifiedLiveUrl`. Leading/trailing whitespace is rejected. Binding compares exact signed URL bytes, not URL-parser equivalence; host case and trailing slashes are not canonicalized. The helper is syntactic, not DNS/provider verification, and does not itself exclude IP-host or userinfo URLs.
- `approval` and `evidence`, each `{ payload, signature }`.

Missing artifact fields may produce a HOLD. Unknown fields, including browser `authority` or `subject`, are rejected. The subject is derived from the verified server session.

Each payload has `version: "origin.attestation.v1"`, `type: "approval" | "deployment"`, `issuer`, `nonce`, ISO `issuedAt` / `expiresAt`, `binding`, and `verdict`. The exact binding repeats the transition, authenticated `subject`, run, artifact hash, and complete target. Deployment evidence additionally requires `providerReceiptId` and lowercase SHA-256 `providerReceiptHash`.

- Approval verdict: `allow` or `deny`; other values escalate.
- Deployment verdict: Zero-Sim `real`, `unverified`, or `unreal`; other values escalate.
- Both attestations expire within 15 minutes of issuance. Future issuance beyond 30 seconds and expired attestations HOLD.
- Signature: Ed25519, base64url, over the UTF-8 bytes of `origin.attestation.v1\n` followed by `canonicalGateJson(payload)` from `gate-transition.ts`.

The trusted external deployment verifier is responsible for inspecting the actual provider receipt and matching its artifact, target, and deployment. G.A.T.E. authenticates that signed attestation; **this implementation does not independently call Vercel or establish deployment health**. An unsigned caller-supplied provider receipt ID/hash is not sufficient.

## Trust configuration and activation

The runtime reads JSON from `er:gate:v2:trusted-policy` in the **existing Upstash REST** resource:

```typescript
{
  version: 1,
  issuers: Array<{
    id: string;
    role: 'loop' | 'deployment-verifier';
    publicKey: string; // Ed25519 SPKI PEM; public material only
    projectIds: string[];
    revoked: boolean;
  }>;
}
```

Only an authorized runtime administrator registers or revokes these keys with Loop approval. There is deliberately no public policy-write endpoint, auto-enrollment, generated production approval, or private issuer key in this app. Protect the existing runtime credentials: anyone who can replace the trust registry is inside this trust boundary.

Receipt authentication uses the existing server-only `NEXTAUTH_SECRET` (minimum 32 characters), domain-separated from session use. Retention uses `KV_REST_API_URL` / `KV_REST_API_TOKEN` or `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`. Redis TCP is not substituted. Missing credentials, unusable signing configuration, or runtime outage cannot PASS. No new integration or credential is implied by this contract.

Activation requires an authorized registry, independently managed issuer keys, actual artifact/provider evidence, and a real authenticated acceptance run. Tests generate ephemeral keys and fixtures only; they do not activate policy or prove deployment. Production keys/policy/data must not be mutated merely to demonstrate a green result.

## v2 receipts and retries

`eventrelay.gate-receipt.v2` includes the decision/reason, authenticated subject, transition, evidence references, run, artifact hash, target, policy hash, request hash, issue time, and `retained`. `receipt_hash` is the SHA-256 of its canonical body; `signature` is HMAC-SHA-256 over `origin.gate-receipt.v2\n{receipt_hash}`. This is runtime-authenticated evidence, not a portable public-key signature or a deploy bearer token.

The runtime owns `er:gate:v2:receipt:*`, `er:gate:v2:transition:*`, and `er:gate:v2:nonce:*`. It atomically compares the exact policy snapshot before PASS and reserves transition/nonce keys with the retained receipt. Identical valid retries return the original authenticated receipt; conflicting requests reject. Current policy and expiry are checked again on retry. Revocation cannot be bypassed by replaying a prior PASS. Altered stored receipts fail closed.

**PASS receipts and accepted transition/nonce replay markers have no automatic expiry.** Removing them removes replay protection. Non-PASS receipts and their per-subject pending index expire after **24 hours**, with at most **100 pending receipts per subject**; quota overflow yields an unretained `HOLD / GATE_HOLD_RETENTION_LIMIT`. Non-PASS requests are re-evaluated, not cached as permanent denials. Promotion to PASS atomically removes the pending entry and preserves the accepted record permanently. Redis time prunes quota entries; caller timestamps do not control retention. Legacy permanent non-PASS records receive the bounded TTL on re-evaluation.

G.A.T.E. remains a policy engine; these are internal runtime records, not a new project database. Storage failure returns `retained: false`; it never pretends a receipt was saved. A negative retry cannot overwrite a retained PASS. Signing-secret rotation invalidates prior receipt authentication and requires an owned operational procedure rather than implicit reacceptance.

## Studio and v1 compatibility

`gate-transition.ts` retains its client-safe v1 diagnostic contract and decision vocabulary. v1 content-addressed receipts are **not** authorization. The Studio URL adapter no longer upgrades a syntactically valid URL into Zero-Sim `real`; a valid raw live claim stays unverified/REJECT without authoritative evidence. This supersedes the earlier #1707 / #1710 URL-only bar without accepting any weaker URL.

Optional `deploymentHttpProbe` evidence (see `live-deployment-probe.ts`) records an HTTP reachability check. A successful probe adds `deployment_http_probe` with id `ok` and may yield PASS together with known authority; a failed probe HOLDs with `GATE_HOLD_DEPLOYMENT_UNREACHABLE`. This is not provider ownership verification (Origin attestations remain required for production PASS on `/api/gate/transitions`).

Studio displays server v2 decisions, transition IDs, and receipt-retention status distinctly from local diagnostics, retains existing auth redirects, clears receipts on selection changes, and ignores late responses for another selected video. A decision chip or completed workflow never starts deployment. Mission advance is not implemented.

## Executable contract map

Paths below are relative to `apps/web/src`. Gate cases are in `lib/__tests__/origin-gate.test.ts`; placeholders such as `%s` identify parameterized test names, not unexecuted examples.

| Requirement | Implementation | Named test / suite |
| --- | --- | --- |
| Exact signed acceptance, all four decisions | `lib/origin-gate.ts` | `PASSes independently signed, exact-bound approval and evidence and retains a signed receipt`; `honors the signed Loop %s verdict`; `preserves the signed Zero-Sim %s verdict` |
| Approval/evidence precedence, no invented evidence | `lib/origin-gate.ts` | `checks approval before evidence, and freshness before signed verdicts`; `HOLDs an evidence workspace with no artifact and never manufactures a live receipt` |
| Both signatures bind subject, transition, run, artifact, project, environment, URL | `lib/origin-gate.ts` | `approval contract matrix` and `deployment contract matrix`: `rejects a separately signed mismatched %s` |
| Project scope, revoked/wrong-role/unknown keys, duplicate IDs | `lib/origin-gate.ts` | Both matrices: `rejects a %s issuer`, `escalates an unknown issuer and an unusable registered key`; `escalates duplicate issuer IDs rather than selecting a preferred record` |
| Independent cryptographic keys | `lib/origin-gate.ts` | `REJECTs one cryptographic key impersonating both independent roles` |
| Exact URL bytes and environment binding, not extra policy | `lib/origin-gate.ts` | `rejects invalid or untrimmed target %s`; `requires exact signed URL bytes for %s, not URL-parser equivalence`; `binds production explicitly without inventing an issuer environment allowlist` |
| Provider references, signature tampering, expiry/skew/lifetime edges | `lib/origin-gate.ts` | `holds signed real evidence without %s`; both matrices: `rejects post-signature payload tampering and a valid signature over the wrong type`, `enforces %s` |
| Independent receipt SHA-256/HMAC check; corrupted storage fails closed | `lib/origin-gate.ts` | `independently authenticates all four decision receipts with Node crypto`; `fails closed on a retained receipt with altered %s` |
| Current policy, expiry and signing still apply to retries | `lib/origin-gate.ts`, `lib/origin-gate-store.ts` | `does not reaccept a retained PASS after signing-secret rotation or a policy read failure`; `does not replay a previous PASS after issuer revocation`; `does not replay a previous PASS after attestation expiry` |
| Atomic quotas/TTL, promotion, immutable PASS/replay records | `lib/origin-gate-store.ts` / `COMMIT_ORIGIN_GATE_SCRIPT` | `bounds %s receipt and quota-index retention to 24 hours`; `atomically caps one subject at 100 pending receipts, including concurrent requests`; `re-evaluates a future-dated HOLD and atomically promotes it to one permanent PASS`; `keeps accepted receipts immutable and replay markers permanent after a negative retry` |
| Storage time, policy race, existing transition, legacy retention | Same production Lua | `prunes expired quota members using storage time rather than caller time`; `cannot promote a held receipt if the policy changes before commit`; `does not promote a held request after another request accepts its transition`; `bounds a legacy permanent non-PASS receipt when it is next re-evaluated` |
| Real session verification and protected API responses | `app/api/gate/transitions/route.ts`, `lib/studio/security.ts` through evaluator/REST/Lua | `real route → NextAuth → evaluator → REST adapter → Lua`: `returns HTTP 200 only with the authentic retained record and permanent replay markers`, `returns HTTP 409 with a real retained %s`, `denies %s identity before any storage call`, `denies %s before evaluation` |
| Caller/session forgery, unavailable transport, concurrent retries/conflicts | Same isolated real-route suite | `rejects caller-supplied identity and signed evidence belonging to another session`; `never authorizes a transition when the REST transport is unavailable`; `returns one identical retained PASS for concurrent authenticated retries`; `allows only one conflicting authenticated acceptance for the same transition` |
| Legacy deployment never executes from an acceptance envelope | `app/api/workflows/studio-deploy/route.ts` | `does not execute the legacy deployment even with a valid envelope and retained PASS`; existing `app/api/workflows/studio-deploy/__tests__/route.test.ts` |
| v2 consumer preserves fields, rejects malformed/mismatched receipts, cannot infer execution | `lib/studio-workflow.ts` | `lib/__tests__/studio-workflow.test.ts`: `preserves an evaluator-issued %s receipt without claiming execution success`, `preserves an actual unretained runtime HOLD`, `does not display a %s as an authoritative server receipt` |
| All decision displays, local fallback, retention, selected-video isolation | `components/OneLoopStudio.tsx` | `components/__tests__/OneLoopStudio.gate.test.tsx`: `displays server %s without inventing deployment links or execution`, `labels a missing server receipt as a local diagnostic, never retained authorization`, `displays a server HOLD as runtime evidence, not a deployment`, `ignores a late receipt when another video is selected` |

The focused command also includes the existing v1 gate, pipeline-status, auth-paths, security and gate-route regression suites. The browser consumer checks shape/envelope consistency; it does **not** possess the server secret or independently verify HMAC.

## Reproducible verification

From repository root, using the declared npm 10.8.0 and a local `redis-server` or `redis6-server`:

```bash
npm --workspace=apps/web run test:gate -- --reporter=default --reporter=json --outputFile.json=/tmp/origin-gate-focused.json
```

`test:gate` enables `ORIGIN_GATE_REDIS_TESTS=1`. An absent Redis binary fails the suite; it never substitutes a hosted resource. The existing `test-frontend` CI job enables the same cases in its full web suite and uploads `$RUNNER_TEMP/web-vitest-report.json` as `web-vitest-${{ github.sha }}` for seven days, including failed runs. This describes configured CI behavior, **not an observed remote run or an available artifact URL**.

### Evidence record — 2026-09-13

- **Tested source:** uncommitted worktree over `5495e31851c2f32910d6e4bbf0c942846168055f`. Implementation/test/CI diff identifier: `03fe0c6bd629c304c66f90ab4b260ad7bda4b977`, computed with `git diff -- apps/web .github/workflows/ci.yml | git hash-object --stdin`; excludes this documentation. No committed revision is implied by these local runs.
- **Runtime:** Node `24.16.0`, Vitest `4.1.10`, Redis `6.2.20`. Verification was also run through `npx --yes npm@10.8.0` to match the manifest; the sandbox default npm is `11.13.0`. CI declares Node 22; remote CI/that runtime was not exercised here.
- **Focused command above:** **326 passed, 0 failed, 0 skipped, 9 files**. All **26** isolated Redis cases executed, including **16** complete real-route cases. Machine-readable report: `/tmp/origin-gate-focused.json`.
- **Full web regression:** `ORIGIN_GATE_REDIS_TESTS=1 npm --workspace=apps/web test -- --reporter=default --reporter=json --outputFile.json=/tmp/origin-gate-web-full.json` — **1,169 passed, 0 failed, 1 skipped, 119 files**. The unrelated opt-in skip is `video-pack store Redis integration executes the atomic claim script against Redis`; no required gate case skipped.
- **Static/config checks:** web `type-check`, targeted ESLint for all four edited TypeScript files, `git diff --check`, and CI YAML parsing/reporting assertions passed. `npm ci --dry-run --ignore-scripts --legacy-peer-deps --no-audit --no-fund` passed under npm 10.8.0 without changing manifests/lockfile; this is a lock-consistency check, not a fresh dependency installation. No dependency versions or consistency policies changed.
- **Prerequisite negative check:** with Redis binaries excluded from `PATH`, the gate file failed with `ORIGIN_GATE_REDIS_TESTS requires redis-server or redis6-server; no external store is used.` Its 26 Redis cases could not execute; this expected failure is separate from the passing proof. Report: `/tmp/origin-gate-missing-redis.json`.
- **Reproduced defect:** the consumer previously displayed envelope `reason` / `reason_code` that disagreed with the retained receipt. Both mismatch tests failed against that behavior; a one-line consistency guard makes them pass. Report of the expected failures: `/tmp/origin-gate-consumer-red.json`. No evaluator, authority, storage or execution behavior changed.
- **Browser smoke only:** local `/studio`, 700 × 674, dark mode, rendered the disabled preflight action and explicit deployment-unavailable text. Screenshot: `/tmp/agent-browser/origin-gate-proof-final.png`. No authenticated browser submission or deployment was performed. All local reports/screenshots remain outside git.

### Three separate conclusions

1. **Software contract verified for the named cases:** fail-closed decisions, exact bindings, signatures, receipts, retries/retention, and Studio consumer/display behavior have fresh passing checks. This cut primarily adds proof/coverage and the reproduced consumer fix, not a replacement gate.
2. **Isolated integration verified:** real route handlers, NextAuth decoding, shared security, evaluator, production REST adapter and actual Lua execute together. Only external transport is replaced by a GET/EVAL bridge to test-owned Unix-socket Redis; TCP and persistence are disabled, relevant env values are stubbed/restored, and ephemeral issuer/session keys are never exported. Deployment kickoff is spied and never called; DNS is isolated. This does not test hosted Upstash, deployed Next routing, independent operational key owners, or Vercel provider execution/health.
3. **Production authorization/acceptance not established:** no real authority enrollment, connected-store submissions, provider evidence, deployment, operational PASS, platform-wide gating, or next-phase authorization was attempted. Those are deliberately outside the approved software-proof cut, not prerequisites for reproducing its tests. Authenticated browser acceptance and remote CI remain unperformed.

### Historical observations — not current blockers

An earlier cut on 2026-09-13 recorded 178 passing tests and a 758 × 752 Studio render, plus `403 invalid_origin`, `503 authentication_unavailable`, and missing recognized sandbox REST credentials. Those observations were not revalidated as current failures here and are not evidence of a production outage or prerequisites for this isolated verification.
