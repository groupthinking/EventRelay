## Canonical issue

Closes #1

## Outcome

Fixes the `NotImplementedError` in `MCPOrchestrator._execute_on_server` by introducing a real `aiohttp.ClientSession` based JSON-RPC 2.0 implementation over HTTP. Improves performance by reusing a pooled `aiohttp.ClientSession`.

## Scope

- Included: `src/youtube_extension/services/mcp/orchestrator.py`, `tests/unit/test_mcp_orchestrator.py`
- Explicitly excluded: N/A

## Risk

- Risk level: low
- Failure mode: Server timeout
- Rollback: Revert

## Verification

- [x] Focused tests
- [x] Required CI
- [x] Review threads resolved

## Production evidence

N/A, testing backend implementation locally via unit tests.

## Agent handoff

- [x] One canonical issue is linked
- [x] No competing PR implements the same issue
- [x] Acceptance criteria are satisfied
- [x] Required checks pass on the current head
- [x] Human decision is requested only for product, security, irreversible infrastructure, or production approval

## Agent provenance

<!-- agent-lock-manifest
{"issue_number": 1, "agent_login": "jules", "run_id": "run-12345"}
-->
