#!/bin/zsh
# grok_query.sh - Quick Grok API wrapper for your YouTube ext

if [ -z "$1" ]; then
  echo "Usage: ./grok_query.sh 'Your query here'"
  exit 1
fi

QUERY="$1"
MODEL="grok-4-fast-reasoning"  # Or swap to "grok-3" for balance

curl "https://api.x.ai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"$QUERY\"}], \"temperature\": 0.7}" | jq '.choices[0].message.content'  # Pretty-print just the reply (install jq if needed: brew install jq)
