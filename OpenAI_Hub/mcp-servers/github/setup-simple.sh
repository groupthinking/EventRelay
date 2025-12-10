#!/bin/bash

# Simplified setup script for GitHub MCP server
# This script uses the custom implementation approach only

GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
SERVER_DIR="/Users/garvey/Documents/Cline/MCP/github"
MCP_SETTINGS_PATH="/Users/garvey/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"

echo "Setting up GitHub MCP server with simple script approach..."

# Set up the script
echo "Setting up custom GitHub MCP server script..."

# Create a merged settings file
echo "Creating merged settings file..."
TMP_FILE=$(mktemp)
cat "$MCP_SETTINGS_PATH" | sed '/"github.com\/modelcontextprotocol\/servers\/tree\/main\/src\/github": {/,/},/d' | sed 's/"mcpServers": {/"mcpServers": {\n    "github.com\/modelcontextprotocol\/servers\/tree\/main\/src\/github": {\n      "autoApprove": ["search_repositories", "get_repository"],\n      "disabled": false,\n      "timeout": 60,\n      "command": "node",\n      "args": [\n        "\/Users\/garvey\/Documents\/Cline\/MCP\/github\/simple-github-server.js"\n      ],\n      "env": {\n        "GITHUB_PERSONAL_ACCESS_TOKEN": "'"$GITHUB_TOKEN"'"\n      }\n    },/' > "$TMP_FILE"

# Output the merged settings
echo "Merged settings created. You can apply these settings by replacing your current settings file at:"
echo "$MCP_SETTINGS_PATH"
echo ""
echo "Here's the content of the merged settings:"
echo "-----------------------------------"
cat "$TMP_FILE"
echo "-----------------------------------"
echo ""
echo "To apply these settings, run:"
echo "cp \"$TMP_FILE\" \"$MCP_SETTINGS_PATH\""

# Check if the user wants to apply the settings automatically
read -p "Do you want to apply these settings automatically? (y/n): " APPLY_SETTINGS
if [[ "$APPLY_SETTINGS" == "y" ]]; then
  cp "$TMP_FILE" "$MCP_SETTINGS_PATH"
  echo "Settings applied successfully. Please restart any Cursor or Claude instances to load the new settings."
else
  echo "Settings not applied automatically. You can apply them manually with the command above."
fi

# Clean up
rm "$TMP_FILE"

echo "Setup complete."
