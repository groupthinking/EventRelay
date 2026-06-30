#!/bin/bash

# MCP Function Deployment Script
# This script helps deploy the MCP-compatible edge function to Supabase

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

# Navigate to project root first
cd /Users/garvey/Desktop/\ Framework-Guide-for-Cursor/

# Deploy function from the project root
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
echo "Test your function with:"
echo 'curl -X POST \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"modelId": "gpt-4", "context": {"operation": "connect", "parameters": {"foo": "bar"}}}'"'"' \'
echo '  https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp'
echo ""

# Remain in project root
cd /Users/garvey/Desktop/\ Framework-Guide-for-Cursor/