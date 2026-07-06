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
echo "API Key: ${GEMINI_API_KEY:0:15}..."
echo ""

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [{
      "parts": [{"text": "Respond with just SUCCESS if you receive this."}]
    }]
  }' | python3 -m json.tool | head -30
