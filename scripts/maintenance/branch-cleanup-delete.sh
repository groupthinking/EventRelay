#!/usr/bin/env bash
#
# branch-cleanup-delete.sh — preview branches from the cleanup assessment.
#
# Generated from docs/branch-cleanup-matrix.csv (2026-07-01 audit).
# Destructive execution is disabled because the current branch lists no longer
# have a fail-closed live open-PR guard or recovery-SHA ledger. Review the list
# before restoring those protections in a separately reviewed change.
#
# NOTE: the labels below are historical assessment results, not current safety
# decisions. Re-check every branch and open PR before any future deletion tool.
#
# Usage:
#   scripts/maintenance/branch-cleanup-delete.sh safe     # preview CLOSE-SAFE branches
#   scripts/maintenance/branch-cleanup-delete.sh review   # preview REVIEW branches
#
set -euo pipefail

if [ "${DRY_RUN:-1}" != "1" ]; then
  echo "Destructive branch cleanup is disabled: restore and test the live open-PR guard and recovery ledger first." >&2
  exit 3
fi
readonly DRY_RUN=1
SAFE_BRANCHES=(
  "chore/docs-audit-reports"
  "claude/capabilities-audit-52xql7"
  "claude/dazzling-edison-0468aj"
  "claude/dazzling-edison-06kjqd"
  "claude/dazzling-edison-1lbv9a"
  "claude/dazzling-edison-47c5po"
  "claude/dazzling-edison-4aiu6o"
  "claude/dazzling-edison-5kw3xm"
  "claude/dazzling-edison-5uxyqn"
  "claude/dazzling-edison-5wps75"
  "claude/dazzling-edison-95u1m4"
  "claude/dazzling-edison-bhkmhg"
  "claude/dazzling-edison-emn6e2"
  "claude/dazzling-edison-g5dftr"
  "claude/dazzling-edison-gcfkkw"
  "claude/dazzling-edison-hoefgl"
  "claude/dazzling-edison-k7x14i"
  "claude/dazzling-edison-ntgy52"
  "claude/dazzling-edison-pap026"
  "claude/dazzling-edison-w5yvz0"
  "claude/dazzling-edison-wquuan"
  "claude/dazzling-edison-ymkr67"
  "claude/determined-maxwell-nb1zz3"
  "claude/explore-codebase-implementation-plan"
  "claude/repo-architecture-review-Aewa3"
  "copilot/find-uvai-projects-and-test-repos"
  "copilot/loop-build-next-item-on-plan"
  "feat/sentry-nextjs"
  "feat/vera-platform"
  "fix/ralph-max-unclosed-demo-verification"
  "fix/transcript-action-graceful-errors"
  "fix/video-processor-pipeline-stubs"
  "ralph-max-final2"
  "ralph-max-final3"
  "ralph-max-final4"
  "v0/ultrathinking-2b862801"
  "v0/ultrathinking-48361bf4"
  "v0/ultrathinking-6aaf1beb-2"
)

REVIEW_BRANCHES=(
  "claude/create-markdown-mermaid"
  "claude/help-github-docs-page"
  "claude/review-session-history-tips"
  "code-health/remove-commented-code-main-py-9476992181961570048"
  "codex/uvai-studio-realtime"
  "copilot/explore-codebase-implementation-plan"
  "copilot/list-latest-open-pull-requests"
  "jules-7975870365122853693-d93780a1"
  "v0/ultrathinking-588aba59"
  "v0/ultrathinking-6aaf1beb"
  "v0/ultrathinking-8ff3a2ce"
)

preview_branch() {
  local b="$1"
  if ! git show-ref --verify --quiet "refs/remotes/origin/$b"; then
    echo "skip (no ref): $b"; return
  fi
  local sha
  sha=$(git rev-parse "origin/$b")
  echo "preview: $sha  $b"
}

case "${1:-}" in
  safe)   for b in "${SAFE_BRANCHES[@]}";   do preview_branch "$b"; done ;;
  review) for b in "${REVIEW_BRANCHES[@]}"; do preview_branch "$b"; done ;;
  *) echo "usage: $0 {safe|review}"; exit 2 ;;
esac
