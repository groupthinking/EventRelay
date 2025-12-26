#!/bin/bash
# ACE Edit Tracking Hook - Captures file edits with domain detection
# Input: file_path, edits[]
# Writes domain state to temp file for MCP Resources (Issue #3 fix)

input=$(cat)
mkdir -p .cursor/ace
echo "$input" >> .cursor/ace/edit_trajectory.jsonl

# Domain detection function
detect_domain() {
  local file_path="$1"
  case "$file_path" in
    */auth/*|*login*|*session*|*jwt*) echo "auth" ;;
    */api/*|*routes*|*endpoint*|*controller*) echo "api" ;;
    */cache/*|*redis*|*memo*) echo "cache" ;;
    */db/*|*migration*|*model*|*schema*) echo "database" ;;
    */component*|*/ui/*|*/view*|*.tsx|*.jsx) echo "ui" ;;
    */test*|*spec*|*mock*) echo "test" ;;
    *) echo "general" ;;
  esac
}

# Extract file path from input JSON
file_path=$(echo "$input" | jq -r '.file_path // .path // empty' 2>/dev/null)

if [ -n "$file_path" ]; then
  current_domain=$(detect_domain "$file_path")
  last_domain=$(cat .cursor/ace/last_domain.txt 2>/dev/null || echo "")

  # Log domain transition if changed
  if [ "$current_domain" != "$last_domain" ] && [ -n "$last_domain" ]; then
    echo "{\"from\": \"$last_domain\", \"to\": \"$current_domain\", \"file\": \"$file_path\", \"timestamp\": \"$(date -Iseconds)\"}" >> .cursor/ace/domain_shifts.log
  fi

  echo "$current_domain" > .cursor/ace/last_domain.txt

  # Write domain state to temp file for MCP Resources
  # MCP server reads this to expose ace://domain/current resource
  # Uses $TMPDIR (macOS) with fallback to /tmp (Linux)
  project_id=$(jq -r '.projectId // "default"' .cursor/ace/settings.json 2>/dev/null || echo "default")
  hash=$(echo -n "$project_id" | md5sum | cut -c1-8)
  temp_dir="${TMPDIR:-/tmp}"
  temp_file="${temp_dir%/}/ace-domain-${hash}.json"
  echo "{\"domain\": \"$current_domain\", \"file\": \"$file_path\", \"timestamp\": \"$(date -Iseconds)\"}" > "$temp_file"
fi

exit 0
