# Studio playflow integration

Integrate PR #2439 with main `512a2558f73d6281b6a880548bedf140b7e30292`.

- Preserve Ship this ZIP export, honest Events, named tools and a single pack workbench.
- Keep Tasks as the default output, source-bound task export and inspectable proposal inputs.
- Restore transcript-tab retry without removing the toolbar retry.
- Keep `agentWorkflowUi` off by default. Review this run only reads proposals from the selected completed, stored-pack run. It does not start a new workflow or execute a proposed tool.
- Scope pending and completed review results to the exact selected row, run and pack identity; discard obsolete async results.
- Show stack-check status for the authenticated viewer.

Application tests and hosted checks must cover the resulting integration commit. Synthetic fixtures do not establish real-video acceptance. This review branch has automatic Vercel deployments disabled. Merge, preview deployment and production promotion remain separate gates.
