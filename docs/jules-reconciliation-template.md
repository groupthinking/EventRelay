# Jules finding reconciliation

Use this per repository, against a pinned current default-branch commit. An email is a claim, not proof that a defect remains.

## Inputs

- Repository, source suggestion URL/date, exact claim, file and symbol.
- Current default-branch SHA and relevant file blob SHAs.
- Existing issue, pull request, review and CI state; reuse the canonical work.
- Authorized changes and whether merge/deployment is authorized.

## Procedure

1. Inventory all accessible suggestions. Paginate; record omitted counts and access failures. Keep private repository details and mail metadata out of public repositories.
2. Deduplicate by repository + symbol + failure behavior, retaining every source reference. Similar titles are candidates for grouping, not proof of equivalence.
3. Read current code, callers, deployment entry points and tests. Classify each claim as reproduced, already addressed, not reproduced, coverage gap, design proposal, or blocked. File existence and a closed PR do not prove resolution.
4. For a defect, add a deterministic regression that fails on pinned main for the claimed reason. Mock external service boundaries, not the function under test. For a coverage gap, demonstrate missing coverage and test the existing contract; do not invent a behavior change.
5. Apply the smallest correction. Preserve public contracts, error behavior, security boundaries and ordering. Keep refactors and feature requests separate.
6. Run focused regression and neighboring tests. Preserve commands, exit codes, stdout/stderr, JUnit, dependency versions, and source/test hashes. A failing baseline must be a product failure, not a missing dependency or broken test.
7. Refresh main before publication. If relevant code moved, reclassify and rerun. Publish one canonical PR per coherent correction with a linked issue and rollback.
8. Verify required CI and unresolved reviews on the exact PR head. Merge only with authorization and satisfied repository gates; never bypass protections. Record the returned merge SHA and confirm ancestry on main.
9. Deploy only through the existing authorized target. Verify the deployment's source SHA and health before claiming it live. A merged commit or queued build is not deployment evidence.

## Per-finding record

```json
{
  "schema_version": 1,
  "repository": "owner/repo",
  "finding_id": "stable-id",
  "sources": [],
  "claim": "",
  "symbol": "",
  "base_sha": "",
  "blob_sha": "",
  "classification": "blocked",
  "reason": "Not yet evaluated",
  "reproduction": {"command": null, "exit_code": null, "artifact": null},
  "correction": {"files": [], "head_sha": null},
  "verification": [],
  "pull_request": null,
  "merge_sha": null,
  "deployment": null,
  "remaining_blocker": null
}
```

## Portfolio execution rules

- Prioritize demonstrated security/data-loss failures, then runtime reliability, then coverage, then measured performance. Keep subjective code-health and product additions in a separate decision queue.
- One writer per overlapping file set. Batch independent read-only inventory; do not batch unrelated production mutations.
- Store a durable ledger keyed by finding ID and current blob SHA. Reopen evaluation when a relevant blob changes. Never infer completion from unread/read email labels or an agent's prose.
- Stop a row at a concrete blocker while continuing independent rows. Report unresolved counts and omitted suggestions explicitly.
- No automatic acceptance of suggestions, bulk blind fixes, or automatic merge permission inherited from this template.

| Temptation | Required evidence/action |
| --- | --- |
| Jules says it is broken | Reproduce on current main |
| Tests are green | Show the regression failed before the fix |
| A test is missing | Add coverage; preserve correct existing behavior |
| External origins mean insecure CORS | Check exact allowlist, credentials and deployed entry point |
| PR is closed | Verify merged SHA and current source behavior |
| Some suggestions are hidden | Keep them blocked; do not invent them |
| Source inspected | Label source-inspected; do not claim runtime verification |
| Merge succeeded | Verify main; report deployment separately |
