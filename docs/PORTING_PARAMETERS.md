# Porting Parameters — EventRelay Clean Spine

> Status: governing document for the re-grow effort.
> Source of authority: the product's success criteria, **not** the current
> implementation. The existing repo is treated as evidence, not as truth.

## Default rule: presumed residue

**Everything in the repository is presumed *residue* until it is traced to one
of the seven success criteria below.** Residue is not ported. The burden of
proof is on *keeping* a thing, never on deleting it.

A module, table, service, route, package, or config graduates from residue to
*core* only when someone can write, in one sentence, the success criterion it
serves and the acceptance test that fails without it. If that sentence cannot
be written, it stays out of the clean spine.

This inverts the repo's current default ("it's here, so it must matter"), which
is how three MCP implementations, five model seams, four datastores, and six
deploy targets accumulated.

---

## The seven success criteria (mockup-independent)

These describe what the product **must accomplish**, divorced from how the
current repo happens to implement it.

| ID  | Success criterion | One-line definition |
|-----|-------------------|---------------------|
| SC1 | **Input ingest & validation** | Accept a YouTube URL; deterministically accept valid input and reject unsupported/invalid input. |
| SC2 | **Faithful transcript acquisition** | Obtain a word-for-word transcript, with a defined fallback (STT) when captions are absent. |
| SC3 | **Typed event extraction** | Produce schema-validated events named `<domain>.<entity>.<action>`. |
| SC4 | **Derived artifacts** | From transcript + events, produce summary, actionable tasks, and insights. |
| SC5 | **Single versioned API contract** | Expose all of the above through one OpenAPI contract that generates the client SDKs. |
| SC6 | **Durable, idempotent, observable jobs** | A job has a status lifecycle, survives process restarts, and `same URL → same result` (replayable). |
| SC7 | **Thin client UI** | A frontend that is a *pure consumer* of the contract and holds no business logic. |

If a capability is not on this list, it is not a requirement. (Notably absent
and therefore out of scope by default: multi-tenancy, RLS, audit/billing
tables, agent meshes, MCP coordinators, browser automation, ML model serving,
load balancing, horizontal-scaling services.)

---

## The salvageable spine

Four existing assets are pre-cleared as core because each maps directly to a
criterion and is already healthy:

1. **The OpenAPI contract** (`openapi/eventrelay.openapi.json`) + Stainless SDK
   generation (`.stainless.yml`, `sdk/`) → **SC5**.
2. **The Next.js frontend** (`apps/web`) → **SC7** — *but only after* its
   server-side `/api/*` business logic and direct-Gemini fallback are removed;
   it must call the backend exclusively through the generated SDK.
3. **The DI container pattern** (`backend/containers/service_container.py`) →
   cross-cutting; the one structural pattern worth keeping verbatim.
4. **The event taxonomy** (`<domain>.<entity>.<action>`) → **SC3** — the domain
   model, not the 10 SQLAlchemy tables built around it.

Everything else must earn its place per the table below.

---

## Per-criterion porting parameters

For each criterion: the capability it demands, the **single** existing asset
that may be ported (if any), the acceptance test that proves it, and what this
criterion explicitly does **not** justify.

### SC1 — Input ingest & validation

- **Capability:** URL parse + validation; canonical video-id extraction.
- **Port candidate:** the validation logic only (Pydantic request models in
  `backend/api/v1/models.py`). Port the *shape*, not the surrounding router.
- **Acceptance test:** valid URL → 202 + job id; malformed/unsupported URL →
  422 with a typed error, no side effects.
- **Does NOT justify:** any persistence, any provider call.

### SC2 — Faithful transcript acquisition

- **Capability:** caption fetch; STT fallback when captions absent.
- **Port candidate:** one transcript path. Choose **one** of the existing
  transcript implementations and delete the rest. STT fallback as a pure
  function behind the same interface.
- **Acceptance test:** captioned video → exact transcript; caption-less video →
  STT transcript; both return identical schema.
- **Does NOT justify:** the 7 `VideoProcessor` variants, `yt-dlp` media
  pipelines beyond what STT needs, NotebookLM browser automation.

### SC3 — Typed event extraction

- **Capability:** transcript → list of schema-validated `<domain>.<entity>.<action>` events.
- **Port candidate:** the **event taxonomy** + the event Pydantic schema. The
  extraction step is a pure function: `(transcript) -> list[Event]`.
- **Acceptance test:** golden transcript → expected event set; every event
  validates against the schema; names match the taxonomy regex.
- **Does NOT justify:** the agent frameworks (`src/agents`,
  `services/agents`), the three MCP implementations, A2A messaging.

### SC4 — Derived artifacts

- **Capability:** summary + tasks + insights from transcript/events.
- **Port candidate:** the *prompt content* from the three Gemini agents
  (transcript_action / personality / strategy) — as data, not as the agent
  orchestration classes. Each derivation is a pure function over the transcript.
- **Acceptance test:** golden transcript → non-empty summary, ≥1 typed task,
  insights object validating against schema.
- **Does NOT justify:** `skill_builder`, `video_subagent`, `video-to-software`,
  `code_generator`, the orchestrator/ and workflows/ layers.

### SC5 — Single versioned API contract

- **Capability:** one OpenAPI spec is the source of truth; SDKs are generated.
- **Port candidate:** `openapi/eventrelay.openapi.json` + `.stainless.yml` +
  `sdk/` (generated, do not hand-edit).
- **Acceptance test:** spec lints; SDKs regenerate clean; a contract test hits a
  running server and validates every response against the schema.
- **Does NOT justify:** the second backend living in `apps/web/src/app/api/*`,
  the `main_v2.py` shims, multiple `FastAPI()` instances.

### SC6 — Durable, idempotent, observable jobs

- **Capability:** one durable store of jobs + events with a status lifecycle and
  replay-by-key (URL + pipeline version).
- **Port candidate:** **one** persistence choice (TBD — see open decisions).
  The DI container to inject it. Nothing else.
- **Acceptance test:** submit job → poll status to completion; restart process
  mid-flight → job still resolvable; resubmit same URL → identical result
  without recomputation.
- **Does NOT justify:** in-memory `_video_jobs`/`_agent_executions` dicts, four
  parallel datastores (Prisma + SQLAlchemy + Firebase Data Connect + Supabase),
  multi-tenant/RLS/audit/soft-delete mixins, the load-balancer and
  horizontal-scaling services.

### SC7 — Thin client UI

- **Capability:** UI that submits a URL, streams/polls job status, renders
  transcript/events/artifacts — via the generated SDK only.
- **Port candidate:** `apps/web` pages + components (dashboard, TranscriptViewer,
  EventList, AgentDashboard) — **minus** all `apps/web/src/app/api/*` route
  handlers and the Gemini fallback in `lib/`.
- **Acceptance test:** with the backend down, the UI shows an error state and
  makes **no** direct model calls; with it up, every data path goes through the
  SDK.
- **Does NOT justify:** Zustand stores that duplicate backend job state beyond
  view state, client-side event extraction.

---

## Residue ledger (presumed-delete unless promoted)

Catalogued during the architecture review. Each item stays out of the spine
until traced to a criterion above.

| Item | Why presumed residue | Promote only if |
|------|----------------------|-----------------|
| `src/utils/notebooklm_profile*/` | Committed browser credentials; maps to no SC | never — security removal, not a feature |
| `src/utils/notebooklm_ingest.py` | NotebookLM browser-automation phase | a criterion requires NotebookLM export (none does) |
| `src/unified_ai_sdk/` | Returns placeholder strings | never — superseded |
| `src/uvai/` | Parallel ML-platform project | an SC needs served ML models (none does) |
| `src/agents/`, `services/agents/` (+ adapters) | Two agent frameworks; SC3/SC4 are pure functions | a criterion needs multi-step autonomy |
| `src/mcp`, `youtube_extension/mcp`, `services/mcp` | Three MCP impls | an SC needs MCP tool execution |
| `src/core`, `src/integration`, `src/backend` (shims) | `importlib`/`main_v2` bridges | never — indirection only |
| `backend/models/*` (10 tables) beyond Job + Event | Platform tax for SC6 | a multi-tenant/billing SC is added |
| Prisma / Firebase Data Connect / Supabase stores | Competing with the one chosen store | the chosen store is one of these |
| `load_balancer`, `horizontal_scaling_system` | Speculative scale | measured load demands it |
| `coverage.json`, `tsbuildinfo`, `*.old`, root `test_*.py`, `debug_gemini.py`, `"…"`-named files | Build/scratch artifacts | never |
| 5 of 6 deploy targets | Deployment indecision | one is chosen; rest deleted |

---

## Promotion process (residue → core)

1. Name the success criterion (SC1–SC7) the item serves.
2. Write the acceptance test that fails without it.
3. Confirm no already-cleared spine asset covers it.
4. Only then port it — porting the smallest unit that passes the test, not the
   surrounding module.

If steps 1–3 cannot be satisfied, the item is deleted, not parked.

---

## Open decisions (block scaffolding; tracked separately)

- **Persistence choice for SC6** — one store, to be selected.
  - Owner: TBD
  - Target date: TBD
  - Decision artifact: TBD
- **Single deployment target** — one of the current six, to be selected.
  - Owner: TBD
  - Target date: TBD
  - Decision artifact: TBD
- **This-phase build scope** — scaffold skeleton vs. spec/README only vs. full
  pipeline migration.
  - Owner: TBD
  - Target date: TBD
  - Decision artifact: TBD

These are recorded here so the spine is not grown against an unmade decision.
