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
