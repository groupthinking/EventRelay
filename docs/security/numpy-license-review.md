# NumPy license review for PR #2409

Reviewed on 2026-10-16. This records the license-check diagnosis for [PR #2409](https://github.com/groupthinking/EventRelay/pull/2409) and [bootstrap issue #2425](https://github.com/groupthinking/EventRelay/issues/2425). The remaining security backlog stays in [#2396](https://github.com/groupthinking/EventRelay/issues/2396).

## Historical rejection

[Dependency Review run 38258616716, job 114843054032](https://github.com/groupthinking/EventRelay/actions/runs/38258616716/job/114843054032) failed on 2026-10-12 while comparing base `bd0f437180b994d8916fcba22ada610bf2fbae0a` with head `1d9f72d7c40bff34aa43b8107cb817ad01e8efd5`. It reported NumPy `2.5.3` to `2.5.4` as a dependency graph change, with six incompatible-license entries across three manifests (each appears twice):

- `requirements.txt`
- `docs/knowledge_prototypes/universal-automation-service/requirements.txt`
- `docs/knowledge_prototypes/mcp-servers/mcp-alexnet/requirements.txt`

The complete expression was `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`. Both [NumPy 2.5.3 metadata](https://pypi.org/pypi/numpy/2.5.3/json) and [NumPy 2.5.4 metadata](https://pypi.org/pypi/numpy/2.5.4/json) declare this same expression. NumPy's bundled [libdivide license](https://github.com/numpy/numpy/blob/v2.5.4/numpy/_core/include/numpy/libdivide/LICENSE.txt) contains the Zlib terms. Dropping that component or replacing the expression with NumPy's primary BSD license would lose material license information.

This was a valid policy rejection, not an AND parser failure. The action used `a1d282b36b6f3519aa1f3fc636f609c47dddb294`. Its [license check](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/licenses.ts) passes the full expression to its [SPDX evaluator](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/spdx.ts). Zlib is absent from this repository's allowlist. A focused check with the action's locked `spdx-satisfies@6.0.0` version rejects the NumPy expression, accepts an AND expression containing only the already approved components, and rejects Zlib alone.

## Current head evidence and limits

[Dependency Review run 38707004697, job 116329188139](https://github.com/groupthinking/EventRelay/actions/runs/38707004697/job/116329188139) succeeded on 2026-10-15 for base `002b697c3c5c6cb208c24e1b3413f13f1a2a8794` and head `64d2562dce7f2d870b32e3982ffe8888bbdcd808`. Dependency detection, snapshot submission, and Dependency Review all executed successfully; this was not the no-dependency-delta skip path. Its complete Dependency Changes section has no NumPy addition, removal, or license failure.

The action SHA, license allowlist, and package exclusions were identical in these two runs. The three affected requirement files, `pyproject.toml`, `uv.lock`, and dependency-review workflow also have no source diff between those heads. The comparison's base changed, and the action submitted fresh resolver-generated snapshots. The observable change is in the dependency graph delta. The retained logs do not expose the complete base and head snapshots, so they do not establish which snapshot change removed the NumPy delta. There is no evidence of a NumPy license correction or policy approval.

The current passing comparison resolves the historical PR check blocker for that exact head only. It does not approve NumPy's Zlib component, establish a compliant full dependency inventory, or prove a future head will pass. A future NumPy addition with this expression must still fail under the present policy. This work adds no Zlib permission, NumPy exclusion, warning-only mode, or license-check disablement.

## Reviewable evidence going forward

The dependency-review workflow now pins the same action implementation observed in both runs and names the exact PR base and head SHAs explicitly. After an attempted comparison, it saves the action outcome and all four raw dependency review outputs in `review.json`, retaining duplicate occurrences and complete SPDX expressions. Missing outputs stay empty rather than being converted to a clean empty array. The artifact name includes the PR head SHA and run attempt, and upload runs after a failed review as well as a successful review. The original review failure remains blocking.

The workflow regression tests execute the evidence-writing step with an incompatible composite expression, duplicate occurrences, incomplete outputs, and hostile strings supplied as data. They also guard the unchanged license allowlist, enabled blocking license check, and absence of a NumPy exclusion. These tests verify local workflow behavior and policy preservation; they do not replace a future exact-head hosted Dependency Review run.

The image remediation remains partial. This license diagnosis does not account for or dismiss the retained 259 HIGH/CRITICAL image occurrences, approve strict enforcement completion, close #2396, or establish production remediation.
