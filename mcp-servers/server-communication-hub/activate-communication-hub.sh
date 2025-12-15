#!/bin/bash

# communication-hub Activation Script
echo "🚀 Activating communication-hub..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/communication-hub/status)

if [ $? -eq 0 ]; then
  echo "✅ communication-hub activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate communication-hub"
fi
