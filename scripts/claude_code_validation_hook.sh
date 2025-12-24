#!/bin/bash
# Git Pre-Commit Hook - Validates Claude Code Changes
# Install: ln -sf ../../scripts/claude_code_validation_hook.sh .git/hooks/pre-commit

echo "🔍 Claude Code Validation Hook"
echo "=============================="

# Run our test verification
echo "1. Checking test consistency..."
if python3 scripts/verify_tests.py; then
    echo "✅ Test consistency checks passed"
else
    echo "❌ Test consistency issues found"
    echo "💡 Run: python3 scripts/verify_tests.py"
    exit 1
fi

# Check for banned patterns in any new/modified files
echo ""
echo "2. Checking for banned patterns..."
BANNED_PATTERNS=(
    "dQw4w9WgXcQ"
    "pyfakefs"
    "fake_filesystem"
    "from pyfakefs"
    "import pyfakefs"
)

VIOLATIONS=0
for pattern in "${BANNED_PATTERNS[@]}"; do
    # Check staged files for banned patterns
    if git diff --cached --name-only | xargs grep -l "$pattern" 2>/dev/null; then
        echo "❌ Found banned pattern: $pattern"
        git diff --cached --name-only | xargs grep -n "$pattern" 2>/dev/null
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done

if [ $VIOLATIONS -gt 0 ]; then
    echo ""
    echo "❌ Found $VIOLATIONS banned pattern violations"
    echo "💡 Fix these issues before committing"
    exit 1
fi

# Check for loose Python files in root
echo ""
echo "3. Checking project structure..."
LOOSE_FILES=$(find . -maxdepth 1 -name "*.py" -not -name "setup.py" -not -name "manage.py" | wc -l)
if [ $LOOSE_FILES -gt 2 ]; then
    echo "❌ Found loose Python files in root directory"
    find . -maxdepth 1 -name "*.py" -not -name "setup.py" -not -name "manage.py"
    echo "💡 Move these to appropriate subdirectories"
    exit 1
fi

# Check for excessive .md files in root
MD_FILES=$(find . -maxdepth 1 -name "*.md" | wc -l)
if [ $MD_FILES -gt 5 ]; then
    echo "❌ Too many .md files in root ($MD_FILES found)"
    echo "💡 Move documentation to docs/ subdirectories"
    exit 1
fi

echo "✅ All Claude Code validation checks passed!"
echo ""
