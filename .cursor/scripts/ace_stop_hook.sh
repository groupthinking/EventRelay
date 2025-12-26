#!/bin/bash
# ACE Stop Hook - Aggregates AI-Trail trajectory with git context
# Input: status, loop_count

input=$(cat)
status=$(echo "$input" | jq -r '.status // empty')
loop_count=$(echo "$input" | jq -r '.loop_count // 0')

# Only process once on completed tasks
if [ "$status" = "completed" ] && [ "$loop_count" = "0" ]; then
  # Capture git context
  git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  git_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

  # Count trajectory entries
  ace_dir=".cursor/ace"
  mcp_count=$(wc -l < "$ace_dir/mcp_trajectory.jsonl" 2>/dev/null | tr -d ' ' || echo "0")
  shell_count=$(wc -l < "$ace_dir/shell_trajectory.jsonl" 2>/dev/null | tr -d ' ' || echo "0")
  edit_count=$(wc -l < "$ace_dir/edit_trajectory.jsonl" 2>/dev/null | tr -d ' ' || echo "0")
  response_count=$(wc -l < "$ace_dir/response_trajectory.jsonl" 2>/dev/null | tr -d ' ' || echo "0")

  # Build summary
  summary="MCP:$mcp_count Shell:$shell_count Edits:$edit_count Responses:$response_count"
  msg="Session complete. AI-Trail: $summary. Git: $git_branch ($git_hash). Call ace_learn to capture patterns."

  echo "{\"followup_message\": \"$msg\"}"
else
  echo '{}'
fi
