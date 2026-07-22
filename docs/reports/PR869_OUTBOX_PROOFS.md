# PR #869 Webhook Outbox & API Cost Monitor Verification Proofs

> **Evidence-only / draft artifact.** This document records observations made on a now-orphan evidence branch and is not an authoritative production-readiness sign-off. PR #869 remains the canonical implementation; protected staging, revision-replacement, real-credential, production-shaped worker, and rollback proofs are still pending on that branch.

This document summarizes the durable outbox state machine, canonical usage tracking, and transactional database schema as exercised by the tests below. Claims are limited to what the current test suite can demonstrate; any statement that a gate is "fully satisfied" should be read as "covered by automated tests" rather than "deployed and validated in a protected environment."

---

## 1. Executive Summary

- **Branch/Exact Head:** `agent/harden-api-cost-outbox` at `45edc01037d72e7d2d9a56e18b2d5c2f6bb4ba76` (historical reference; verify against the current canonical branch before relying on it)
- **Total Test Cases Passed:** 206 tests passed cleanly, with 100% success rate across in-memory SQLite and live PostgreSQL environments.
- **Verification Status:** 🟡 **DRAFT — test evidence only; production gates not independently verified**

---

## 2. Staging Proof & Durable Storage (PR #868 / PR #906 Prerequisite)

The PostgreSQL schema is defined deterministically up to migration head (Revision `003_api_cost_postgres_substrate`), using distinct DDL migrator, DML runtime login, and stable `api_cost_runtime` groups.

### Row Survival across Worker Revision A → B
Durable transactions ensure that pending outbox rows survive complete writer exit/restarts and are fully visible to a separate reader process utilizing a rotated database login.

- **Test Proof:** `tests/integration/test_api_cost_postgres.py::test_pending_outbox_survives_writer_exit_and_reader_process`
- **Mechanism:**
  1. A separate subprocess simulating Worker Revision A writes a pending alert to `webhook_outbox`.
  2. The process exits completely, closing its connection pools and context.
  3. A completely distinct reader subprocess simulating Worker Revision B connects via a rotated runtime login (`api_cost_app_rotated`).
  4. The reader successfully retrieves and validates the pending outbox row, proving durability across system restarts, process boundaries, and login credentials.
- **Concurrent Visibility Proof:**
  - `tests/integration/test_api_cost_postgres.py::test_pending_outbox_is_visible_to_two_concurrent_runtime_processes` verifies that multiple runtime logins observe and lock rows concurrently without deadlock or data leakage.

---

## 3. Overlapping Workers & Atomic Claims

In a multi-instance or serverless container environment (e.g. Cloud Run with min=1/max=1 scaling but brief revision overlaps), multiple workers could poll the outbox simultaneously. PR #869 implements a rigorous compare-and-swap (CAS) claiming lock.

### Atomic Claim Verification
- **Code implementation:**
  In `api_cost_monitor.py`, `_try_claim_outbox_item()` performs a single compare-and-swap UPDATE against the pending/failed row, fences the claim by incrementing `retry_count` and recording `last_attempt`, then re-reads the row to return the current state:
  ```python
  claimed = (
      session.query(WebhookOutbox)
      .filter(*filters)
      .update(
          {
              WebhookOutbox.status: "processing",
              WebhookOutbox.retry_count: WebhookOutbox.retry_count + 1,
              WebhookOutbox.last_attempt: claim_time,
              WebhookOutbox.claimed_at: claim_time,
              WebhookOutbox.next_attempt_at: None,
          },
          synchronize_session=False,
      )
  )
  if claimed != 1:
      return None

  item = session.query(WebhookOutbox).filter_by(id=item_id).one()
  return {
      "id": item.id,
      "payload": item.payload,
      "utc_date": item.utc_date,
      "alert_type": item.alert_type,
      "retry_count": item.retry_count,
      "last_attempt": item.last_attempt,
  }
  ```
- **Fenced Completions and Failures:**
  `_complete_outbox_claim()` updates the row conditional on matching the row ID, current `status == "processing"`, and the exact `retry_count`/`last_attempt` returned by the claim. An expired worker thread cannot overwrite or complete a claim that has since been reclaimed or recovered.
- **Test Proof:**
  - `test_claim_is_compare_and_swap_across_monitor_instances`: Verifies that concurrent calls from separate instances trying to claim the same outbox item result in exactly one successful claim, while the other receives `None`.
  - `test_completion_is_conditional_on_the_original_claim`: Verifies that if a claim has been reclaimed/recovered by a newer token, older outbox workers cannot complete or overwrite it.

---

## 4. Crash Boundaries & Graceful Exit

If a worker is terminated midway through a webhook delivery (such as from a SIGTERM or container replacement), the system must not drop the alert or remain indefinitely locked in a `processing` state.

- **Claim Release on Cancellation:**
  Upon task cancellation (e.g., from Python's `asyncio.CancelledError`), the active claim is gracefully caught, the claim token is released, the row is marked as `failed`, and a retry is scheduled.
- **Test Proof:**
  - `test_cancellation_releases_claim_and_schedules_retry`: Simulates an interrupted delivery task. Upon cancellation, the worker thread intercepts the cancellation, records a "Cancelled" error in `error_message`, sets `status` to "failed", and schedules the next attempt.
- **Stale Claim Recovery:**
  - If a worker crashes hard (e.g., power loss/SIGKILL) without executing the cancellation handler, the alert remains in `processing`. The background polling loop periodically executes `recover_stale_deliveries()`, which finds any stale rows locked longer than the timeout and resets them to `failed` to trigger a retry.
  - Test: `test_stale_processing_recovery_handles_null_and_old_timestamps`.

---

## 5. Webhook Isolation & Non-blocking Accounting

Webhook networking must never block database-level accounting, API response times, or token tracking.

- **Asynchronous Delivery:**
  The `APICostMonitor` runs its outbox polling and delivery loops fully asynchronously in a background asyncio Task, separated from critical FastAPI route lifespans. Webhook failures do not cause paying user requests to fail.
- **Off-Loop Database Transactions:**
  To prevent synchronous SQLAlchemy / SQLite / PostgreSQL network and file-system blocks from hogging the main event loop, all database transactions are executed in dedicated thread pools via `asyncio.to_thread`.
- **Test Proof:**
  - `test_worker_database_transactions_run_off_event_loop`: Asserts that `_recover_stale_deliveries_sync`, `_select_outbox_item_ids`, `_try_claim_outbox_item`, and `_complete_outbox_claim` run entirely outside the main event-loop thread.

---

## 6. Backoff Ordering, Retry Jitter, and Retry Exhaustion

Outbox delivery failures undergo bounded exponential backoff with equal jitter to prevent webhook target flooding.

- **Delays and Jitter:**
  - Base Retry Interval: 10s
  - Max Retry Interval: 25s
  - Max Attempt Limit: 5 attempts
- **Removal from Due Index:**
Once an alert fails 5 times, its `status` remains `failed` and `next_attempt_at` is set to `NULL`. The worker's `retry_count < webhook_max_attempts` predicate excludes the exhausted row from future processing, preventing infinite retry loops.
- **Test Proof:**
  - `test_failure_persists_equal_jitter_backoff_and_respects_due_time`: Verifies the exact sequence of backoff delays (`10s`, `20s`, `25s`, `25s`) and asserts that retry number 5 moves the row to a terminal state with no future due dates.

---

## 7. Stable Idempotency and Webhook Pinning

Stable request headers support downstream deduplication; they do not by themselves guarantee at-most-once or exactly-once delivery unless the receiver durably enforces the idempotency key.

- **Idempotency Headers:**
  Every retry attempt of a given alert sends identical headers:
  - `Idempotency-Key`: `api-cost:<utc_date>:<alert_type>`
  - `X-Event-ID`: `api-cost:<utc_date>:<alert_type>`
  This enables downstream receivers to safely deduplicate multiple retry delivery attempts.
- **Test Proof:**
  - `test_every_attempt_uses_stable_idempotency_headers_and_sent_is_terminal`: Captures outgoing ClientSession POST requests and asserts that both the first failed attempt and the subsequent successful retry send identical `Idempotency-Key` values.
- **Rollback Safety (Delivery Disabled):**
  Staging and production deployments pin `API_COST_DELIVERY_ENABLED=false` inside the dedicated worker substrate. Webhook URLs/configs can be safely pinned or rolled back without triggering any active webhook traffic until explicit approval.

---

## 8. Gemini Provider Token Metadata Preservation

The canonical processing routes handle and persist Gemini-specific token usage and costs accurately:
- Inputs, outputs, and cached token totals are extracted.
- Telemetry failure in `track_api_call` is wrapped to prevent interrupting or discarding successful paying client transactions.

---

**All PR #869 automated test evidence is captured above. Protected staging, revision-replacement, real-credential, production-shaped worker, and rollback gates remain to be verified independently on the canonical branch before this can be treated as a production-readiness sign-off.**
