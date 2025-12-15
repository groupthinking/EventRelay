#!/bin/bash

# knowledge-management Activation Script
echo "🚀 Activating knowledge-management..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/knowledge-management/status)

if [ $? -eq 0 ]; then
  echo "✅ knowledge-management activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate knowledge-management"
fi
