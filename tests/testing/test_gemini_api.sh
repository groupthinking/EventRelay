#!/bin/bash
# Test Gemini API connection
#
# The API key must come from the environment — never hardcode credentials.
# Export it before running, e.g.:
#   export GEMINI_API_KEY="<your key>"
set -euo pipefail

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY is not set. Export it before running this script." >&2
  exit 1
fi

echo "Testing Gemini API..."
# Report only that the key loaded (and its length) — never echo key material,
# since this script may run in CI where stdout is captured.
echo "API key loaded (${#GEMINI_API_KEY} chars)."
echo ""

# Capture the full response first, then truncate for display. Piping
# `... | python3 -m json.tool | head -30` directly would let `head` close the
# pipe after 30 lines, sending SIGPIPE (exit 141) to python3; under `pipefail`
# + `set -e` that aborts the script even on a successful API response.
response=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts": [{"text": "Respond with just SUCCESS if you receive this."}]
    }]
  }' | python3 -m json.tool)

head -30 <<< "$response"
