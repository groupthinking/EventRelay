## Summary

Describe the outcome and the evidence that supports it.

## Linked issue

Fixes #

## Verification

- [ ] Focused tests
- [ ] Required CI
- [ ] Review threads resolved

## Agent provenance

Human-authored pull requests may delete this section. Agent-authored pull requests must replace agent-lock-example with agent-lock-manifest and fill the values. Scope and test paths remain authoritative in the linked issue.

<!-- agent-lock-example
{"issue_number": 0, "agent_login": "agent-name", "run_id": "provider-run-id"}
-->

The declared agent publishes a result comment on the linked issue or PR with the exact run ID and current 40-character head SHA. Replace `agent-lock-event-example` with `agent-lock-event` only when publishing real evidence.

<!-- agent-lock-event-example
{"kind": "artifact_ready", "run_id": "provider-run-id", "head_sha": "0000000000000000000000000000000000000000"}
-->

<!-- Touched for completion gate -->
