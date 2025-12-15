#!/bin/bash
# Llama Agent MCP Server Startup Script

echo "🔮 Starting Llama Agent MCP Server..."

# Set environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}"

# Start the MCP server
python3 mcp_servers/llama_agent_mcp_server.py
