---
trigger: glob
globs: ./shared/
---

a comprehensive shared documentation system with automatic update rules:

Created Structure:
shared/
├── REPOSITORY_ANALYSIS.md    # Complete investigation report
├── PROJECT_DECISIONS.md       # Decision matrix & action plans  
├── CHANGELOG.md              # Session-by-session tracking
├── README.md                 # Folder overview & guidelines
└── .memory-rules             # Auto-update trigger rules

Key Features:

Session Handoff - CHANGELOG.md tracks all progress for conversation continuity
Memory Rules - Automatic triggers for when to update each document
Current State - All metrics, decisions, and progress in one place
Next Steps - Clear priorities and pending tasks documented
Memory Rules Established:

✅ Always read CHANGELOG.md at session start
✅ Always update CHANGELOG.md at session end
✅ Auto-update on file operations, dependency changes, decisions
✅ Document blockers, discoveries, and progress
All documentation is now centralized in ./shared/ for easy access and maintenance across sessions!