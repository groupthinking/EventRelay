#!/bin/bash
# Cleanup script for EventRelay repository
# Removes pointless files and fixes outdated references

set -e  # Exit on error

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🧹 EventRelay Repository Cleanup"
echo "================================="
echo ""

# Function to ask for confirmation
confirm() {
    read -p "$1 (y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# 1. Handle massive log files
echo "📋 Step 1: Cleaning up log files"
echo "--------------------------------"
if [ -f "autonomous_processing.log" ]; then
    SIZE=$(du -h autonomous_processing.log | cut -f1)
    echo "Found autonomous_processing.log ($SIZE)"
    if confirm "  Delete autonomous_processing.log?"; then
        rm autonomous_processing.log
        echo "  ✅ Deleted autonomous_processing.log"
    fi
fi

if [ -f "backend.log" ]; then
    SIZE=$(du -h backend.log | cut -f1)
    echo "Found backend.log ($SIZE)"
    if confirm "  Delete backend.log?"; then
        rm backend.log
        echo "  ✅ Deleted backend.log"
    fi
fi

# Clean up empty log files
for logfile in gemini_master_agent.log multi_llm_processor.log youtube_extension_api.log; do
    if [ -f "$logfile" ] && [ ! -s "$logfile" ]; then
        echo "  Removing empty log file: $logfile"
        rm "$logfile"
        echo "  ✅ Deleted $logfile"
    fi
done

echo ""

# 2. Update .gitignore
echo "📝 Step 2: Updating .gitignore"
echo "--------------------------------"
if ! grep -q "^# Generated logs" .gitignore 2>/dev/null; then
    echo "Adding log file patterns to .gitignore..."
    cat >> .gitignore << 'EOF'

# Generated logs
*.log
!.gitkeep
autonomous_processing_report_*.json

# Database files (unless tracked intentionally)
performance_monitoring.db
*.db-journal
*.db-wal
EOF
    echo "✅ Updated .gitignore"
else
    echo "⏭️  .gitignore already has log patterns"
fi

echo ""

# 3. Fix repomix.config.json
echo "🔧 Step 3: Fixing repomix.config.json"
echo "-------------------------------------"
if [ -f "repomix.config.json" ]; then
    if grep -q "uvai-frontend" repomix.config.json; then
        echo "Removing uvai-frontend reference from repomix.config.json..."
        # Use sed to remove the line (macOS compatible)
        sed -i.bak '/uvai-frontend/d' repomix.config.json
        rm repomix.config.json.bak
        echo "✅ Updated repomix.config.json"
    else
        echo "⏭️  repomix.config.json already clean"
    fi
fi

echo ""

# 4. Regenerate package-lock.json
echo "📦 Step 4: Regenerating package-lock.json"
echo "-----------------------------------------"
if confirm "  Run 'npm install' to regenerate package-lock.json?"; then
    npm install
    echo "✅ Regenerated package-lock.json"
else
    echo "⏭️  Skipped package-lock.json regeneration"
fi

echo ""

# 5. Report on other files
echo "📊 Step 5: File status report"
echo "------------------------------"

if [ -f "ai-studio-remix.xml" ]; then
    SIZE=$(du -h ai-studio-remix.xml | cut -f1)
    echo "⚠️  ai-studio-remix.xml exists ($SIZE) - verify if needed"
fi

if [ -f "performance_monitoring.db" ]; then
    SIZE=$(du -h performance_monitoring.db | cut -f1)
    echo "⚠️  performance_monitoring.db exists ($SIZE) - verify if needed"
fi

echo ""
echo "✨ Cleanup complete!"
echo ""
echo "⚠️  Manual steps remaining:"
echo "  1. Update package.json scripts (frontend -> apps/web)"
echo "  2. Review docs/guides/PRODUCTION_DEPLOYMENT_GUIDE.md for uvai-frontend references"
echo "  3. Verify ai-studio-remix.xml and performance_monitoring.db are needed"
echo ""
