#!/usr/bin/env bash
#
# branch-cleanup-delete.sh — archive-tag then delete branches per the assessment.
#
# Generated from docs/branch-cleanup-matrix.csv. Every branch is first tagged
# `archive/<branch>` (so its SHA is recoverable indefinitely) and only then
# deleted from origin. Review the lists before running.
#
# Usage:
#   scripts/maintenance/branch-cleanup-delete.sh safe     # delete the 28 CLOSE-SAFE branches
#   scripts/maintenance/branch-cleanup-delete.sh stale    # delete the 30 CLOSE-STALE branches
#   scripts/maintenance/branch-cleanup-delete.sh review   # delete the 3 REVIEW branches (after you've looked)
#   DRY_RUN=1 scripts/maintenance/branch-cleanup-delete.sh safe   # print actions only
#
set -uo pipefail
SAFE_BRANCHES=(
  "claude/fix-action-step-error"
  "claude/fix-code-generator-output-again"
  "claude/fix-code-generator-unique-output"
  "claude/model-enum-sdk-followups"
  "codex/phase-3-async-video-routing"
  "copilot/delete-unnecessary-action"
  "copilot/fix-agent-pipeline-issues"
  "copilot/fix-dependency-review-action-inputs"
  "copilot/fix-nextjs-dos-vulnerability"
  "copilot/ghsa-8h8q-6873-q5fj-patch-nextjs"
  "copilot/security-bump-next-patched-version"
  "fix/database-cleanup-sqli-8169832145558809896"
  "fix/secure-cors-code-gen-250672599973076040"
  "fix/sql-injection-database-cleanup-18129828169216058434"
  "jules-13171754861581372920-22d7900e"
  "jules-14956868518633406482-f4fcdef0"
  "jules-security-cors-fix-10738780459144826270"
  "optimize-github-deployment-5034492779168511499"
  "v0/groupthinking-c47a0d1f"
  "v0/page-changes-dc7539d3"
  "v0/producer-ai-clone-5c5cde0f"
  "v0/ultrathinking-16d686fb"
  "v0/ultrathinking-2f38fe5f"
  "v0/ultrathinking-88584400"
  "v0/ultrathinking-b4b57996"
  "v0/ultrathinking-df8a2787"
  "v0/ultrathinking-e1f6bbf3"
  "v0/ultrathinking-f5c094d0"
)
STALE_BRANCHES=(
  "add-observability-tests-6699426491412081943"
  "claude/evaluate-transition-to-vertex-ai"
  "claude/fix-code-generator-output"
  "claude/fix-identical-vanilla-template"
  "claude/integrate-stainless-sdk"
  "claude/slack-check-status-update-R47Ph"
  "codex/consolidate-deployed-frontends"
  "codex/create-gtm-production-plan"
  "codex/fix-identical-vanilla-template"
  "codex/integrate-stainless-sdk-api-client"
  "codex/merge-scattered-mcp-repos"
  "copilot/fix-code-generator-output"
  "copilot/fix-code-generator-template-issue"
  "copilot/fix-typo-in-documentation"
  "copilot/handle-long-video-timeout"
  "copilot/merge-mcp-repositories"
  "fix-unused-import-cloud-ai-15137397722487778698"
  "fix/audit-issues"
  "salvage/youtube-extension-port"
  "test-video-utils-edge-cases-4459148101848315985"
  "v0/groupthinking-2a07c3a7"
  "v0/groupthinking-332b31e5"
  "v0/groupthinking-651a70af"
  "v0/groupthinking-86bedbf8"
  "v0/groupthinking-9b1b1e32"
  "v0/groupthinking-aed70cab"
  "v0/groupthinking-c6a57764"
  "v0/ultrathinking-3955abcc"
  "v0/ultrathinking-8d8eeaa8"
  "v0/ultrathinking-9af1709d"
)
REVIEW_BRANCHES=(
  "copilot/improve-documentation"
  "fix/unified-ai-sdk-real-providers-154"
  "v0/ai-system-architecture-ac4e7c39"
)

case "${1:-}" in
  safe)   sel=("${SAFE_BRANCHES[@]}") ;;
  stale)  sel=("${STALE_BRANCHES[@]}") ;;
  review) sel=("${REVIEW_BRANCHES[@]}") ;;
  *) echo "usage: $0 {safe|stale|review}   (DRY_RUN=1 to preview)"; exit 2 ;;
esac

echo "Batch '$1': ${#sel[@]} branches"
for b in "${sel[@]}"; do
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "  [dry-run] git tag archive/$b origin/$b && git push origin refs/tags/archive/$b && git push origin --delete $b"
    continue
  fi
  echo "==> $b"
  git tag -f "archive/$b" "origin/$b" 2>/dev/null
  git push origin "refs/tags/archive/$b" 2>/dev/null
  git push origin --delete "$b"
done
echo "Done. Recover any branch with:  git push origin archive/<branch>:refs/heads/<branch>"
