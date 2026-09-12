# MCP Skills extension (SEP-2640) — watch state and trust boundaries

**Issue:** [groupthinking/EventRelay#1640](https://github.com/groupthinking/EventRelay/issues/1640)  
**Decision date:** 2026-09-08  
**Current posture:** **WATCH → TEST** (no implementation yet)

## Decision

Do not implement production behavior for `io.modelcontextprotocol/skills` until one activation trigger is verified:

1. SEP-2640 is merged/accepted, or
2. an official MCP SDK ships a reference implementation with a pinned draft revision suitable for interop testing.

## Verified state

- The MCP Skills working group published stable-format rendering for `io.modelcontextprotocol/skills` on 2026-09-04 (`ext-skills` commit `f1f8605`).
- The extension repository labels the work experimental and not an official MCP specification or recommendation.
- [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640) is still open and remains the canonical proposal.

## Trust boundaries to preserve

If/when we run the conformance spike, preserve these invariants:

- Skills are identified by **compound identity** `{server_identity, skill_uri}`.
- Manifests must include full per-file SHA-256 + byte-size metadata, or explicit `"dynamic"`.
- Resource reads and model-context injection remain **origin-bound**.
- No host execution or permission grant without explicit per-skill approval.
- Approval must be revoked when resource/digest sets change.
- Cache writes must be isolated by origin+skill, or every read must re-verify digest.
- No silent skill-name shadowing across servers or local skills.

## Bounded action at trigger time (fixture-only)

When an activation trigger is verified, run a **draft-only**, **feature-flagged** conformance spike:

1. Add sample server capability for `io.modelcontextprotocol/skills`.
2. Exercise `skills/list`, `skills/get`, and normal `resources/read`.
3. Store compound identity `{server_identity, skill_uri}`.
4. Verify byte size + SHA-256 before exposing skill files to model context.
5. Reject digest drift, cross-origin reads, silent name collisions, and unapproved execution.
6. Emit EventRelay receipts for listing, approval, retrieval, verification, and denial.

## Non-goals / safety boundary

- Do not present SEP-2640 as an official standard while the SEP remains open.
- Do not equate remote MCP-served skills with local trusted skills.
- Do not enable remote skill execution, deployment, merge, or production configuration changes.
