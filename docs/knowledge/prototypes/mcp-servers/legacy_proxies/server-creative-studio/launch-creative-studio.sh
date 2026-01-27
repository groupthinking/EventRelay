#!/bin/bash

# MCP creative-studio Launcher
echo "🚀 Launching creative-studio..."

# Set environment variables from configuration
export PATH="/Users/garvey/Desktop/mcp-bridge/system/registry/@modelcontextprotocol/server-creative-studio/node_modules/.bin:/Users/garvey/.npm/_npx/e54cca0e4081644e/node_modules/.bin:/node_modules/.bin:/Users/garvey/.nvm/versions/node/v22.8.0/lib/node_modules/npm/node_modules/@npmcli/run-script/lib/node-gyp-bin:/Users/garvey/.nvm/versions/node/v22.8.0/bin:/usr/local/bin:/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Launch service
npx @modelcontextprotocol/server-creative-studio --rendering-quality=professional --asset-management=integrated
