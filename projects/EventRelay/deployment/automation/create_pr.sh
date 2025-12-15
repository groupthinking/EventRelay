#!/usr/bin/env bash
set -euo pipefail

BRANCH="automation/auto-issues-$(date +%s)"
git checkout -b "$BRANCH"
git add automation tools/collect_todos.py
git commit -m "chore(automation): add auto-issue summaries and todo collection report"

if command -v gh >/dev/null 2>&1; then
  echo "Creating PR with gh..."
  gh pr create --title "Automated: add security + triage artifacts" --body-file automation/PR_SUMMARY_auto_issues.md --base main --head "$BRANCH"
  echo "PR created (or opened as draft) — check your GitHub account"
else
  echo "gh CLI not found. Run these commands to push and open a PR manually:"
  echo "  git push -u origin $BRANCH"
  echo "  gh pr create --title \"Automated: add security + triage artifacts\" --body-file automation/PR_SUMMARY_auto_issues.md --base main --head $BRANCH"
fi
