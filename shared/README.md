# Shared Documentation Folder
**Location:** `/Users/garvey/Dev/shared/`  
**Purpose:** Work-in-progress documentation and session handoff materials

---

## 📁 Folder Contents

### Core Documentation

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **REPOSITORY_ANALYSIS.md** | Complete repository investigation report | After major discoveries |
| **PROJECT_DECISIONS.md** | Decision matrix and action plans | When decisions are made |
| **TECH_STACK_MATRIX.md** | Technology comparison across projects | When tech changes |
| **CHANGELOG.md** | Session-by-session progress tracking | Every session |
| **README.md** | This file - folder overview | As needed |

---

## 🎯 Purpose

This folder serves as the **single source of truth** for:

1. **Repository State** - Current status of all projects
2. **Decisions Made** - What we decided and why
3. **Progress Tracking** - What's done, in progress, and pending
4. **Session Handoff** - Context for new chat sessions
5. **Tech Documentation** - Comprehensive tech stack information

---

## 📋 Update Guidelines

### When to Update

**CHANGELOG.md** - Update at:
- ✅ End of each work session
- ✅ When completing major tasks
- ✅ When encountering blockers
- ✅ When making important decisions

**REPOSITORY_ANALYSIS.md** - Update when:
- ✅ New projects are discovered
- ✅ Projects are archived or removed
- ✅ Major findings are uncovered
- ✅ Metrics change significantly

**PROJECT_DECISIONS.md** - Update when:
- ✅ New decisions are made
- ✅ Action items are completed
- ✅ Plans change or pivot
- ✅ Risks are identified

**TECH_STACK_MATRIX.md** - Update when:
- ✅ Dependencies are upgraded
- ✅ New technologies are adopted
- ✅ Tech debt is resolved
- ✅ Frameworks are changed

---

## 🔄 Session Handoff Process

### Starting a New Session

1. **Read CHANGELOG.md first** - Get context on what was done last
2. **Check "In Progress" section** - See what's currently being worked on
3. **Review "Pending Tasks"** - Understand what's next
4. **Read "Notes for Next Session"** - Important context and questions

### Ending a Session

1. **Update CHANGELOG.md** with:
   - What was accomplished
   - What's in progress
   - What's blocked
   - Notes for next session
2. **Update relevant documentation** if major changes occurred
3. **Commit changes** to preserve state

---

## 📊 Current State Summary

**As of:** December 20, 2024

### Repository Overview
- **Total Projects:** 10
- **Active Production:** 3 (EventRelay, netmesh-production, mcp-servers)
- **Under Investigation:** 2 (self-correcting-executor, agents-marketplace)
- **Archived:** 1 (multiple projects in _archive/)
- **Reference:** 2 (Vision-Agents, docs)

### Critical Metrics
- **Directories:** 33,342 (target: <10,000)
- **Disk Usage:** ~500MB (target: <300MB)
- **Tech Debt Score:** 6.5/10 (target: 8.5/10)

### Top Priorities
1. 🔴 Extract genkit-mcp wrapper (save 200MB)
2. 🟡 Investigate self-correcting-executor-PRODUCTION
3. 🟡 Upgrade EventRelay TypeScript to 5.x
4. 🟢 Standardize React versions

---

## 🗂️ File Relationships

```
shared/
├── README.md (you are here)
│   └── Overview of all documentation
│
├── CHANGELOG.md
│   └── References → All other docs for specific changes
│
├── REPOSITORY_ANALYSIS.md
│   └── Deep dive into each project
│       └── Used by → PROJECT_DECISIONS.md
│
├── PROJECT_DECISIONS.md
│   └── Based on → REPOSITORY_ANALYSIS.md
│       └── Tracked in → CHANGELOG.md
│
└── TECH_STACK_MATRIX.md
    └── Detailed tech comparison
        └── Informs → PROJECT_DECISIONS.md
```

---

## 🎨 Documentation Standards

### Markdown Formatting
- Use **bold** for emphasis
- Use `code` for file paths, commands, and technical terms
- Use tables for structured data
- Use checkboxes for task lists
- Use emojis sparingly for visual navigation

### Status Indicators
- ✅ Complete
- 🔄 In Progress
- ⏳ Pending
- ⚠️ Needs Attention
- 🔴 High Priority
- 🟡 Medium Priority
- 🟢 Low Priority
- 🗄️ Archive Candidate

### File Naming
- Use SCREAMING_SNAKE_CASE for major docs (CHANGELOG.md)
- Use descriptive names (REPOSITORY_ANALYSIS.md not ANALYSIS.md)
- Include dates in session-specific docs if needed

---

## 🔐 Memory Rules

### Auto-Update Triggers

The following changes should **automatically trigger documentation updates**:

1. **File Operations**
   - Moving/renaming projects → Update REPOSITORY_ANALYSIS.md
   - Archiving projects → Update CHANGELOG.md + REPOSITORY_ANALYSIS.md
   - Creating new projects → Update all relevant docs

2. **Dependency Changes**
   - npm install/upgrade → Update TECH_STACK_MATRIX.md
   - Package.json changes → Update TECH_STACK_MATRIX.md
   - Framework migrations → Update all docs

3. **Decision Making**
   - Any "we should..." decision → Update PROJECT_DECISIONS.md
   - Any "let's do..." action → Update CHANGELOG.md
   - Any "this is blocked" → Update CHANGELOG.md

4. **Session Transitions**
   - End of session → Update CHANGELOG.md (mandatory)
   - Start of session → Read CHANGELOG.md (mandatory)
   - Context switch → Note in CHANGELOG.md

---

## 📖 Quick Reference

### Common Tasks

**Starting Work:**
```bash
cd /Users/garvey/Dev
cat shared/CHANGELOG.md | head -100  # Read recent changes
```

**After Making Changes:**
```bash
# Update CHANGELOG.md with what you did
# Commit changes to preserve state
```

**Finding Information:**
- Project details → `REPOSITORY_ANALYSIS.md`
- What to do next → `PROJECT_DECISIONS.md`
- Tech stack info → `TECH_STACK_MATRIX.md`
- Recent progress → `CHANGELOG.md`

---

## 🚀 Next Steps

Based on current state, the next session should:

1. ✅ Read CHANGELOG.md for context
2. 🔍 Investigate self-correcting-executor-PRODUCTION
3. 🗜️ Extract genkit-mcp wrapper
4. 📝 Update documentation with findings
5. 🎯 Plan TypeScript upgrade for EventRelay

---

## 📞 Support

If documentation is unclear or missing information:
1. Check CHANGELOG.md for recent context
2. Review REPOSITORY_ANALYSIS.md for project details
3. Consult PROJECT_DECISIONS.md for rationale
4. Update this README.md to clarify for future sessions

---

**Maintained By:** AI Assistant (Kombai)  
**Last Updated:** December 20, 2024  
**Version:** 1.0.0  
**Status:** ✅ Active