#!/usr/bin/env bash
#
# branch-cleanup-delete.sh — archive-tag then delete branches per the assessment.
#
# Generated from docs/branch-cleanup-matrix.csv (2026-07-01 audit).
# Every branch is first tagged `archive/<branch>` (SHA recoverable indefinitely)
# and only then deleted from origin. Review the lists before running.
#
# NOTE: CLOSE-SAFE = the branch's PR is already closed/merged (GitHub preserves
# the ref) OR the tip carries zero unique work. Deleting these loses nothing.
# REVIEW = no open PR but still carries content or is a merged-PR remnant; glance
# before deleting.
#
# Usage:
#   scripts/maintenance/branch-cleanup-delete.sh safe             # delete CLOSE-SAFE branches
#   scripts/maintenance/branch-cleanup-delete.sh review           # delete REVIEW branches (after looking)
#   DRY_RUN=1 scripts/maintenance/branch-cleanup-delete.sh safe   # print actions only
#
# Recover any branch later with:
#   git push origin archive/<branch>:refs/heads/<branch>
#
set -uo pipefail
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

run() { if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY: $*"; else echo "+ $*"; "$@"; fi; }

archive_and_delete() {
  local b="$1"
  if ! git show-ref --verify --quiet "refs/remotes/origin/$b"; then
    echo "skip (no ref): $b"; return
  fi
  run git tag -f "archive/$b" "origin/$b"
  run git push origin "refs/tags/archive/$b"
  run git push origin --delete "$b"
}

case "${1:-}" in
  safe)   for b in "${SAFE_BRANCHES[@]}";   do archive_and_delete "$b"; done ;;
  review) for b in "${REVIEW_BRANCHES[@]}"; do archive_and_delete "$b"; done ;;
  *) echo "usage: $0 {safe|review}   (prefix DRY_RUN=1 to preview)"; exit 2 ;;
esac
