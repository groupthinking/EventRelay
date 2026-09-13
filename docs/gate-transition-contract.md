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

Both routes use the existing Studio owner/session check, same-origin mutation protection, bounded JSON reader, and `Cache-Control: no-store`. HTTP authentication/input failures may return `401`, `403`, `400`, or `413` before evaluation; unexpected boundary failures return `503`, never authorization.

## Decisions

| Decision | When |
| --- | --- |
| **PASS** | Session subject, exact artifact/run/transition/target binding, scoped Loop approval, independent verifier evidence with Zero-Sim `real`, fresh valid signatures, unchanged trusted policy, and atomic retention all verify. |
| **HOLD** | Required evidence is missing, unverified, stale, or the signing/retention runtime is unavailable. |
| **REJECT** | Evidence is unreal, a live claim has no signed verification receipt, signatures/bindings are mismatched, authority is denied/revoked/out of scope, a nonce or accepted transition is reused, or the request violates the strict contract. |
| **ESCALATE** | Authority, configured verification key, or signed verdict is unknown. |

Missing evidence is not invented. A registered role is not enough without its valid signature. Two different issuer names sharing one cryptographic key are not independent approval and verification.

## Request and attestations

The acceptance request contains:

- `transitionId`, `kind: "studio.deploy"`, `fromState: "proposed"`, `toState: "live"`.
- `runId`, lowercase SHA-256 `artifactHash`.
- `target: { provider: "vercel", projectId, environment: "preview" | "production", liveUrl }` with a normalized, validated HTTPS hostname URL.
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

Records have no automatic expiry: removing nonce/transition keys removes replay protection. Retention lifecycle changes need explicit ownership and approval. G.A.T.E. remains a policy engine; these are internal runtime records, not a new project database. Storage failure returns `retained: false`; it never pretends a receipt was saved. Signing-secret rotation invalidates prior receipt authentication and requires an owned operational procedure rather than implicit reacceptance.

## Studio and v1 compatibility

`gate-transition.ts` retains its client-safe v1 diagnostic contract and decision vocabulary. v1 content-addressed receipts are **not** authorization. The Studio URL adapter no longer upgrades a syntactically valid URL into Zero-Sim `real`; a valid raw live claim stays unverified/REJECT without authoritative evidence. This supersedes the earlier #1707 / #1710 URL-only bar without accepting any weaker URL.

Studio displays server v2 decisions, transition IDs, and receipt-retention status distinctly from local diagnostics, retains existing auth redirects, clears receipts on selection changes, and ignores late responses for another selected video. A decision chip or completed workflow never starts deployment. Mission advance is not implemented.

## Verification

From repository root:

```bash
npm exec --workspace=apps/web --no -- vitest run src/lib/__tests__/origin-gate.test.ts src/lib/__tests__/gate-transition.test.ts src/lib/__tests__/studio-workflow.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/auth-paths.test.ts src/app/api/gate/transitions/__tests__/route.test.ts src/app/api/workflows/studio-deploy/__tests__/route.test.ts src/components/__tests__/OneLoopStudio.gate.test.tsx
npm run type-check --workspace=apps/web
```

Coverage includes signed acceptance, missing/weak/unreal/unknown evidence, binding/signature tampering, scope/revocation, expiry, independent keys, retries/concurrency, altered receipts, runtime failure, protected API boundaries, no workflow kickoff, and selected-video receipt isolation. Browser acceptance and a real configured-runtime PASS are distinct checks; local fixtures cannot replace either.

Sandbox verification on 2026-09-13: the focused suite plus `src/lib/studio/__tests__/security.test.ts` passed **178 tests across 9 files**, and the web type-check passed. `/studio` rendered at 758 × 752 in dark mode. Full authenticated browser acceptance remains blocked: browser submissions returned `403 invalid_origin`, and a direct same-origin local submission returned `503 authentication_unavailable`. The existing Upstash integration reports connected, but the sandbox-injected environment did not expose a recognized REST credential pair on repeated checks. These are sandbox observations, not evidence of a production outage. No production configuration was changed and no operational PASS or next-phase authorization is claimed.
