#!/bin/bash

# Setup Supabase MCP Integration
echo "Setting up Supabase MCP Integration..."

# Check if token is in environment, or prompt for it
if [ -z "$SUPABASE_ACCESS_TOKEN" ]; then
  echo "Supabase access token not found in environment."
  echo -n "Enter your Supabase access token (or press enter to use placeholder): "
  read TOKEN
  if [ -z "$TOKEN" ]; then
    TOKEN="YOUR_SUPABASE_ACCESS_TOKEN"
    echo "Using placeholder. You'll need to replace this later with your actual token."
  else
    echo "Using provided token."
    export SUPABASE_ACCESS_TOKEN="$TOKEN"
  fi
else
  echo "Using Supabase access token from environment."
  TOKEN="$SUPABASE_ACCESS_TOKEN"
fi

# Check if configuration directories exist, create if needed
mkdir -p .cursor
mkdir -p .vscode

# Create .cursor/mcp.json if it doesn't exist or update it
echo "Creating/updating .cursor/mcp.json file..."
cat > .cursor/mcp.json << EOL
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "${env:SUPABASE_ACCESS_TOKEN}"
      ]
    }
  }
}
EOL
echo ".cursor/mcp.json file created successfully!"

# Create .vscode/mcp.json if it doesn't exist or update it
echo "Creating/updating .vscode/mcp.json file..."
cat > .vscode/mcp.json << EOL
{
  "inputs": [
    {
      "type": "promptString",
      "id": "supabase-access-token",
      "description": "Supabase personal access token",
      "password": true
    }
  ],
  "servers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest"],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "\${input:supabase-access-token}"
      }
    }
  }
}
EOL
echo ".vscode/mcp.json file created successfully!"

# Create .mcp.json if it doesn't exist or update it
echo "Creating/updating .mcp.json file in project root..."
cat > .mcp.json << EOL
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "${env:SUPABASE_ACCESS_TOKEN}"
      ]
    }
  }
}
EOL
echo ".mcp.json file created successfully!"

# Set up environment variable for the current session
if [ "$TOKEN" != "YOUR_SUPABASE_ACCESS_TOKEN" ]; then
  # Add to shell profile if possible
  if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "export SUPABASE_ACCESS_TOKEN" "$HOME/.zshrc"; then
      echo "Adding SUPABASE_ACCESS_TOKEN to ~/.zshrc"
      echo "export SUPABASE_ACCESS_TOKEN=\"$TOKEN\"" >> "$HOME/.zshrc"
      echo "Added token to ~/.zshrc. You'll need to restart your terminal or run 'source ~/.zshrc'"
    fi
  elif [ -f "$HOME/.bash_profile" ]; then
    if ! grep -q "export SUPABASE_ACCESS_TOKEN" "$HOME/.bash_profile"; then
      echo "Adding SUPABASE_ACCESS_TOKEN to ~/.bash_profile"
      echo "export SUPABASE_ACCESS_TOKEN=\"$TOKEN\"" >> "$HOME/.bash_profile"
      echo "Added token to ~/.bash_profile. You'll need to restart your terminal or run 'source ~/.bash_profile'"
    fi
  elif [ -f "$HOME/.bashrc" ]; then
    if ! grep -q "export SUPABASE_ACCESS_TOKEN" "$HOME/.bashrc"; then
      echo "Adding SUPABASE_ACCESS_TOKEN to ~/.bashrc"
      echo "export SUPABASE_ACCESS_TOKEN=\"$TOKEN\"" >> "$HOME/.bashrc"
      echo "Added token to ~/.bashrc. You'll need to restart your terminal or run 'source ~/.bashrc'"
    fi
  else
    echo "Could not find a shell profile file to add the token to."
    echo "Please manually add 'export SUPABASE_ACCESS_TOKEN=\"$TOKEN\"' to your shell profile."
  fi
fi

# Verify the MCP server npm package is installed
echo "Checking if Supabase MCP server package is installed..."
if ! npx @supabase/mcp-server-supabase@latest --version &> /dev/null; then
  echo "Installing Supabase MCP server package..."
  npm install -g @supabase/mcp-server-supabase@latest
fi

echo ""
echo "-----------------------------------------------------------------"
echo "Supabase MCP Integration Setup Complete!"
echo "-----------------------------------------------------------------"
echo ""
echo "Configuration files have been created/updated:"
echo "- .cursor/mcp.json (for Cursor)"
echo "- .vscode/mcp.json (for VS Code/Copilot)"
echo "- .mcp.json (for Claude and other tools)"
echo ""
if [ "$TOKEN" == "YOUR_SUPABASE_ACCESS_TOKEN" ]; then
  echo "ACTION REQUIRED: Replace placeholders with your actual Supabase token"
  echo "You can get a personal access token from: https://supabase.com/dashboard/account/tokens"
  echo ""
  echo "To verify your setup, run:"
  echo "export SUPABASE_ACCESS_TOKEN=your_actual_token"
  echo "node test_supabase_mcp_connection.js"
else
  echo "To verify your setup, run:"
  echo "node test_supabase_mcp_connection.js"
fi
echo "-----------------------------------------------------------------" 