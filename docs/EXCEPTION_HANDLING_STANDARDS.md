# Exception handling standards (AUDIT-006)

Critical paths (auth, G.A.T.E., pack persistence, deployment handoff):

1. Catch specific exceptions first; use `except Exception` only at outer boundaries with `logger.exception` or structured `logger.error(..., exc_info=True)`.
2. Never swallow auth or payment failures—return explicit HTTP status / reason codes.
3. Bare `except:` is forbidden in new code (Ruff BLE001 in critical modules over time).

Remediation is incremental; issue #2168 remains open. The previously prioritized `backend/api/v1/router.py` path is absent from the repository tree inspected on 2026-10-08. Current audit targets include `apps/backend/main.py`, `src/agents/mcp_tools/deployment_tool.py`, agent orchestrators under `src/agents/`, and agent services under `src/youtube_extension/services/agents/`. This document is policy, not evidence that every critical handler has been remediated.

Before changing a handler, capture its concrete failure mode and caller contract. Use specific exceptions for expected failures; outer-boundary exceptions must log context and propagate an explicit failure. Do not convert security/payment failures into successful defaults. A repository-wide count is insufficient acceptance evidence; attach route/agent failure tests for each repaired critical path.


## Boundary marker

A broad handler (`except Exception`) that is kept on purpose carries an inline marker with its reason, on the `except` line:

```python
except Exception as exc:  # exception-boundary: <why this must not raise and what the caller gets instead>
```

A marked boundary logs the context (step/agent/task), the error class, and the traceback, and returns an explicit failure. Unmarked broad handlers are remediation debt.

## Remediated (issue #2168, slice 1)

| File | Before | After | Tests |
| --- | --- | --- | --- |
| `src/agents/mcp_tools/deployment_tool.py` | 4 broad handlers (entry point + git / GitHub repo / Vercel steps); owner-lookup `RuntimeError` swallowed by the GitHub step; entry point printed to stderr | Steps catch only `OSError` and `subprocess.SubprocessError` (incl. `TimeoutExpired`); owner lookup raises `GitHubIdentityError(RuntimeError)`, the only exception caught around it; every failed step logs stage, error class and a token-redacted traceback; one marked boundary at the entry point logs via `logger` and returns `status: "error"` with `error_class` | `tests/unit/test_exception_boundaries_2168.py` |
| `src/youtube_extension/services/agents/adapters/agent_orchestrator.py` | 5 broad handlers | Shared SQL store setup catches only `SQLAlchemyError`, `ImportError` (missing driver) and `OSError` (file); anything else raises. Four marked boundaries (create agent, `execute_task`, `execute_single`, message delivery) log agent/task, error class and traceback; return values unchanged | `tests/unit/test_exception_boundaries_2168.py` |

The test file's guard test pins the broad-handler count (1 and 4) and requires every one to carry the marker with a reason.

## Remaining work

Counts are unmarked `except:` / `except Exception` / `except BaseException` lines after this slice (`grep -rnE '^\s*except\s*(:|\(?\s*(Exception|BaseException)\b)'`), measured 2026-11-09.

- `src/agents/` (all modules): 125 unmarked broad handlers.
- `src/youtube_extension/services/agents/adapters/` (other adapters): 12 unmarked broad handlers.
- `src/youtube_extension/services/ai/gemini_service.py`: 22 broad handlers.
- `src/utils/notebooklm_ingest.py`: 5 bare `except:` (10 broad handlers in total).
- `apps/backend/main.py` caption fetch: one `except Exception` around `_fetch_captions`; it already fails closed (returns `success: False`, no fabricated text) but should be narrowed to the provider/transport errors and timeout, or marked as a boundary with logging.
- Ruff `BLE001` (blind except) is not enabled yet; turn it on per module as each one is remediated, starting with the two files above.
