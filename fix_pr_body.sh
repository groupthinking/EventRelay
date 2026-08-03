#!/bin/bash
git commit --amend -m "🛡️ Sentinel: [MEDIUM] Prevent Information Disclosure in API Error Responses

## Canonical issue
Closes #1281

## Outcome
Prevents internal application states, stack traces, or external service errors from being directly exposed to clients. This reduces information leakage in the Next.js API routes by utilizing a standardized \`formatApiError()\` sanitizer, making reconnaissance or targeted attacks more difficult.

## Risk
- Risk level: low
- Failure mode: Legitimate clients receiving sanitized error messages instead of actionable messages if the sanitizer is too aggressive.
- Rollback: Revert the commit and use previous generic error mapping.

## Verification
- [x] Focused tests
- [x] Required CI
- [x] Review threads resolved

Tests passing in CI verify that \`error-handling-stack-safety.test.ts\` protects the boundaries and that mocked route logic (like testing HTTP status 504 on timeouts or checking \`isClientError\` parsing strings) are not broken.

## Production evidence
N/A - security enforcement logic checked by static testing on CI.
"
