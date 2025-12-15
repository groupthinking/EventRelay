#!/bin/bash

# Fly.io Deployment Script for YouTube Extension Backend
# Usage: ./deploy-fly.sh

set -e

echo "🚀 DEPLOYING TO FLY.IO"
echo "========================"

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged in to Fly.io
if ! fly auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io. Please run:"
    echo "   fly auth login"
    exit 1
fi

echo "✅ Fly CLI ready"

# Create app if it doesn't exist
if ! fly apps list | grep -q "youtube-extension-api"; then
    echo "📱 Creating Fly.io app..."
    fly apps create youtube-extension-api --org personal
else
    echo "✅ App already exists"
fi

# Create volume for persistent data
if ! fly volumes list | grep -q "youtube_extension_data"; then
    echo "💾 Creating persistent volume..."
    fly volumes create youtube_extension_data --size 1 --region iad
else
    echo "✅ Volume already exists"
fi

# Set environment variables
echo "🔧 Setting environment variables..."
fly secrets set \
    YOUTUBE_API_KEY="$YOUTUBE_API_KEY" \
    GEMINI_API_KEY="$GEMINI_API_KEY" \
    XAI_GROK4_API="$XAI_GROK4_API" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    ASSEMBLYAI_API_KEY="$ASSEMBLYAI_API_KEY"

# Deploy the application
echo "🚀 Deploying application..."
fly deploy

# Check deployment status
echo "📊 Checking deployment status..."
fly status

echo "✅ Deployment complete!"
echo "🌐 Your app is available at: https://youtube-extension-api.fly.dev"
echo "📊 Monitor at: https://fly.io/apps/youtube-extension-api"
