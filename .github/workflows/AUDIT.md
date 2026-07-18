# Agent completion enforcement audit record

Owner: repository administrators. The advisory truth-gate workflow is diagnostic only. The merge-enforcement boundary is the default-branch `Agent completion enforcement` Check run bound directly to the PR head SHA.

Trust assumptions: a dedicated GitHub App, not an agent credential, retains append-only agent events and produces the exact-head per-path report. The verifier fails closed if the publisher App, report identity, trusted label actor, human exemption actor, or custom-role policy is absent or mismatched. Custom roles are fail-closed; legacy `read` is never an authorization signal.

Operational rule: protect `.github/agent-lock/trusted-publishers.json`, workflow files, and the verifier with CODEOWNERS and the repository ruleset. Required checks are: `Agent completion enforcement`, independent approval, and resolved conversations. `agent-completion/truth-gate` remains explicitly advisory.
