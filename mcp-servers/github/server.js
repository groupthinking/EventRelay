#!/usr/bin/env node

// This is a wrapper script for the GitHub MCP server
// It simply starts the server with the GitHub token provided in environment variables

// Make sure token is present
if (!process.env.GITHUB_PERSONAL_ACCESS_TOKEN) {
  console.error('Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable is not set');
  process.exit(1);
}

// Forward to the @modelcontextprotocol/server-github package
const serverPath = require.resolve('@modelcontextprotocol/server-github');
require(serverPath);

console.error('GitHub MCP server started successfully');
