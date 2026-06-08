#!/bin/bash

# MCP Function Deployment Script
# This script helps deploy the MCP-compatible edge function to Supabase

# Resolve the repository root dynamically so this works on any machine / CI.
# Override by exporting DEPLOY_ROOT before running the script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/.." && pwd))}"

echo "=== MCP Function Deployment Script ==="
echo "This script will help you deploy the connect-to-cursor-mcp function to Supabase"
echo ""

# Step 1: Login to Supabase (if not already logged in)
echo "Step 1: Logging in to Supabase"
echo "You may need to follow browser prompts to authenticate"
supabase login

# Check login status
if [ $? -ne 0 ]; then
  echo "Login failed. Please try again."
  exit 1
fi

echo "Login successful!"
echo ""

# Step 2: Deploy the function
echo "Step 2: Deploying MCP-compatible edge function"

# Navigate to the repository root (resolved above).
cd "$DEPLOY_ROOT" || { echo "Could not cd to project root: $DEPLOY_ROOT"; exit 1; }

# Deploy function from the project root.
# IMPORTANT: do NOT pass --no-verify-jwt. JWT verification must stay enabled so
# the function rejects anonymous requests (verify_jwt = true is also pinned in
# supabase/config.toml, and the function re-validates the token in code).
echo "Deploying from: $(pwd)"
supabase functions deploy connect-to-cursor-mcp

# Check deployment status
if [ $? -ne 0 ]; then
  echo "Deployment failed. Please check the error messages above."
  exit 1
fi

echo ""
echo "=== Deployment Successful! ==="
echo "Your MCP-compatible function is now live at:"
echo "https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp"
echo ""
echo "Test your function with (a valid Supabase user JWT is required):"
echo 'curl -X POST \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "Authorization: Bearer $SUPABASE_USER_JWT" \'
echo '  -d '"'"'{"modelId": "gpt-4", "context": {"operation": "connect", "parameters": {"foo": "bar"}}}'"'"' \'
echo '  https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp'
echo ""

# Remain in the repository root
cd "$DEPLOY_ROOT" || exit 1 