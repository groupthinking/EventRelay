#!/bin/bash

# code-assistant Activation Script
echo "🚀 Activating code-assistant..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/code-assistant/status)

if [ $? -eq 0 ]; then
  echo "✅ code-assistant activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate code-assistant"
fi
