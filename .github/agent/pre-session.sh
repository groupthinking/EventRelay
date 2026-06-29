#!/bin/bash
# Pre-Session Script for EventRelay
# Location: .github/agent/pre-session.sh
# Purpose: Enforce Daily Commit Protocol from .memory-rules v2.0.0

set -e

SHARED_DIR="shared"
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)
CURRENT_DAY=$(date +%d)
YESTERDAY_DAY=$(date -v-1d +%d 2>/dev/null || date -d "yesterday" +%d)
YESTERDAY_MONTH=$(date -v-1d +%m 2>/dev/null || date -d "yesterday" +%m)
YESTERDAY_YEAR=$(date -v-1d +%Y 2>/dev/null || date -d "yesterday" +%Y)

TODAY_FOLDER="$SHARED_DIR/$CURRENT_YEAR-$CURRENT_MONTH/$CURRENT_DAY"
YESTERDAY_FOLDER="$SHARED_DIR/$YESTERDAY_YEAR-$YESTERDAY_MONTH/$YESTERDAY_DAY"

echo "=== EventRelay Pre-Session Check ==="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Check if yesterday's folder exists and has uncommitted changes
if [ -d "$YESTERDAY_FOLDER" ]; then
    UNCOMMITTED=$(git status --porcelain "$YESTERDAY_FOLDER" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo "[ACTION] Committing prior day's work: $YESTERDAY_FOLDER"
        git add "$YESTERDAY_FOLDER"
        git commit -m "docs: commit $YESTERDAY_YEAR-$YESTERDAY_MONTH-$YESTERDAY_DAY session logs"
    else
        echo "[OK] Prior day already committed: $YESTERDAY_FOLDER"
    fi
else
    echo "[INFO] No prior day folder found: $YESTERDAY_FOLDER"
fi

# Step 2: Create today's folder if it doesn't exist
if [ ! -d "$TODAY_FOLDER" ]; then
    echo "[ACTION] Creating today's folder: $TODAY_FOLDER"
    mkdir -p "$TODAY_FOLDER"
    echo "# Session Log - $CURRENT_YEAR-$CURRENT_MONTH-$CURRENT_DAY" > "$TODAY_FOLDER/CHANGELOG.md"
    echo "" >> "$TODAY_FOLDER/CHANGELOG.md"
    echo "## In Progress" >> "$TODAY_FOLDER/CHANGELOG.md"
    echo "" >> "$TODAY_FOLDER/CHANGELOG.md"
    echo "## Completed" >> "$TODAY_FOLDER/CHANGELOG.md"
    echo "" >> "$TODAY_FOLDER/CHANGELOG.md"
    echo "## Notes for Next Session" >> "$TODAY_FOLDER/CHANGELOG.md"
else
    echo "[OK] Today's folder exists: $TODAY_FOLDER"
fi

# Step 3: Show git status
echo ""
echo "=== Git Status ==="
git status --short

echo ""
echo "=== Pre-Session Complete ==="
