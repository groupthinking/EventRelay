# Exception handling standards (AUDIT-006)

Critical paths (auth, G.A.T.E., pack persistence, deployment handoff):

1. Catch specific exceptions first; use `except Exception` only at outer boundaries with `logger.exception` or structured `logger.error(..., exc_info=True)`.
2. Never swallow auth or payment failures—return explicit HTTP status / reason codes.
3. Bare `except:` is forbidden in new code (Ruff BLE001 in critical modules over time).

Remediation is incremental; prioritize `backend/api/v1/router.py`, `services/agents/`, and MCP orchestrator entrypoints.
