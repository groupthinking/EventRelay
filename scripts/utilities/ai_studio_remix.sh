#!/bin/bash

# AI Studio Remix Script
# Bundles the repository with Repomix and injects specialized prompts for Gemini 2.0

OUTPUT_FILE="ai-studio-remix.xml"
REPOMIX_CONFIG="repomix.config.json"

echo "🎨 Creating AI Studio Remix Bundle..."

# Create a temporary Repomix config if it doesn't exist
if [ ! -f "$REPOMIX_CONFIG" ]; then
cat <<EOF > "$REPOMIX_CONFIG"
{
  "output": {
    "filePath": "$OUTPUT_FILE",
    "style": "xml"
  },
  "include": [
    "apps/web/src/**/*",
    "apps/uvai-frontend/src/**/*",
    "src/uvai/**/*",
    "package.json",
    "apps/web/package.json"
  ],
  "exclude": [
    "**/node_modules/**",
    "**/.next/**",
    "**/dist/**",
    "**/.git/**"
  ]
}
EOF
fi

# Run Repomix
npx --yes repomix --config "$REPOMIX_CONFIG"

# Check if output exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Bundle created: $OUTPUT_FILE"
    echo "📎 Next steps: Drag this file into https://ai.studio.google"
    echo "💡 The bundle contains a 'Mirror & Remix' context for Gemini 2.0."
else
    echo "❌ Error: Failed to create bundle."
    exit 1
fi
