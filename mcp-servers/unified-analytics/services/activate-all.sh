#!/bin/bash

# MCP Master Activation Script
echo "🚀 Activating all MCP services..."

WORK_DIR="$(dirname "$0")"
SERVICES_DIR="$WORK_DIR/services"

# Activate each service
for script in "$SERVICES_DIR"/activate-*.sh; do
  SERVICE=$(basename "$script" | sed 's/activate-//g' | sed 's/.sh//g')
  echo ""
  echo "┌─────────────────────────────────┐"
  echo "│ Activating $SERVICE"
  echo "└─────────────────────────────────┘"
  
  "$script"
done

echo ""
echo "✅ All MCP services activated"
echo ""
echo "To verify system status, run: $WORK_DIR/check-status.sh"
