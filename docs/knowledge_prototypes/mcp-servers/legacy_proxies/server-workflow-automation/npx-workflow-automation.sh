#!/bin/bash

# MCP workflow-automation Launcher
echo "🚀 Launching @modelcontextprotocol/server-workflow-automation --trigger-complexity=advanced --cross-application=enabled"

# Configure environment
export PATH="/Users/garvey/Desktop/mcp-bridge/system/registry/@modelcontextprotocol/server-workflow-automation/node_modules/.bin:/Users/garvey/.npm/_npx/e54cca0e4081644e/node_modules/.bin:/node_modules/.bin:/Users/garvey/.nvm/versions/node/v22.8.0/lib/node_modules/npm/node_modules/@npmcli/run-script/lib/node-gyp-bin:/Users/garvey/.nvm/versions/node/v22.8.0/bin:/usr/local/bin:/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Execute service bridge
npx @modelcontextprotocol/server-workflow-automation --trigger-complexity=advanced --cross-application=enabled
