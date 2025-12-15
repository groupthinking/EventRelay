#!/bin/bash

# MCP Master Launcher
echo "🚀 Launching MCP Service Suite"
echo "────────────────────────────"

WORK_DIR="$(dirname "$0")"

# Function to check if core server is running
function check_core_server {
  if curl -s http://localhost:51234/status > /dev/null; then
    echo "✅ Core server is running"
    return 0
  else
    echo "❌ Core server is not running"
    return 1
  fi
}

# Check core server status
if ! check_core_server; then
  echo "  → Starting core server..."
  "$WORK_DIR/../initialize-core.sh" > /dev/null
  
  # Verify core server started
  sleep 2
  if ! check_core_server; then
    echo "❌ Failed to start core server"
    exit 1
  fi
fi

# Launch all services in background
echo ""
echo "🚀 Launching services..."

# Create log directory
mkdir -p "$WORK_DIR/logs"

# Launch each service
for script in "$WORK_DIR"/launch-*.sh; do
  if [[ "$script" != *"launch-all.sh"* ]]; then
    SERVICE=$(basename "$script" | sed 's/launch-//g' | sed 's/.sh//g')
    echo "  → Starting $SERVICE"
    "$script" > "$WORK_DIR/logs/$SERVICE.log" 2>&1 &
    echo "    ✓ Started with PID $!"
  fi
done

echo ""
echo "✅ All services launched successfully"
echo "  → Service logs available at: $WORK_DIR/logs/"
echo ""
echo "To check system status, run:"
echo "  curl http://localhost:51234/status | python3 -m json.tool"
