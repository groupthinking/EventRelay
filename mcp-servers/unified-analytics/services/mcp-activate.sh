#!/bin/bash

# MCP Master Activation Script
echo "🚀 MCP System Activation"
echo "─────────────────────────"

# Set environment variables
export MCP_ROOT="$(dirname "$0")"
export MCP_BIN="$MCP_ROOT/bin"
export MCP_LAUNCHERS="$MCP_ROOT/launchers"
export MCP_LOGS="$MCP_ROOT/logs"

# Step 1: Set up core bridge system
echo "📡 Initializing core bridge system..."
node "$MCP_BIN/mcp-bridge.js" setup

# Step 2: Set up npm bridge
echo "📦 Configuring npm integration..."
node "$MCP_BIN/setup-npm-bridge.js"

# Step 3: Create path shims
echo "🔄 Creating command shims..."

# Create shims directory
SHIMS_DIR="$MCP_ROOT/shims"
mkdir -p "$SHIMS_DIR"

# Create shim script
cat > "$SHIMS_DIR/install-shims.sh" << 'EOD'
#!/bin/bash

# MCP Command Shims Installer
echo "🔄 Installing MCP command shims..."

# Get source directory
SHIMS_SRC="$(dirname "$0")"
MCP_ROOT="$(dirname "$SHIMS_SRC")"

# Create bin directory in user's home if it doesn't exist
USER_BIN="$HOME/bin"
mkdir -p "$USER_BIN"

# Check if USER_BIN is in PATH
if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
  echo "⚠️ $USER_BIN is not in your PATH"
  echo "Add the following to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
  echo "export PATH=\"$USER_BIN:\$PATH\""
fi

# Create shims for all MCP commands
for SERVICE in code-assistant data-analysis workflow-automation knowledge-management communication-hub creative-studio; do
  # Create shim script
  cat > "$USER_BIN/mcp-$SERVICE" << EOF
#!/bin/bash

# MCP $SERVICE Shim
# Forwards commands to MCP bridge system

# Execute through bridge
"$MCP_ROOT/launchers/$SERVICE" "\$@"
