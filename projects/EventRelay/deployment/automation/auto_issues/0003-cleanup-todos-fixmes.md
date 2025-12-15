Title: Code hygiene — audit and triage TODO/FIXME comments into issues

Summary
-------
The codebase contains many `TODO` and `FIXME` comments across core modules, archived artifacts, and third-party vendored packages. These markers hide incomplete work and technical debt that must be triaged before production readiness.

Scope
-----
- `agents/specialized/quality_agent.py` intentionally scans for `TODO|FIXME|HACK|XXX` comments but there are many in other areas.
- Documentation, tests, and deployment adapters (e.g., `video-to-execution-starter-v2/deploy/*`) contain TODOs.

Recommended remediation
----------------------
1. Create a prioritized backlog of real issues from TODOs/FIXMEs found in source files (exclude vendored deps and virtualenv).
2. Address production-critical TODOs first (deployment adapters, backend endpoints, API key handling).
3. Remove or convert cosmetic TODOs into low-priority issues or TODO tracking docs.
4. Add a lint rule to warn on TODO/FIXME in production code.

Next steps (automated)
----------------------
- Create a PR adding this checklist and a script `tools/collect_todos.py` that extracts TODOs and emits a JSON backlog for triage.

Suggested labels: maintenance, tech-debt
