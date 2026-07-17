#!/bin/bash
set -e
git checkout -b fix/remove-importlib-util-openai-dev
git add src/agents/openai_dev_task_manager.py
git commit -m "🧹 Remove Unused importlib.util Import

🎯 What: Removed the unused \`importlib.util\` import in \`src/agents/openai_dev_task_manager.py\` and refactored the dynamic loading to use direct Python imports.
💡 Why: Removing the dynamic class loading using file path and relying on standard direct import eliminates the need for the \`importlib.util\` module, making the code much cleaner and easier to maintain.
✅ Verification: Tested the refactored code directly by loading the \`OpenAIDevTaskManager\` class, validating no regressions, and running \`ruff check\` + \`black\` for formatting.
✨ Result: Cleaned up unnecessary imports, simplifying the code logic without altering existing functionality."
