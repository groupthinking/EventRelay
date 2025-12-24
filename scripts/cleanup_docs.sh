#!/bin/bash
# Clean up scattered documentation files

echo "🧹 Organizing documentation files..."

# Create docs subdirectories
mkdir -p docs/planning docs/reports docs/guides docs/status

# Move planning documents
echo "📋 Moving planning documents..."
mv PLAN.md docs/planning/ 2>/dev/null || true
mv ARCHITECTURAL_*.md docs/planning/ 2>/dev/null || true
mv PROJECT_SCAFFOLDING.md docs/planning/ 2>/dev/null || true

# Move reports
echo "📊 Moving reports..."
mv *_REPORT.md docs/reports/ 2>/dev/null || true
mv *_AUDIT*.md docs/reports/ 2>/dev/null || true
mv COMPREHENSIVE_*.md docs/reports/ 2>/dev/null || true

# Move guides
echo "📖 Moving guides..."
mv *_GUIDE.md docs/guides/ 2>/dev/null || true
mv *_README.md docs/guides/ 2>/dev/null || true
mv ENHANCED_README.md docs/guides/ 2>/dev/null || true

# Move status files
echo "📈 Moving status files..."
mv *_STATUS.md docs/status/ 2>/dev/null || true
mv *_SUMMARY.md docs/status/ 2>/dev/null || true
mv IMPLEMENTATION_*.md docs/status/ 2>/dev/null || true
mv FINAL_*.md docs/status/ 2>/dev/null || true

# Move fix documentation
echo "🔧 Moving fix documentation..."
mv *_FIX*.md docs/status/ 2>/dev/null || true
mv *_FIXES*.md docs/status/ 2>/dev/null || true

# Move miscellaneous docs
echo "📝 Moving miscellaneous docs..."
mv BLUEPRINT_*.md docs/planning/ 2>/dev/null || true
mv TODO_*.md docs/planning/ 2>/dev/null || true
mv DUPLICATE_*.md docs/reports/ 2>/dev/null || true

echo "✅ Documentation cleanup complete!"
echo ""
echo "📁 New structure:"
echo "  docs/planning/  - Project planning documents"
echo "  docs/reports/   - Audit and analysis reports"  
echo "  docs/guides/    - Usage and development guides"
echo "  docs/status/    - Status updates and fixes"
echo ""
echo "🎯 Root directory is now clean for Claude Code!"
