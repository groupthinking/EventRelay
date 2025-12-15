# Claude Code Hooks Setup Guide

## Multiple Hook Options

You now have several ways to catch Claude Code issues immediately after code generation:

### Option 1: Manual Post-Validation (Simplest)

Run after Claude Code makes changes:
```bash
chmod +x scripts/post_claude_validation.sh
./scripts/post_claude_validation.sh
```

### Option 2: Git Pre-Commit Hook (Automatic)

Install the git hook to catch issues before commits:
```bash
chmod +x scripts/claude_code_validation_hook.sh
ln -sf ../../scripts/claude_code_validation_hook.sh .git/hooks/pre-commit
```

Now git will automatically validate before each commit.

### Option 3: File System Watcher (Real-time)

Install watchdog dependency:
```bash
pip install watchdog
```

Run the continuous file watcher:
```bash
python3 scripts/claude_code_watcher.py
```

This monitors file changes and validates automatically.

### Option 4: VS Code Integration

Add to `.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Validate Claude Code Changes",
            "type": "shell",
            "command": "./scripts/post_claude_validation.sh",
            "group": "build",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        }
    ]
}
```

Run with Ctrl+Shift+P → "Tasks: Run Task" → "Validate Claude Code Changes"

## What Each Hook Catches

1. **Banned video IDs** (dQw4w9WgXcQ)
2. **Mock filesystem usage** (pyfakefs)  
3. **Loose Python files** in root directory
4. **Excessive .md files** creating bloat
5. **Test consistency issues**
6. **Project structure violations**

## Auto-Fix Capabilities

Some hooks can automatically suggest or apply fixes:

```bash
# Fix banned video IDs
sed -i 's/dQw4w9WgXcQ/auJzb1D-fag/g' tests/*.py

# Clean up loose files
mkdir -p scripts/misc
mv *.py scripts/misc/

# Run verification
python3 scripts/verify_tests.py
```

## Recommended Setup

For immediate Claude Code issue detection:

1. **Install git hook** for commit-time validation
2. **Use manual script** right after Claude Code sessions  
3. **Run file watcher** during active development

This multi-layered approach catches issues at different stages and prevents the filesystem bloat and confusion you were experiencing.
