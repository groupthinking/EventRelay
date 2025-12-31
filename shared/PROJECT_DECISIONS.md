# Project Decisions & Action Plan

**Date:** December 20, 2024  
**Status:** Phase 2 - Decision Making

---

## Decision Matrix

### Projects to Keep (Active Production)

| Project                | Decision | Rationale                                | Priority |
| ---------------------- | -------- | ---------------------------------------- | -------- |
| **EventRelay**         | ✅ Keep  | Primary AI platform, active development  | Critical |
| **netmesh-production** | ✅ Keep  | Production Cloudflare app, modern stack  | Critical |
| **mcp-servers**        | ✅ Keep  | Core infrastructure for both projects    | Critical |
| **software-on-demand** | ✅ Keep  | Active validation utility for EventRelay | Medium   |
| **xai-grok-wrapper**   | ✅ Keep  | Utility library, well-documented         | Low      |

### Projects Investigated & Resolved

| Project                                 | Status      | Resolution          | Date         |
| --------------------------------------- | ----------- | ------------------- | ------------ |
| **self-correcting-executor-PRODUCTION** | ✅ Resolved | Moved to ~/Desktop  | Dec 21, 2024 |
| **agents-marketplace**                  | ✅ Resolved | Archive recommended | Dec 22, 2024 |

### Projects Archived

| Project                    | Decision           | Destination                      | Date Completed    |
| -------------------------- | ------------------ | -------------------------------- | ----------------- |
| **Zero to Launch Bundle**  | 🗄️ Archived        | Removed by user                  | Dec 21, 2024      |
| **genkit-mcp (full repo)** | 🗄️ Archived        | `_archive/genkit-mcp-full-repo/` | Dec 21, 2024      |
| **agents-marketplace**     | 🗄️ Archive Pending | `_archive/agents-marketplace/`   | Awaiting approval |

---

## Technical Decisions

### 1. genkit-mcp Bloat Resolution

**Decision:** Extract wrapper only, archive full repository

**Status:** ✅ **Complete** (Dec 21, 2024)

**Actual Results:**

- ✅ Disk space saved: ~200MB
- ✅ Files removed: ~24,300
- ✅ Wrapper extracted to `mcp-servers/genkit-wrapper/`
- ✅ Full repo archived to `_archive/genkit-mcp-full-repo/`
- ✅ No broken imports found
- ✅ Functionality maintained

**Risk Assessment:** Low - Completed successfully with no issues

---

### 2. EventRelay Tech Stack Standardization

**Decision:** Phased approach to reduce technical debt

#### Phase 1: TypeScript Upgrade (Week 1-2)

**Target:** TypeScript 4.9.5 → 5.x

**Rationale:**

- Critical security and performance improvements
- Better type inference
- Required for modern tooling

**Implementation:**

```bash
cd ./projects/EventRelay/frontend
npm install typescript@^5.6.0 --save-dev
npm install @types/react@^18.3.0 @types/react-dom@^18.3.0 --save-dev

# Update all package workspaces
cd ../packages/logger && npm install typescript@^5.6.0 --save-dev
# Repeat for all packages
```

**Risk:** Medium (breaking changes possible)  
**Mitigation:** Incremental package-by-package upgrade

---

#### Phase 2: React Version Standardization (Week 3-4)

**Target:** Standardize on React 18.x across all apps

**Rationale:**

- React 19 has breaking changes
- React 18 is stable and well-supported
- Easier to maintain consistency

**Apps to Downgrade:**

- `supabase/mcp-supabase-frontend` (19.0.0 → 18.2.0)
- `supabase/` main (19.0.0 → 18.2.0)
- `with-a2a-a2ui` (19.2.3 → 18.2.0)

**Risk:** Low (downgrade is safer than upgrade)

---

#### Phase 3: Build Tool Migration (Month 2)

**Target:** CRA → Vite (frontend only)

**Rationale:**

- 10x faster build times
- Better HMR (Hot Module Replacement)
- Modern tooling ecosystem
- Industry standard

**Deferred:** Not immediate priority, plan for Month 2

---

#### Phase 4: Styling Simplification (Month 3)

**Target:** Reduce from 3 systems to 2

**Current State:**

- MUI v7 (component library)
- Emotion (CSS-in-JS, required by MUI)
- Tailwind v3 (utility classes)

**Decision:** Keep MUI + Emotion, use Tailwind sparingly for utilities only

**Rationale:**

- MUI requires Emotion (can't remove)
- MUI provides comprehensive components
- Tailwind useful for quick utilities
- Removing Tailwind would require rewriting many components

**Alternative:** If major refactor happens, consider MUI + Tailwind only (remove Emotion)

---

### 3. MCP Server Consolidation

**Decision:** Create monorepo for custom servers, keep external servers separate

**Structure:**

```
mcp-servers/
├── custom/                      # Monorepo for custom servers
│   ├── package.json            # Root workspace config
│   ├── packages/
│   │   ├── github/
│   │   ├── grok/
│   │   ├── puppeteer/
│   │   ├── fetch/
│   │   └── shared/             # Shared utilities
│   └── docs/
├── external/                    # External/third-party servers
│   ├── perplexity-mcp/
│   └── metacognition-tools/
├── specialized/                 # Specialized @modelcontextprotocol servers
│   ├── server-knowledge-management/
│   ├── server-code-assistant/
│   └── [4 more servers]
├── infrastructure/
│   ├── shared-state/
│   └── ai_ops_skill_mesh_kit/
└── genkit-wrapper/             # Minimal wrapper (after extraction)
```

**Implementation Timeline:** Week 2-3

---

### 4. Express Version Standardization

**Decision:** Standardize on Express v5 for all custom servers

**Rationale:**

- Express v5 is stable
- Better async/await support
- Improved error handling
- Future-proof

**Servers to Upgrade:**

- All genkit samples (if kept) - v4 → v5
- Verify compatibility with MCP SDK

**Timeline:** Week 2

---

### 5. ORM Strategy

**Decision:** Keep both ORMs, use appropriately

**Rationale:**

- SQLAlchemy (Python) - Backend, FastAPI
- Prisma (TypeScript) - Frontend packages, Node.js services
- Different ecosystems, both needed
- Migration would be costly with minimal benefit

**Alternative Considered:** Drizzle for TypeScript (like netmesh-production)

- **Rejected:** Prisma is already integrated, migration not worth effort

---

### 6. Developer Workflow Strategy

**Decision:** Use version-controlled `.vscode/tasks.json` for shared workflows.

**Rationale:**

- Ensures all developers (and CI environments) have access to standard commands.
- Removes dependency on individual user configuration.
- Aligns with "Configuration as Code" principle.

**Defined Tasks:**

- `Run API (Dev)`
- `Deploy Staging`
- `Run Worker`
- `Verify Grok`
- `Run Tests`

**Status:** ✅ Implemented (Dec 31, 2024)

---

## Completed Action Items

### ✅ Phase 1: Investigation (Dec 20, 2024)

- [x] Repository scan and project identification
- [x] Tech stack documentation
- [x] Dependency mapping
- [x] Metrics establishment
- [x] Documentation system creation

### ✅ Phase 2: Cleanup (Dec 21, 2024)

- [x] genkit-mcp extraction and archival
- [x] self-correcting-executor-PRODUCTION relocation
- [x] Zero to Launch Bundle removal
- [x] Archive structure organization

### ✅ Phase 2: Final Investigation (Dec 22, 2024)

- [x] agents-marketplace investigation complete
- [x] All documentation updated
- [x] Ready for Phase 3

---

## Pending Action Items

### Immediate (This Week) - Awaiting Approval

#### Task 1: Archive agents-marketplace

```bash
# Archive the directory
mkdir -p ./_archive/agents-marketplace
mv ./agents-marketplace ./_archive/agents-marketplace/

# Create archive note
cat > ./_archive/agents-marketplace/ARCHIVED.txt << 'EOF'
Archived: December 22, 2024
Reason: Legacy OpenAI Hub scaffolding scripts, no longer in use
References: Non-existent $HOME/Dev/OpenAI_Hub directory
Investigation: No active usage found in current projects
Safe to archive: Yes - no dependencies found
EOF
```

**Risk:** Minimal - No active usage found

---

### Day 3-4: Cleanup Phase

#### Task 3: Archive Zero to Launch Bundle

```bash
mkdir -p ./_archive/documentation
mv "./Zero to Launch Bundle" ./_archive/documentation/zero-to-launch-bundle
echo "Archived on $(date)" > ./_archive/documentation/zero-to-launch-bundle/ARCHIVED.txt
```

---

#### Task 4: Extract genkit-mcp Wrapper

```bash
# Create wrapper directory
mkdir -p ./mcp-servers/genkit-wrapper

# Copy only MCP plugin
cp -r ./mcp-servers/genkit-mcp/repo/js/plugins/mcp/* ./mcp-servers/genkit-wrapper/

# Copy minimal documentation
cp ./mcp-servers/genkit-mcp/README.md ./mcp-servers/genkit-wrapper/
cat > ./mcp-servers/genkit-mcp-wrapper/README.md << 'EOF'
# Genkit MCP Plugin Wrapper

This is a minimal extraction of the Genkit MCP plugin from the full Google Genkit repository.

**Original Repository:** https://github.com/firebase/genkit
**Plugin Location:** js/plugins/mcp/

**Full repository archived at:** `../../_archive/genkit-mcp-full-repo/`

## Usage

See the original plugin documentation in the examples/ directory.
EOF

# Archive full repository
mkdir -p ./_archive/genkit-mcp-full-repo
mv ./mcp-servers/genkit-mcp ./_archive/genkit-mcp-full-repo/
echo "Archived on $(date). Original size: 203MB, 24,409 files" > ./_archive/genkit-mcp-full-repo/ARCHIVED.txt

# Update any references (if found)
grep -r "genkit-mcp" ./mcp-servers/ ./projects/ --include="*.json" -l | while read file; do
  echo "Check $file for references to update"
done
```

**Validation:**

```bash
# Verify wrapper works
cd ./mcp-servers/genkit-wrapper
npm install
npm test  # If tests exist

# Check size reduction
du -sh ./_archive/genkit-mcp-full-repo/
du -sh ./mcp-servers/genkit-wrapper/
```

---

### Day 5: Documentation & Validation

#### Task 5: Update Documentation

```bash
# Update ECOSYSTEM_SUMMARY.md
# Update README files
# Create migration notes
```

#### Task 6: Validate Changes

```bash
# Run tests
cd ./projects/EventRelay && npm test
cd ./projects/netmesh-production && npm test

# Check for broken imports
grep -r "genkit-mcp" ./mcp-servers/ ./projects/ --include="*.ts" --include="*.js"

# Verify MCP servers still work
# Test Claude integration
```

---

## Success Criteria

### Phase 2 Completion Checklist ✅

- [x] self-correcting-executor-PRODUCTION investigated and relocated (Dec 21)
- [x] agents-marketplace investigated and recommendation made (Dec 22)
- [x] Zero to Launch Bundle removed (Dec 21)
- [x] genkit-mcp extracted and full repo archived (Dec 21)
- [x] All documentation updated (Dec 22)
- [x] No broken imports or references
- [x] Disk space reduced by ~200MB
- [x] File count reduced by ~24,000

### Phase 3 Readiness Checklist

- [x] All unknown projects resolved
- [x] All cleanup actions complete
- [x] Documentation up to date
- [ ] Engineer approval for Phase 3 start
- [ ] Timeline established for TypeScript upgrade
- [ ] Resources allocated for React standardization

### Month 1 Completion Checklist

- [ ] EventRelay TypeScript upgraded to 5.x
- [ ] React versions standardized to 18.x
- [ ] MCP servers consolidated into monorepo structure
- [ ] Express versions standardized to v5
- [ ] All projects documented
- [ ] Disk usage < 300MB
- [ ] Directory count < 10,000

---

## Risk Assessment

### High Risk Items

1. **TypeScript Upgrade** - May break existing code
   - Mitigation: Package-by-package upgrade, thorough testing
2. **genkit-mcp Extraction** - May break MCP functionality
   - Mitigation: Keep full archive, test thoroughly before deletion

### Medium Risk Items

1. **React Version Downgrade** - May have compatibility issues

   - Mitigation: Downgrade is safer than upgrade, test each app

2. **MCP Server Consolidation** - May affect running services
   - Mitigation: Do during low-traffic period, have rollback plan

### Low Risk Items

1. **Archive Zero to Launch Bundle** - Personal documents

   - Mitigation: Simple move operation, easily reversible

2. **agents-marketplace Review** - Shell scripts
   - Mitigation: Check usage before removal

---

## Rollback Plans

### If genkit-mcp Extraction Fails

```bash
# Restore from archive
mv ./_archive/genkit-mcp-full-repo/genkit-mcp ./mcp-servers/
rm -rf ./mcp-servers/genkit-wrapper
```

### If TypeScript Upgrade Breaks Build

```bash
# Revert package by package
cd ./projects/EventRelay/frontend
npm install typescript@4.9.5 --save-dev
```

### If MCP Server Consolidation Causes Issues

```bash
# Restore original structure
# Keep backup of original structure before consolidation
```

---

## Next Review Date

**Date:** December 27, 2024  
**Agenda:**

- Review Week 1 progress
- Assess any blockers
- Plan Week 2 activities
- Update metrics and goals

---

**Status:** Phase 2 Complete - Ready for Phase 3  
**Phase 2 Completed:** December 22, 2024  
**Phase 3 Approval:** Pending Engineer Decision
