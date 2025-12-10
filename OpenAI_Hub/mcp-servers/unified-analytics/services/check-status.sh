#!/bin/bash

# MCP System Status Checker
echo "🔄 MCP System Status"
echo "────────────────────"

# Check core server
echo "Core Server: "
CORE_RESPONSE=$(curl -s http://localhost:51234/status)

if [ $? -eq 0 ]; then
  echo "  ✅ MCP Core Server: Active"
  echo "$CORE_RESPONSE" | python3 -m json.tool
else
  echo "  ❌ MCP Core Server: Not responding"
fi

echo ""
echo "Services:"
echo "─────────"

# Check each service
SERVICES=(
  "code-assistant"
  "data-analysis"
  "workflow-automation"
  "knowledge-management"
  "communication-hub"
  "creative-studio"
)

for SERVICE in "${SERVICES[@]}"; do
  SERVICE_RESPONSE=$(curl -s http://localhost:51234/service/$SERVICE/status)
  
  if [ $? -eq 0 ]; then
    echo "  ✅ $SERVICE: Active"
  else
    echo "  ❌ $SERVICE: Not responding"
  fi
done

echo ""
echo "System ready for MCP operations"
