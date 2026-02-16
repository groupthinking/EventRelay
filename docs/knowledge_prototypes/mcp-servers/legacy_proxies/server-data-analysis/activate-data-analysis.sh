#!/bin/bash

# data-analysis Activation Script
echo "🚀 Activating data-analysis..."

# Send activation request to server
RESPONSE=$(curl -s -X GET http://localhost:51234/service/data-analysis/status)

if [ $? -eq 0 ]; then
  echo "✅ data-analysis activated successfully"
  echo "$RESPONSE" | python3 -m json.tool
else
  echo "❌ Failed to activate data-analysis"
fi
