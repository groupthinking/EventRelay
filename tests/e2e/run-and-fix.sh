#!/usr/bin/env bash
#
# EventRelay E2E Test Runner — Red/Green Signal System
#
# Usage: ./tests/e2e/run-and-fix.sh [base_url]
#
# Runs the full E2E test suite against the specified deployment.
# Emits GREEN or RED signal. On RED, logs the failure to failure-log.md.
#
# Environment:
#   BASE_URL — deployment URL (default: https://uvai.io)
#   MAX_RETRIES — max retry attempts (default: 3)

set -euo pipefail

BASE_URL="${1:-${BASE_URL:-https://uvai.io}}"
MAX_RETRIES="${MAX_RETRIES:-3}"
FAILURE_LOG="tests/failure-log.md"
ATTEMPT=0

export BASE_URL

echo "╔══════════════════════════════════════════════════════╗"
echo "║  EventRelay E2E Test Runner                          ║"
echo "║  Target: $BASE_URL"
echo "║  Max retries: $MAX_RETRIES"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

while [ $ATTEMPT -lt $MAX_RETRIES ]; do
  ATTEMPT=$((ATTEMPT + 1))
  echo "━━━ Attempt $ATTEMPT/$MAX_RETRIES ━━━"
  echo ""

  # Run tests and capture output
  TEST_OUTPUT=$(mktemp)
  set +e
  npx vitest run tests/e2e/ --reporter=verbose 2>&1 | tee "$TEST_OUTPUT"
  EXIT_CODE=${PIPESTATUS[0]}
  set -e

  if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ✅ ALL TESTS PASSED                                 ║"
    echo "║  Deployment at $BASE_URL is healthy."
    echo "╚══════════════════════════════════════════════════════╝"
    rm -f "$TEST_OUTPUT"
    exit 0
  fi

  echo ""
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║  🔴 FAILURE DETECTED — Attempt $ATTEMPT/$MAX_RETRIES"
  echo "╚══════════════════════════════════════════════════════╝"

  # Extract failed test names
  FAILURES=$(grep -E 'FAIL|×|✕|AssertionError|Error:' "$TEST_OUTPUT" | head -20)
  DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

  # Log to failure-log.md
  cat >> "$FAILURE_LOG" << EOF

---

### 🔴 Failure — $DATE

**Attempt:** $ATTEMPT/$MAX_RETRIES
**Target:** $BASE_URL
**Runner:** Local (run-and-fix.sh)

**Failed tests:**
\`\`\`
$FAILURES
\`\`\`

**Status:** $([ $ATTEMPT -lt $MAX_RETRIES ] && echo "Retrying..." || echo "Max retries exhausted.")
EOF

  rm -f "$TEST_OUTPUT"

  if [ $ATTEMPT -lt $MAX_RETRIES ]; then
    echo ""
    echo "Waiting 10 seconds before retry..."
    sleep 10
  fi
done

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🔴 FAILURE — Max retries ($MAX_RETRIES) exhausted   ║"
echo "║  Manual investigation required.                      ║"
echo "╚══════════════════════════════════════════════════════╝"
exit 1
