#!/bin/bash
# Simple Post-Claude Code Validation Script
# Run this after Claude Code makes changes to catch issues immediately

echo "🔧 Post-Claude Code Validation"
echo "============================="

# 1. Quick file scan for banned patterns
echo "1. Scanning for banned patterns..."
ISSUES=0

# Check for Rick Roll video ID (exclude validation scripts themselves)
if grep -r "dQw4w9WgXcQ" tests/ src/ 2>/dev/null | grep -v "test_storage.py" | grep -v "validation" | grep -v "verify_tests"; then
    echo "❌ Found banned Rick Roll video ID in source code"
    echo "💡 Fix: sed -i 's/dQw4w9WgXcQ/auJzb1D-fag/g' [filename]"
    ISSUES=$((ISSUES + 1))
else
    echo "✅ No banned video IDs found in source code"
fi

# Check for mock filesystem usage
if grep -r "pyfakefs\|fake_filesystem" tests/ 2>/dev/null; then
    echo "❌ Found banned mock filesystem usage"
    echo "💡 Convert to real tempfile operations"
    ISSUES=$((ISSUES + 1))
fi

# Check for loose Python files
LOOSE_COUNT=$(find . -maxdepth 1 -name "*.py" -not -name "setup.py" -not -name "manage.py" | wc -l)
if [ $LOOSE_COUNT -gt 2 ]; then
    echo "❌ Found $LOOSE_COUNT loose Python files in root"
    find . -maxdepth 1 -name "*.py" -not -name "setup.py" -not -name "manage.py"
    echo "💡 Move these to src/, scripts/, or tests/"
    ISSUES=$((ISSUES + 1))
fi

# 2. Run comprehensive test verification
echo ""
echo "2. Running comprehensive verification..."
if python3 scripts/verify_tests.py; then
    echo "✅ Test verification passed"
else
    echo "❌ Test verification failed"
    ISSUES=$((ISSUES + 1))
fi

# 3. Check if tests still pass
echo ""
echo "3. Running critical tests..."
if python3 -m pytest tests/unit/test_storage.py -q; then
    echo "✅ Storage tests pass"
else
    echo "❌ Storage tests failing"
    ISSUES=$((ISSUES + 1))
fi

# 4. Summary
echo ""
if [ $ISSUES -eq 0 ]; then
    echo "🎉 All validations passed! Claude Code changes look good."
    exit 0
else
    echo "⚠️  Found $ISSUES issues that need attention"
    echo ""
    echo "🔧 Quick fixes available:"
    echo "  • Fix video IDs: sed -i 's/dQw4w9WgXcQ/auJzb1D-fag/g' tests/*.py"
    echo "  • Run full verification: python3 scripts/verify_tests.py"
    echo "  • Test storage: pytest tests/unit/test_storage.py -v"
    exit 1
fi
