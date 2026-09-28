# September 27 Jules reconciliation

Baseline: `adf8d1e0e61787966a9a09b7827c8d54abd27bcc`.

| Finding | Result | Evidence |
| --- | --- | --- |
| JWT secret fallback | Already addressed | Blob `005ac1b912f47e7c5987ef85cdde313c064c4452`; generated-app signing-fails-closed test passes |
| Blocking notification file append | Reproduced and corrected | `before.xml`: thread assertion fails; `after.xml`: passes. Open/write moved together into `asyncio.to_thread` |
| Schema queries in cleanup loop | Already addressed | Real SQLite trace: one PRAGMA for three deletion batches; five expired rows removed, one recent row retained |
| Missing BigQuery access-token test | Already addressed | Existing missing/empty-token tests pass in focused suite |
| Missing checkpoint I/O failure tests | Coverage gap corrected | New mkdir, temporary write and rename failures propagate and preserve previous latest checkpoint; upload not called |
| External domains in credentialed CORS | Broad claim not reproduced | Actual configurations reject arbitrary and lookalike origins; uvai.io is explicitly allowed |
| Legacy backend localhost origins | Configuration difference remains | Cited backend allows fixed localhost ports; Docker-selected `youtube_extension.main` filters them in production. Live deployment configuration was not inspected; do not claim all entry points are equally hardened |
| Long Next.js generator | Design/refactoring proposal | Function still exists; length alone is not a reproducible defect; no broad refactor |
| Redis/Upstash TODO | Feature proposal | Text occurs inside a generation prompt; no demonstrated runtime defect; no storage change |
| 19 omitted suggestions | Blocked | Email includes two omitted coverage items and 17 omitted code-health items; Jules page requires sign-in |

## Commands and results

Use the repository's Python environment with the dependencies in `environment.txt`.

Baseline, after adding regressions but before source correction:

```sh
python -m pytest tests/unit/test_notification_service.py tests/unit/test_weight_persistence.py tests/unit/test_bigquery_export.py tests/unit/test_database_cleanup_service.py tests/unit/test_database_cleanup_security.py -q --no-cov
```

Exit 1: **1 failed, 161 passed**. The single failure proves file I/O used the event-loop thread.

After correction, the same command plus `tests/unit/test_code_generator.py`:
exit 0, **258 passed**. Full logs and JUnit are adjacent. Tests use local files and mocked network boundaries; no external email or cloud write was performed.

Additional checks:

```sh
PYTHONPATH=src python artifacts/jules-2026-09-27/verify_findings.py
git diff --check
```

Both exit 0. `reconciliation-checks.json` records actual middleware allow/deny checks and SQLite traces. CORS verification executes the exact configuration AST nodes in isolation, not full application startup or a live endpoint.

## Boundaries

The production change is only the notification append. The existing suppression/logging of append errors is preserved. Cancellation of a `to_thread` await does not stop a worker already writing; this patch makes no durability or ordering guarantee for concurrent/cancelled callers. No configuration, JWT, database query, generated application or checkpoint runtime changes.

CI, merge and deployment must be verified separately on the published head. This local receipt does not assert any of them.
