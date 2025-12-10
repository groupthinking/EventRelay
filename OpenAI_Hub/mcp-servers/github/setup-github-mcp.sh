#!/bin/bash

# Script to set up GitHub MCP server
# This script tries multiple approaches to set up the server

GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
SERVER_DIR="/Users/garvey/Documents/Cline/MCP/github"
MCP_SETTINGS_PATH="/Users/garvey/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"

echo "Setting up GitHub MCP server..."

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "Docker is available, trying Docker approach..."
    
    # Build the Docker image
    cd "$SERVER_DIR"
    docker build -t mcp/github -f Dockerfile .
    
    if [ $? -eq 0 ]; then
        echo "Docker image built successfully"
        
        # Update MCP settings to use Docker
        cat > "$SERVER_DIR/docker-settings.json" << EOL
{
  "mcpServers": {
    "github.com/modelcontextprotocol/servers/tree/main/src/github": {
      "autoApprove": [
        "search_repositories",
        "get_repository"
      ],
      "disabled": false,
      "timeout": 60,
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}",
        "mcp/github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
EOL
        echo "Docker configuration created at $SERVER_DIR/docker-settings.json"
        echo "To apply this configuration, merge it with your existing MCP settings file"
        echo "Replace the github server entry in $MCP_SETTINGS_PATH"
    else
        echo "Failed to build Docker image"
    fi
else
    echo "Docker not available, trying NPX approach..."
    
    # Try to run npx directly
    echo "Testing npx with GitHub MCP server..."
    echo '{"jsonrpc":"2.0","id":1,"method":"list_tools","params":{}}' | GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}" npx -y @modelcontextprotocol/server-github
    
    if [ $? -eq 0 ]; then
        echo "NPX approach works!"
        
        # Update MCP settings to use NPX
        cat > "$SERVER_DIR/npx-settings.json" << EOL
{
  "mcpServers": {
    "github.com/modelcontextprotocol/servers/tree/main/src/github": {
      "autoApprove": [
        "search_repositories",
        "get_repository"
      ],
      "disabled": false,
      "timeout": 60,
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
EOL
        echo "NPX configuration created at $SERVER_DIR/npx-settings.json"
        echo "To apply this configuration, merge it with your existing MCP settings file"
        echo "Replace the github server entry in $MCP_SETTINGS_PATH"
    else
        echo "NPX approach failed"
        
        # Fallback to simple script approach
        echo "Falling back to simple script approach..."
        cp "$SERVER_DIR/simple-github-server.js" "$SERVER_DIR/github-mcp-server.js"
        chmod +x "$SERVER_DIR/github-mcp-server.js"
        
        # Update MCP settings to use the simple script
        cat > "$SERVER_DIR/script-settings.json" << EOL
{
  "mcpServers": {
    "github.com/modelcontextprotocol/servers/tree/main/src/github": {
      "autoApprove": [
        "search_repositories",
        "get_repository"
      ],
      "disabled": false,
      "timeout": 60,
      "command": "node",
      "args": [
        "${SERVER_DIR}/github-mcp-server.js"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
EOL
        echo "Simple script configuration created at $SERVER_DIR/script-settings.json"
        echo "To apply this configuration, merge it with your existing MCP settings file"
        echo "Replace the github server entry in $MCP_SETTINGS_PATH"
    fi
fi

echo "Setup complete. Please review the generated settings and update your MCP settings file accordingly."
