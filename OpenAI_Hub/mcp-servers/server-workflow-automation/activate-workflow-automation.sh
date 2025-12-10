#!/bin/bash

# workflow-automation Activation Script
echo "🚀 Activating workflow-automation..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/workflow-automation/status)

if [ $? -eq 0 ]; then
  echo "✅ workflow-automation activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate workflow-automation"
fi
