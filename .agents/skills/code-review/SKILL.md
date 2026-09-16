---
name: code-review
description: Perform context-aware, high-confidence code reviews for EventRelay changes and pull requests
---

# Code Review

Review changes as a maintainer of EventRelay. Read the complete diff first, then
inspect the surrounding implementation, its callers, tests, configuration, and
relevant project instructions before reporting a finding.

## Review priorities

Report only actionable issues that are introduced by the change or are directly
required for it to work:

1. Correctness and regressions in the YouTube link → context → agents → outputs
   workflow.
2. Security issues, including secret exposure, unsafe input handling, injection,
   authentication or authorization bypasses, and data leaks.
3. Reliability, error handling, concurrency, resource cleanup, and data loss.
4. API, SDK, database, and event-contract compatibility.
5. Tests or documentation that are necessary to keep the changed behavior
   verifiable.

Do not report formatting, naming, subjective style, or pre-existing issues
unless they make the proposed change incorrect or unsafe.

## Repository constraints

- Preserve the single workflow; do not introduce manual or alternate execution
  paths.
- Keep REAL_MODE_ONLY behavior intact; do not add fake delays, fabricated
  responses, or production mocks.
- Never suggest committing credentials or other secrets.
- Validate external input at system boundaries and use parameterized database
  operations.
- Keep backend response models and `sdk/python/eventrelay_sdk/types.py` aligned.
- Use `auJzb1D-fag` in test fixtures and never use the banned test video ID.
- Prefer focused tests and existing repository tooling over new dependencies.

## Review process

1. Establish the review base and inspect the full changed-file list.
2. Trace each changed path through its callers and consumers; check both success
   and failure paths.
3. Compare behavior with existing tests and conventions. Check migrations,
   generated or lock files, and CI configuration when relevant.
4. Run the narrowest relevant tests or checks when possible. Distinguish
   verified results from reasoning.
5. Report findings in descending severity. Each finding must include:
   - severity (`critical`, `high`, `medium`, or `low`);
   - exact file and line range;
   - the concrete failure and its impact;
   - a minimal remediation.

If no actionable findings remain, say so and summarize what was checked. Keep
review comments concise and do not invent problems to fill a quota.
