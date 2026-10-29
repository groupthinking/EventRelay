# Durable review journal: opt-in local runtime integration

This named draft integration extends the existing `/api/agents/actions` **preview** path. It does not introduce another product, replace Origin G.A.T.E., authorize deployment, or execute an original model-proposed action.

## Default and opt-in behavior

Without `RELAY_REVIEW_JOURNAL_MODE`, the current preview and execute behavior is unchanged. With the exact operator-configured value `local-review-only`:

1. Resolve trusted, absolute local interpreter/scripts/state paths. Reject invalid configuration and known serverless hosts before requesting a model plan. Vercel's read-only/ephemeral filesystem is unsupported.
2. Reject `mode: execute` with HTTP 409 before any original tool runs.
3. Require the existing trusted signed identity resolution, never a request-body email. Anonymous attempts get HTTP 401 before a model call.
4. Request `runActionAgent({...options, executeTools:false})` exactly as the existing preview path does.
5. Persist the exact pending plan as a local artifact through the Node bridge and Python SQLite command journal. Scope the idempotency key by a digest of trusted identity plus exact plan. A client `jobId` cannot select this key, paths, permissions or adapters.
6. Return `localArtifactReceipt` only after observed bytes satisfy all required gates. Original actions remain pending, `originalActionsExecuted:false` and `originalTaskComplete:false`.

An empty model plan creates an honest empty review artifact. Invalid/nonpending model output or a failed/unknown journal result does not silently fall back to ephemeral success. Errors return a sanitized non-success response; no original actions are executed. Unknown subprocess outcomes are not retried automatically. Inspect the durable task receipt before any recovery.

The opt-in is operator-owned environment configuration on a persistent single host:

```text
RELAY_REVIEW_JOURNAL_MODE=local-review-only
RELAY_REVIEW_STATE_DIRECTORY=/absolute/private/state-directory
RELAY_REVIEW_SCRIPTS_DIRECTORY=/absolute/EventRelay/scripts
RELAY_REVIEW_PYTHON_EXECUTABLE=/absolute/path/to/python3
```

No environment changes are made by this PR. Do not provide these fields through model prompts or HTTP payloads. Do not enable on Vercel, Lambda, Cloud Run, network filesystems or a directory shared with untrusted users. Plan contents are plaintext; use a dedicated permission-restricted account/directory, never put credentials in the plan, and establish a retention policy before multi-user hosting. This slice is intentionally not a hosted storage service or a public receipt lookup API.

## Execution and evidence contract

The Python slice allows one fixed local artifact operation per immutable contract. It rejects model-selected paths, unknown tools, executable code and approval fields. `external_action` always blocks. SQLite holds contract hashes, durable execution intent, attempt budgets and an append-only hash-linked timeline. Writes are atomic/no-clobber, and recovery checks actual current bytes before replaying anything. A permission denial blocks rather than retries. Stale/deleted/changed artifacts invalidate receipts.

Receipts use `relay.local-receipt.v1`, **not** an Origin G.A.T.E. receipt or operational PASS. The integration never imports a deployment PASS as authority. Hash-linked history is integrity checking within a trusted OS account, not authentication against a malicious database owner. Monetary cost remains unknown because host computation is not metered. The new local journal does not replace shared runtime session storage, Upstash Video Packs, scheduler/reminder systems or any external action adapter.

## Verify

```bash
python3 -m unittest discover -s tests -p test_relay_local_harness.py -v
node --test tests/relay-local-review.test.mjs tests/relay-review-route.test.mjs
```

Node 24 executes the actual TypeScript route using built-in type stripping. Provider, auth and minimal framework dependencies are test stubs; the integration bridge, subprocesses, SQLite and artifact verification are real. The tests make no provider/network calls. Existing full web/Python suites and strict type/lint checks remain separate acceptance stages; these focused tests do not substitute for them.

## Deployment and review boundaries

The intended branch `codex/relay-durable-review-integration` has a branch-specific Vercel deployment exclusion in its first proposed tree. This is not enough to assert that every linked project's effective configuration honors it; verify effective Vercel project root/config before publishing the remote ref. Never publish an intermediate branch pointing to unguarded main. Do not weaken preview-required E2E checks merely to obtain green CI. No preview means those checks may remain blocked/red by design.

The draft remains unmerged. Activation, live model acceptance and external project completion are not proven by offline tests. No credential creation, deployment, production account change, original action execution, UVAI reconstruction or Shopify change is authorized or claimed by this integration.
