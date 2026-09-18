# MCP Skills extension (SEP-2640) — watch state and trust boundaries

**Issue:** [groupthinking/EventRelay#1640](https://github.com/groupthinking/EventRelay/issues/1640)
**Decision date:** 2026-09-15
**Current posture:** **ADOPT → TEST** (fixture-only; no live import or execution)

## Decision

Implement only bounded fixture and official-conformance coverage for
`io.modelcontextprotocol/skills`. Production retrieval, client import, and
skill execution remain disabled until their own observable receipts exist.

## Verified state

- MCP Core Maintainers accepted [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640) on 2026-09-03, and the Final core specification now lives at
  `modelcontextprotocol/modelcontextprotocol/seps/2640-skills-extension.md`
  ([commit `1eb5bbe`](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/1eb5bbe8ac933bdb595fedc687b8ed545e440491)).
- Historical working-group change evidence for the cache metadata requirement
  remains attributable to `modelcontextprotocol/ext-skills/specs/skills.md`
  ([commit `d866efd`](https://github.com/modelcontextprotocol/ext-skills/commit/d866efdba298b55b8156c7b7aa1bdebc1b625f4c)).
- The September 16 link-repair commit updated the core SEP's supporting links to
  the `ext-skills` archive paths
  ([commit `f56f204`](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/f56f204f6290f6531b14d5734eb3e0a10f0eb201)).
- The official conformance suite added seven Skills scenarios on 2026-09-11
  ([commit `7169291`](https://github.com/modelcontextprotocol/conformance/commit/7169291ec0b68eb370fddcd9947313ab0d5e4156)).
- The official MCP client-support matrix currently marks ChatGPT's Skills
  support as **Partial** ([commit `2997f33`](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/2997f33bf6e4aab3db48d755fc877c8feab32c71)).
  This repository does not treat that matrix entry as proof of a live ChatGPT
  import wire contract.

## Trust boundaries to preserve

If/when we run the conformance spike, preserve these invariants:

- Skills are identified by **compound identity** `{server_identity, skill_uri}`.
- Manifests must include full per-file SHA-256 + byte-size metadata, or explicit `"dynamic"`.
- Resource reads and model-context injection remain **origin-bound**.
- No host execution or permission grant without explicit per-skill approval.
- Approval must be revoked when resource/digest sets change.
- Cache writes must be isolated by origin+skill, or every read must re-verify digest.
- No silent skill-name shadowing across servers or local skills.

## Implemented bounded actions (fixture-only)

The official suite is pinned with explicit supported, failed, and excluded
scenario accounting. The Agent Factory host also has a fixture-only ChatGPT
handoff contract that:

1. Requires the Resources and Skills extension capabilities.
2. Validates a direct `skills/get` complete response without depending on listing.
3. Stores compound identity `{server_identity, skill_uri}` and binds approval to
   that identity plus the verified manifest digest.
4. Verifies static-resource byte size + SHA-256 before a handoff can be prepared.
5. Rejects digest drift, cross-origin reads, decoded path traversal, invalid cache
   metadata, any mismatch in the complete verbatim frontmatter object, top-level
   dynamic resources, and unapproved execution.
6. Emits a deterministic, machine-readable receipt that distinguishes the
   accepted core normative contract from preserved working-group design-history
   evidence while performing zero network, import, tool, or external-effect
   operations.

## Non-goals / safety boundary

- Do not claim live ChatGPT compatibility or conformance from fixture coverage or
  the official MCP client matrix.
- Do not equate remote MCP-served skills with local trusted skills.
- Do not enable remote skill execution, deployment, merge, or production configuration changes.
