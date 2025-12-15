#!/bin/bash

# Create Production Preparation Issues for EventRelay
# This script creates GitHub issues for all 3 phases of production preparation

set -e

# Detect repository name (owner/repo) from git remote or allow override
if [ -n "$REPO" ]; then
    # Use REPO from environment variable
    echo "ℹ️ Using repository from REPO environment variable: $REPO"
else
    # Try to detect from gh CLI
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
    if [ -z "$REPO" ]; then
        # Fallback: try to parse from git remote
        REPO=$(git remote get-url origin 2>/dev/null | sed -n 's#.*github.com[:/]\([^/]\+\)/\([^/.]\+\).*#\1/\2#p')
    fi
    if [ -z "$REPO" ]; then
        # Final fallback: use hard-coded value
        REPO="groupthinking/EventRelay"
        echo "⚠️ Could not auto-detect repository, using default: $REPO"
    else
        echo "ℹ️ Detected repository: $REPO"
    fi
fi
TEMPLATE_DIR=".github/ISSUE_TEMPLATE"
echo "🚀 Creating Production Preparation Issues for EventRelay"
echo "========================================================="
echo ""

# Check if gh CLI is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "📦 Install it from: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub"
    echo "🔐 Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"
echo ""

# Function to create issue
create_issue() {
    local phase=$1
    local title=$2
    local template=$3
    local labels=$4
    
    echo "📝 Creating $phase issue..."
    
    issue_url=$(gh issue create \
        --repo "$REPO" \
        --title "$title" \
        --body-file "$TEMPLATE_DIR/$template" \
        --label "$labels")
    
    if [ $? -eq 0 ]; then
        echo "✅ $phase issue created: $issue_url"
    else
        echo "❌ Failed to create $phase issue"
        return 1
    fi
    
    echo ""
}

# Create Phase 1 issue
create_issue \
    "Phase 1" \
    "[Phase 1] Security & Environment Setup" \
    "phase-1-security-environment.md" \
    "production,security,phase-1,high-priority"

# Create Phase 2 issue
create_issue \
    "Phase 2" \
    "[Phase 2] Monitoring & CI/CD Setup" \
    "phase-2-monitoring-cicd.md" \
    "production,monitoring,ci-cd,phase-2,high-priority"

# Create Phase 3 issue
create_issue \
    "Phase 3" \
    "[Phase 3] Testing & Production Launch" \
    "phase-3-testing-launch.md" \
    "production,testing,phase-3,deployment"

echo "========================================================="
echo "✅ All production preparation issues created successfully!"
echo ""
echo "📊 Next steps:"
echo "   1. Review each issue for detailed tasks"
echo "   2. Start with Phase 1 (Security & Environment)"
echo "   3. Complete phases sequentially (1 → 2 → 3)"
echo "   4. Track progress in GitHub Issues"
echo ""
echo "📚 Documentation: .github/ISSUE_TEMPLATE/README.md"
echo "🔗 View issues: https://github.com/$REPO/issues"
echo ""
echo "🎯 Target: Production-ready in 2-3 days (24 hours work)"
echo "========================================================="
# Script to create GitHub issues for all 3 production phases

set -e

REPO="groupthinking/EventRelay"
ISSUE_DIR=".github/ISSUE_TEMPLATE"

echo "🚀 Creating Production Phase Issues for EventRelay"
echo "=================================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed."
    echo "   Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI."
    echo "   Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Create Phase 1 Issue
echo "📝 Creating Phase 1: Security & Environment Setup..."
PHASE1_BODY=$(cat "$ISSUE_DIR/phase-1-security-environment.md" | tail -n +7)
PHASE1_ISSUE=$(gh issue create \
    --repo "$REPO" \
    --title "[PHASE 1] Security & Environment Setup" \
    --body "$PHASE1_BODY" \
    --label "phase-1,security,environment,production")
echo "   ✅ Created: $PHASE1_ISSUE"
PHASE1_NUMBER=$(echo "$PHASE1_ISSUE" | grep -o '[0-9]*$')
echo ""

# Create Phase 2 Issue
echo "📝 Creating Phase 2: Monitoring & CI/CD Setup..."
PHASE2_BODY=$(cat "$ISSUE_DIR/phase-2-monitoring-cicd.md" | tail -n +7)
PHASE2_ISSUE=$(gh issue create \
    --repo "$REPO" \
    --title "[PHASE 2] Monitoring & CI/CD Setup" \
    --body "$PHASE2_BODY" \
    --label "phase-2,monitoring,cicd,infrastructure")
echo "   ✅ Created: $PHASE2_ISSUE"
PHASE2_NUMBER=$(echo "$PHASE2_ISSUE" | grep -o '[0-9]*$')
echo ""

# Create Phase 3 Issue
echo "📝 Creating Phase 3: Testing & Production Launch..."
PHASE3_BODY=$(cat "$ISSUE_DIR/phase-3-testing-launch.md" | tail -n +7)
PHASE3_ISSUE=$(gh issue create \
    --repo "$REPO" \
    --title "[PHASE 3] Testing & Production Launch" \
    --body "$PHASE3_BODY" \
    --label "phase-3,testing,production,launch")
echo "   ✅ Created: $PHASE3_ISSUE"
PHASE3_NUMBER=$(echo "$PHASE3_ISSUE" | grep -o '[0-9]*$')
echo ""

echo "=================================================="
echo "✅ All production phase issues created successfully!"
echo ""
echo "📋 Issue Summary:"
echo "   Phase 1 (Security & Environment): #$PHASE1_NUMBER"
echo "   Phase 2 (Monitoring & CI/CD):     #$PHASE2_NUMBER"
echo "   Phase 3 (Testing & Launch):       #$PHASE3_NUMBER"
echo ""
echo "🚀 Next Steps:"
echo "   1. Start with Phase 1: gh issue view $PHASE1_NUMBER --web"
echo "   2. Follow the getting started commands in each issue"
echo "   3. Mark tasks as complete using the checkboxes"
echo "   4. Move to next phase after completing all tasks"
echo ""
echo "💡 Tip: Assign issues to team members with:"
echo "   gh issue edit <issue-number> --add-assignee <username>"
echo ""
