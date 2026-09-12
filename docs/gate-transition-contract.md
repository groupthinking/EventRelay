# G.A.T.E. transition contract

Governed Acceptance & Transition Engine. This is the Origin hardgate in-repo — not a second product, not a project database, and not a builder.

## Split (locked)

| Layer | Question |
| --- | --- |
| **Zero-Sim** | Is the evidence real? |
| **G.A.T.E.** | Do verified evidence + authority permit this state transition? |
| **EventRelay** | Durable runtime / receipts (versioned, hashable, citable). |

G.A.T.E. does **not** build the artifact. It does **not** become Mission Workspace or the Outcome Graph. Flywheel center stays Mission Workspace + Outcome Graph + acceptance; EventRelay + Zero-Sim/G.A.T.E. are continuous, not post-build only.

Plane = **proposed** until config + receipts are verified. SeeScriptShip lock ≠ install / run / deploy.

## Decisions

Every consequential state transition resolves to exactly one of:

| Decision | When |
| --- | --- |
| **PASS** | Zero-Sim `real`, authority actor is known (`anonymous` \| `signed-in` \| `system`), and required evidence for the claimed `from→to` is present and verified. |
| **HOLD** | Required evidence is **missing**, or evidence is present but **weak / unverified**. The plane stays proposed. Caller may retry with a real receipt. |
| **REJECT** | Zero-Sim `unreal`, or the caller **claims** `to=live` with a live URL that fails the verified-receipt bar (https + hostname). |
| **ESCALATE** | Authority actor is unknown, or a supplied Zero-Sim verdict is not `real` \| `unverified` \| `unreal`. G.A.T.E. will not invent a decision. |

### Missing vs weak (documented)

- **Missing** (`GATE_HOLD_MISSING_EVIDENCE`): no required receipt. For `studio.deploy`, the required receipt is a verified live URL — a workflow `completed` status or run id is not enough.
- **Weak** (`GATE_HOLD_WEAK_EVIDENCE`): refs exist but Zero-Sim is `unverified`. G.A.T.E. does not upgrade that to `real`.
- **Unreal** (`GATE_REJECT_UNREAL_EVIDENCE`): Zero-Sim says the evidence is not real (malformed hash, invented/unparseable live URL treated as a live claim).

G.A.T.E. never invents evidence. If a fact is not in the request, it HOLDs or REJECTs; it does not fetch, simulate, or stub a receipt.

## Contract

Module: `apps/web/src/lib/gate-transition.ts`

```
evaluateTransition({
  transitionId, kind, fromState, toState,
  evidenceRefs,   // hashes / ids / uris — only what the caller has
  authority,      // { actor, claim? }
  zeroSim?,       // supplied result, or assessed fail-closed from refs
}) → { decision, reason, reason_code, receipt }
```

Receipt (`eventrelay.gate-receipt.v1`) is EventRelay-shaped: versioned, canonical-JSON SHA-256 (`receipt_hash`), id `er:gate:v1:{transitionId}`. Suitable to store or cite later. This module does not persist it (Upstash remains the Video Pack store only).

Zero-Sim assessment (when the caller does not supply a verdict):

- empty refs → `unverified` / `ZERO_SIM_MISSING_EVIDENCE`
- malformed SHA-256 or a presented `live_url` that fails https+hostname → `unreal`
- otherwise → `unverified` (format-valid refs are **not** upgraded to `real`)

The Studio adapter may assert Zero-Sim `real` only after `studioVerifiedLiveUrl` succeeds. That bar is locked by #1707 / #1710 — it is not a network probe that the deploy exists.

## Gated transition (PR1)

**`studio.deploy`**: `proposed` → `live` on the OneLoopStudio Deploy attempt.

- Anonymous Deploy remains an **attempt** (button: Attempt deploy). Enabled ≠ receipt.
- G.A.T.E. runs on every Attempt deploy that is not an auth redirect — including when `startStudioDeploy` fails (e.g. `BACKEND_URL is not configured`) — and **before** `studioDeployOutcomeMessage`.
- Studio **must** render a visible decision chip (`data-testid="studio-gate-receipt"`): **PASS | HOLD | REJECT | ESCALATE**, the short reason, and `receipt.id` / `receipt_hash` (`eventrelay.gate-receipt.v1`). Missing backend config is **HOLD** (`GATE_HOLD_MISSING_EVIDENCE`) plus the backend reason — not a silent/no-chip failure.
- **PASS** only with a verified `https://` live URL that has a hostname.
- Workflow `completed` without that URL → **HOLD**. Copy must not say “Deploy completed”.
- Presented live URL that fails the hostname bar → **REJECT**.
- Unknown authority actor → **ESCALATE**.

Mission advance is not implemented in this repo; do not invent a Mission Workspace gate here.

## Tests

```bash
cd apps/web && npx vitest run src/lib/__tests__/gate-transition.test.ts
```
