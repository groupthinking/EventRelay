# Exception handling standards (AUDIT-006)

Critical paths (auth, G.A.T.E., pack persistence, deployment handoff):

1. Catch specific exceptions first; use `except Exception` only at outer boundaries with `logger.exception` or structured `logger.error(..., exc_info=True)`.
2. Never swallow auth or payment failures—return explicit HTTP status / reason codes.
3. Bare `except:` is forbidden in new code (Ruff BLE001 in critical modules over time).

Remediation is incremental; issue #2168 remains open. The previously prioritized `backend/api/v1/router.py` path is absent from the repository tree inspected on 2026-10-08. Current audit targets include `apps/backend/main.py`, `src/agents/mcp_tools/deployment_tool.py`, agent orchestrators under `src/agents/`, and agent services under `src/youtube_extension/services/agents/`. This document is policy, not evidence that every critical handler has been remediated.

Before changing a handler, capture its concrete failure mode and caller contract. Use specific exceptions for expected failures; outer-boundary exceptions must log context and propagate an explicit failure. Do not convert security/payment failures into successful defaults. A repository-wide count is insufficient acceptance evidence; attach route/agent failure tests for each repaired critical path.

