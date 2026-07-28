<<<<<<< HEAD
## Summary

Describe the outcome and the evidence that supports it.

## Linked issue

Fixes #

## Verification

=======
## Canonical issue

Closes #

## Outcome

Describe the user or operational result this PR produces.

## Scope

- Included:
- Explicitly excluded:

## Risk

- Risk level: low / medium / high
- Failure mode:
- Rollback:

## Verification

List exact automated and manual checks, tied to the current head SHA.

>>>>>>> origin/main
- [ ] Focused tests
- [ ] Required CI
- [ ] Review threads resolved

<<<<<<< HEAD
=======
## Production evidence

Provide the Vercel preview, production deployment, runtime evidence, or state why production evidence is not applicable.

## Agent handoff

- [ ] One canonical issue is linked
- [ ] No competing PR implements the same issue
- [ ] Acceptance criteria are satisfied
- [ ] Required checks pass on the current head
- [ ] Human decision is requested only for product, security, irreversible infrastructure, or production approval

>>>>>>> origin/main
## Agent provenance

Human-authored pull requests may delete this section. Agent-authored pull requests must replace agent-lock-example with agent-lock-manifest and fill the values. Scope and test paths remain authoritative in the linked issue.

<!-- agent-lock-example
{"issue_number": 0, "agent_login": "agent-name", "run_id": "provider-run-id"}
-->

The declared agent publishes a result comment on the linked issue or PR with the exact run ID and current 40-character head SHA. Replace `agent-lock-event-example` with `agent-lock-event` only when publishing real evidence.

<!-- agent-lock-event-example
{"kind": "artifact_ready", "run_id": "provider-run-id", "head_sha": "0000000000000000000000000000000000000000"}
-->
