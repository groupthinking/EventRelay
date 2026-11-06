# Durable workflow task implementation — 2026-10-27

Baseline: main `e93fd0e975cda0f3a59cb7fa812c19c64f6b2a52`.
Authorization: Hayden requested action on the Oct 23 UVAI status report's recommended durable-task next step. This is a bounded implementation cut, not authorization to merge or change production.

## Before and after

`create_workflow_task` previously returned “Created task” with an in-memory object. It now requires a server-verified NextAuth provider/subject identity and a run ID, validates task inputs, writes through the existing Upstash REST credentials, and reads the persisted record before reporting fulfillment. It never falls back to memory. Storage errors return a failed action with no receipt.

The task key is SHA-256 scoped to identity, run ID, and the fixed-order validated task fields. Atomic SET NX makes concurrent retries return the original task/creation time. Records do not expire. Task reads use the server-verified owner namespace, not client owner input. `GET /api/agents/actions?taskId=<receipt-id>` retrieves the same user's task. Receipt data survives action-agent serialization; the summary also includes its ID. Anonymous task writes now return 401 and missing run IDs return 400. Preview remains side-effect free.

## Verification

Commands executed locally with Node v24.22.1, npm 11.9.0 and installed Vitest 4.1.11:

- Focused five-file suite: **42 passed, 0 failed, 0 skipped**. Files: workflow-task-store, action-tools, action-agent-routing, actions-route, action-agent-store.
- Full web suite: **1,530 passed, 28 skipped, 171 files passed**, 31.05 seconds. This preceded the final provider/subject namespace tightening; the focused suite was rerun after that change and again passed all 42 tests.
- `npm --prefix apps/web run type-check`: passed after the final code change.
- Targeted ESLint for changed TypeScript files: passed; final identity files rechecked.
- `git diff --check`: passed.

The isolated REST fixture verifies 1 initial write + 3 concurrent retries produce 1 record and identical receipts. It also verifies owner isolation, run isolation, invalid-input rejection, signed-session verification, failure status, required readback, and receipt propagation. This fixture is not proof of live Upstash quality or restart durability.

## Remaining acceptance work

This is implementation evidence, not live video-to-action acceptance. No hosted store or paid AI provider was called by these tests. Successful real end-to-end runs: **not measured**. Cost/run and live latency: **unavailable**. No merge or production deployment was performed as part of implementation.

The current reviewed-action transport supplies a run ID but not verified source timestamps or transcript/content hashes. Tasks therefore do not claim verified source provenance. `commitSha` records VERCEL_GIT_COMMIT_SHA when available, otherwise null. Source provenance, actual provider usage/cost, fresh-process hosted readback and authenticated UI acceptance remain required for the report's complete acceptance test. No scheduler, resource bookmark persistence or hosted execution adapter was added.

Next acceptance exercise (requires an authorized non-production runtime/store and permitted source video): preview causes 0 task writes; confirm creates 1 task; three identical retries return the same ID with 1 record; a fresh authenticated process reads it; another owner cannot; a forced storage outage never yields fulfilled. Retain exact source URL, timestamps/content hash, run ID, build SHA and actual usage/cost or explicitly unknown values. Do not mark complete until those receipts exist.

Related PR #2470 adds a local review-only journal and expressly excludes live action execution. This cut does not duplicate that journal. The two PRs touch the action route and will need integration review before either is merged.

## Task-write request boundary

Executing a batch containing `create_workflow_task` requires `application/json` and a serialized same-origin `Origin` header. Cross-site fetch metadata is rejected even when Origin matches. Same-site sibling domains, `null` or absent browser origins, and forwarded host headers do not establish mutation authority. A rejected request runs none of the actions in a mixed batch.

Non-browser clients may omit Origin only when they send an explicit Bearer token and no Cookie header. The token must still pass the existing provider/subject session verification. Merely adding an Authorization header cannot exempt cookie-based requests. This narrow guard does not change preview, task reads, or execution batches without workflow tasks. Development proxy origins are not implicitly trusted.

The origin regression suite uses real signed test sessions, the real route/executor/task-store code, and an isolated REST fixture. It verifies that a sibling-origin text/plain form writes no record, same-origin confirmation and retry return one receipt, and verified bearer-only clients remain supported. The origin guard is separate from the preview binding below and does not address the remaining storage review findings.

## Server-verifiable task previews

Authenticated previews containing workflow tasks now return `jobId` (a server-issued `preview_<UUID>`) and `confirmationToken`. To confirm, send `mode: "execute"`, the returned `jobId` and `confirmationToken`, and the reviewed actions. Old clients sending only an arbitrary run ID and actions now fail closed with 409. Anonymous preview is still read-only and has no executable receipt. The earlier client-supplied preview job ID is a correlation hint, not task-write authority.

The receipt is a domain-separated HMAC proof of a server-created preview, binding the authenticated provider/subject owner, server run ID, and the entire ordered `{tool,input}` plan. Object key order is canonicalized; action and array order are retained. Display-only summaries are not execution authority. Plans must be pending and error-free, and receipt-shaped data is rejected. Invalid signatures, changed owners/runs/actions, malformed plans, duplicate actions, and missing signing configuration cannot authorize writes. Normal execution-time input and entitlement validation still apply.

The proof has no expiry because it records immutable preview issuance rather than granting login or one-time approval. Every execution still requires current authenticated ownership and the task-write request boundary. Keeping the original proof/run ID preserves delayed and concurrent task retries without creating a second identity. Do not automatically re-preview after an uncertain write or verification failure: a new preview is a new run. Rotating NEXTAUTH_SECRET invalidates earlier proofs, while existing task records remain readable through owner-scoped GET.

Limits: the proof is not verified source-video provenance, evidence that a human viewed the UI, or a one-time execution lock. Task records are idempotent; other actions in a mixed batch may repeat on retries. Receipt versioning must be reviewed if tool execution semantics change. When integrated with #2470, local review-only mode must not issue executable task receipts and must continue refusing execute requests before this hosted-task path.

## Storage transport protection

Task storage accepts only valid HTTPS endpoints without URL userinfo. Unsafe or malformed configuration fails with the generic storage-unavailable error before any bearer credential or command data reaches fetch. Every command uses `redirect: "error"`, including the atomic write script, mandatory readback and owner-scoped GET. No hostname allowlist or changes to the shared credential resolver are introduced; both supported environment-variable families retain the same HTTPS transport policy.

Regression tests use native fetch with an isolated MockAgent dispatcher and real networking disabled. Before the fix, 307/308 redirects forwarded the POST task body across origins (native fetch strips cross-origin Authorization). Afterward, 301/302/303/307/308, same-origin redirects and HTTPS-to-HTTP redirects fail without contacting the target. HTTP configuration could separately transmit the bearer token and task data in plaintext and is now rejected before transport.

## Batch behavior during a task-store outage

The confirmed-action executor stops attempting additional workflow tasks after the first storage/configuration/protocol/readback failure. Each remaining task is returned as failed with an explicit "not attempted" summary and no receipt. Earlier verified task receipts are preserved. Other tool types continue in their original order, and ordinary invalid task inputs do not trip the storage-failure guard.

The guard is local to one execution call. A later explicit retry of the original confirmed plan attempts storage again and reuses the same task IDs, including a SET that may have succeeded before its readback failed. Nothing is retried automatically, and "not confirmed saved" is not a claim that an uncertain write did not happen.

This prevents one dead store from costing fifty consecutive ten-second task timeouts: a first atomic-write timeout now incurs one ten-second wait. The follow-up patch adds a 25-second cumulative task-storage deadline across atomic writes and mandatory readbacks; it is still not a deadline for unrelated non-task tools; a slow successful atomic write followed by a readback timeout can consume approximately twenty seconds, and earlier successful tasks or non-task tools can add latency.


## Owner capacity and initialization contract

New task IDs require an explicit `WORKFLOW_TASKS_PER_OWNER_LIMIT`, a canonical positive integer no greater than JavaScript's safe-integer maximum. There is no default or unlimited mode. This is an operator-selected limit, not a new product entitlement or pricing tier.

For each verified owner, `er:workflow-task-quota:v1:<SHA-256(owner)>` must be a permanent Redis string containing `v1:<count>`. Count is a canonical nonnegative safe integer. The owner value is the same JSON provider/subject identity used by the task store, not a client-supplied identity. Missing, malformed, unsupported-version, expiring or wrong-type metadata fails closed without repairing it. New owners also require trusted initialization; absence is not proof of zero existing records.

**Availability impact:** deploying this gate without the limit and initialized owner counts blocks all new task creation. Existing owner-scoped reads and retries of existing task IDs continue before quota checks, even when metadata or the limit is missing, invalid, full or lowered. No task is evicted, expired or rewritten to make room. Capacity rejection returns a failed action without a receipt and does not trip the storage-outage guard, so existing retries later in the same batch still run.

The atomic EVAL command checks the task ID, validates metadata, reserves one owner slot, then writes the new record with SET NX. Concurrent new IDs cannot exceed initialized capacity, and concurrent identical retries do not consume extra slots. Mandatory readback remains separate. A retry after a lost acknowledgement uses the original run and ID. The backend must support atomic multi-key EVAL for the existing task and quota key names; an unsupported command or key-slot policy fails closed as a storage outage. This has not been tested against a hosted provider.

Redis scripts serialize commands but do not roll back previous writes on runtime failure. Reservation intentionally precedes the task write: a later failed write can conservatively consume a slot, but cannot leave an uncounted task. Do not automatically decrement reservations after a timeout, reset a missing counter, or infer absence from an incomplete scan. Store eviction, administrative resets, or writers that bypass this gate invalidate accounting and require reconciliation.

Rollout requires a separate, authorized operator decision and migration. Freeze all task writers, including old application instances; select the explicit limit; enumerate and verify all existing permanent task records for each owner; initialize permanent versioned counts from those verified records; ensure no legacy writer can bypass accounting; then enable gated writes. A verified fresh owner may be initialized to zero only by a trusted provisioning/migration path. This patch supplies neither an initialization endpoint nor a live migration and has not modified live data. Reconciliation of conservatively reserved slots likewise requires a write freeze and verified records before changing metadata. Lowering the configured limit does not delete existing records; owners at or above it cannot create new IDs.

The opt-in `WORKFLOW_TASK_REDIS_TESTS=1` test suite runs the production Lua against a disposable local Redis over a private Unix socket with TCP disabled. `WORKFLOW_TASK_REDIS_BINARY` may select an installed official Redis binary. It covers concurrent distinct writes, concurrent retries, invalid initialization, count boundaries, independent owners, lost acknowledgements and retries later in a capacity-rejected batch. The ordinary test suite does not start Redis; its REST fixtures assume initialized capacity and are not concurrency proof.

## Rate limiter credential consistency

The proxy rate limiter now uses the shared REST credential resolver, accepting either the complete Upstash pair or the complete KV pair with the existing Upstash precedence. A valid KV-only deployment no longer fails before the durable-task route. The existing TCP fallback, client reuse and production fail-closed behavior remain unchanged. No credentials are logged or changed.


## November 5 follow-up — storage budget and credential-family integrity

The confirmed task executor now creates a shared 25-second absolute task-storage deadline at the first workflow-task attempt in each reviewed batch. The deadline is passed through each task's atomic EVAL and mandatory GET readback; the existing per-request ceiling is ten seconds. A task attempted after the deadline is failed without contacting storage and receives no fabricated receipt. The batch stops further task writes after the first unavailable/uncertain storage result. Earlier readback-verified receipts remain intact, and retrying the same confirmed plan reuses deterministic record IDs. This is a task-storage limit only; unrelated tool actions retain their existing behavior, and a serverless global execution deadline still requires independent control.

The common Redis credential resolver now accepts only complete (URL, token) pairs from the same configuration family. A complete Upstash pair takes precedence; a complete KV pair works when the Upstash pair is incomplete. Partial credentials from different families cannot be combined.

CI acceptance on the follow-up commit must include focused task batch and Redis credential regressions, the full web suite, type-check, lint and build. Hosted Upstash and real-video/source provenance remain separately unverified. Deployment, owner quota initialization, and production task activation are not part of this code change.
