#!/bin/bash

# creative-studio Activation Script
echo "🚀 Activating creative-studio..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/creative-studio/status)

if [ $? -eq 0 ]; then
  echo "✅ creative-studio activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate creative-studio"
fi
