#!/bin/bash
set -e

# EventRelay Repository Cleanup Script
# Removes bloat, duplicates, and confusion-causing files

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN="${1:-dry-run}"  # Default to dry-run, pass "execute" to actually delete

cd "$REPO_ROOT"

echo "════════════════════════════════════════"
echo "EventRelay Repository Cleanup"
echo "Mode: $DRY_RUN"
echo "════════════════════════════════════════"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

delete_file() {
    local file="$1"
    local reason="$2"

    if [ -e "$file" ]; then
        local size=$(du -sh "$file" 2>/dev/null | cut -f1)
        echo -e "${YELLOW}[DELETE]${NC} $file ${RED}($size)${NC} — $reason"

        if [ "$DRY_RUN" = "execute" ]; then
            rm -rf "$file"
            echo -e "  ${GREEN}✓ Deleted${NC}"
        fi
    fi
}

echo "─────────────────────────────────────────"
echo "1. MASSIVE LOG FILES (826MB+ total)"
echo "─────────────────────────────────────────"
delete_file "autonomous_processing.log" "Massive 826MB log file"
delete_file "backend.log" "11MB backend log"
delete_file "gemini_master_agent.log" "Agent log file"
delete_file "multi_llm_processor.log" "LLM processor log"
delete_file "youtube_extension_api.log" "API log file"

echo ""
echo "─────────────────────────────────────────"
echo "2. OUTDATED/DUPLICATE DOCUMENTATION"
echo "─────────────────────────────────────────"
delete_file "docs/FRONTEND_AUDIT.md" "Outdated audit report"
delete_file "docs/BACKEND_VERIFICATION_REPORT.md" "Outdated verification"
delete_file "docs/YOLO_STATUS_REPORT.md" "Outdated status report"
delete_file "docs/USER_PERSONAS_TESTING_REPORT.md" "Outdated testing report"
delete_file "docs/VIBEVOICE_EVALUATION.md" "Wrong tool evaluation (TTS not STT)"
delete_file "docs/ADVERTISING_COPY.md" "Marketing content in dev repo"
delete_file "docs/GTM_STRATEGY.md" "Marketing strategy in dev repo"
delete_file "docs/COMPETITIVE_ANALYSIS.md" "Business doc in dev repo"
delete_file "docs/DOCUMENTATION_GAPS.md" "Meta-documentation"
delete_file "docs/API_QUICK_REFERENCE.md" "Duplicate of API_REFERENCE.md"
delete_file "docs/deployment/CLOUD_RUN_QUICKSTART.md" "Duplicate of CLOUD_RUN_DEPLOYMENT.md"

echo ""
echo "─────────────────────────────────────────"
echo "3. EXPERIMENTAL/BLOAT CODE"
echo "─────────────────────────────────────────"
delete_file "docs/analysis/ai_ops_skill_mesh_kit" "Experimental AI ops code (12 files)"
delete_file "docs/analysis/ai.google.dev_api.2025-09-20T19_42_50.214Z.json" "Ephemeral API snapshot"
delete_file "docs/analysis/ai.google.dev_gemini-api_docs.2025-09-20T19_44_36.867Z.json" "Ephemeral docs snapshot"
delete_file "docs/analysis/ai_studio_analysis_bMknfKXIFA8.json" "Ephemeral analysis"
delete_file "docs/analysis/execution_results_bMknfKXIFA8.json" "Ephemeral execution results"
delete_file "docs/analysis/github_diagnostic_report.json" "Diagnostic snapshot"
delete_file "docs/analysis/production_todo_report.json" "TODO snapshot"
delete_file "docs/analysis/timeout_update_summary.json" "Update summary"

echo ""
echo "─────────────────────────────────────────"
echo "4. BUILD ARTIFACTS (should be .gitignored)"
echo "─────────────────────────────────────────"
delete_file "performance_monitoring.db" "1.2MB monitoring database"
delete_file ".coverage" "53KB coverage data"
delete_file "ai-studio-remix.xml" "205KB AI Studio export"
delete_file "apps/web/.next/cache/webpack/client-production/index.pack.old" "Old Webpack cache"
delete_file "apps/web/.next/cache/webpack/client-development/index.pack.gz.old" "Old Webpack cache"
delete_file "apps/web/.next/cache/webpack/server-development/index.pack.gz.old" "Old Webpack cache"
delete_file "apps/web/.next/cache/webpack/server-production/index.pack.old" "Old Webpack cache"

echo ""
echo "─────────────────────────────────────────"
echo "5. EMPTY/ORPHANED DIRECTORIES"
echo "─────────────────────────────────────────"
delete_file ".kombai" "Orphaned tool directory"
delete_file "workflow_results" "Empty workflow results"

echo ""
echo "─────────────────────────────────────────"
echo "6. DUPLICATE .env.example FILES"
echo "─────────────────────────────────────────"
# Keep root .env.example, delete others (they should reference root)
delete_file "packages/database/.env.example" "Duplicate (use root .env.example)"
delete_file "packages/config/.env.example" "Duplicate (use root .env.example)"

echo ""
echo "════════════════════════════════════════"
if [ "$DRY_RUN" = "dry-run" ]; then
    echo -e "${YELLOW}DRY RUN COMPLETE${NC}"
    echo ""
    echo "To execute cleanup, run:"
    echo "  ./scripts/cleanup_bloat.sh execute"
else
    echo -e "${GREEN}CLEANUP COMPLETE${NC}"
    echo ""
    echo "Next: Run 'git status' to review changes"
fi
echo "════════════════════════════════════════"
