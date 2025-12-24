# EventRelay Remediation Plan

**Analysis Date:** 2025-12-03  
**Priority Scale:** P0 (Critical) → P1 (High) → P2 (Medium) → P3 (Low)

---

## 🚨 P0 - Critical (Fix Immediately)

### REM-001: Fix Pickle Deserialization Vulnerability

```yaml
id: REM-001
severity: CRITICAL
category: Security
location:
  file: src/youtube_extension/backend/services/intelligent_cache.py
  lines: 285
description: |
  pickle.loads() on Redis data enables RCE if cache is compromised.
impact: Complete system compromise via arbitrary code execution.
remediation:
  immediate: |
    # Disable Redis caching temporarily
    REDIS_CACHE_ENABLED=false in .env
  proper: |
    Replace pickle with JSON serialization.
    For complex objects, use msgpack with schema validation.
  code_example: |
    # BEFORE
    entry_data = pickle.loads(data)
    
    # AFTER
    import json
    entry_data = json.loads(data.decode('utf-8'))
effort_estimate: 2-4 hours
dependencies: []
verification:
  test: |
    Create test with malicious pickle payload, verify rejection.
  automated: |
    pytest tests/unit/test_intelligent_cache_security.py
```

---

### REM-002: Resolve NPM High Severity Vulnerabilities

```yaml
id: REM-002
severity: CRITICAL
category: Dependencies
location:
  file: package.json, package-lock.json
  lines: N/A
description: |
  31 npm vulnerabilities including 6 high severity in build tooling.
impact: Supply chain attacks, XSS in development builds.
remediation:
  immediate: |
    npm audit fix
  proper: |
    npm audit fix --force
    npm update @ai-sdk/anthropic @ai-sdk/google @ai-sdk/openai
    Test all builds after upgrade.
  code_example: |
    # In CI pipeline
    - name: Security Audit
      run: npm audit --audit-level=high
      continue-on-error: false
effort_estimate: 4-8 hours (including testing)
dependencies: []
verification:
  test: npm audit --audit-level=high returns exit code 0
  automated: Add to CI/CD pipeline
```

---

### REM-003: Remove dangerouslySetInnerHTML Usage

```yaml
id: REM-003
severity: HIGH
category: Security
location:
  file: frontend/src/components/LearningFusion.tsx
  lines: 429-438
description: |
  Inline script with function.toString() creates XSS vector.
impact: Session hijacking, credential theft if function is tainted.
remediation:
  immediate: |
    Remove the script tag entirely for now.
  proper: |
    Move tests to Jest test file.
  code_example: |
    # BEFORE (in component)
    <script dangerouslySetInnerHTML={{ __html: `...` }} />
    
    # AFTER (in test file)
    // frontend/src/components/__tests__/LearningFusion.test.tsx
    describe('computeBlockedState', () => {
      it('blocks when time exceeded', () => {
        expect(computeBlockedState(false, 3001, 3000)).toBe(true);
      });
    });
effort_estimate: 1-2 hours
dependencies: []
verification:
  test: grep -r "dangerouslySetInnerHTML" frontend/ returns no results
  automated: Add ESLint rule react/no-danger
```

---

## ⚠️ P1 - High (Fix Before Production)

### REM-004: Audit Subprocess Input Sources

```yaml
id: REM-004
severity: HIGH
category: Security
location:
  file: Multiple (see SECURITY_REPORT.md)
  lines: Various
description: |
  23 subprocess calls found. While using array arguments (safe pattern),
  need to verify no user input flows to arguments.
impact: Command injection if user data reaches subprocess args.
remediation:
  immediate: |
    Document each subprocess call with input source annotation.
  proper: |
    Add input validation/sanitization layer.
    Use allowlists for acceptable command arguments.
  code_example: |
    # Add validation
    ALLOWED_COMMANDS = {'npm', 'node', 'python'}
    
    def safe_run(cmd: List[str], **kwargs):
        if cmd[0] not in ALLOWED_COMMANDS:
            raise ValueError(f"Unauthorized command: {cmd[0]}")
        return subprocess.run(cmd, **kwargs)
effort_estimate: 4-6 hours
dependencies: []
verification:
  test: Security audit confirms no user input to subprocess
  automated: Static analysis with bandit
```

---

### REM-005: Consolidate Test Directories

```yaml
id: REM-005
severity: MEDIUM
category: Code Quality
location:
  file: tests/, clean_refactor/, root directory
  lines: N/A
description: |
  Tests scattered across 3+ locations making discovery difficult.
impact: Reduced test coverage visibility, CI complexity.
remediation:
  immediate: |
    Create unified tests/ structure.
  proper: |
    Move all tests to tests/{unit,integration,e2e}/.
    Update pytest.ini paths.
    Remove clean_refactor/ after migration.
  code_example: |
    # Final structure
    tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_cache.py
    │   └── ...
    ├── integration/
    │   └── ...
    ├── e2e/
    │   └── ...
    └── fixtures/
        └── test_data.py
effort_estimate: 4-8 hours
dependencies: []
verification:
  test: pytest tests/ runs all tests
  automated: CI passes with new structure
```

---

## 🔶 P2 - Medium (Fix Within Month)

### REM-006: Remove Duplicate Agent Directories

```yaml
id: REM-006
severity: MEDIUM
category: Code Quality
location:
  file: agents/, development/agents/
  lines: N/A
description: |
  Agent code exists in multiple locations causing confusion.
impact: Maintenance burden, potential version drift.
remediation:
  proper: |
    1. Identify canonical location (development/agents/)
    2. Update all imports
    3. Remove agents/ from root
    4. Update documentation
effort_estimate: 4-6 hours
dependencies: [REM-005]
```

---

### REM-007: Clean Environment Configuration

```yaml
id: REM-007
severity: LOW
category: Configuration
location:
  file: .env*, various
  lines: N/A
description: |
  6+ environment files create confusion and drift risk.
impact: Configuration errors in deployment.
remediation:
  proper: |
    Keep only:
    - .env.example (template)
    - .env (local, gitignored)
    
    Document environment differences in README.
effort_estimate: 2-3 hours
dependencies: []
```

---

### REM-008: Archive Generated Projects

```yaml
id: REM-008
severity: LOW
category: Repository Hygiene
location:
  file: generated_projects/
  lines: N/A
description: |
  Generated demo projects bloat repository.
impact: Slower clones, confusion about source vs output.
remediation:
  proper: |
    1. Add generated_projects/ to .gitignore
    2. Remove from git history (optional)
    3. Store in separate artifacts location if needed
effort_estimate: 1 hour
dependencies: []
```

---

## 📅 Implementation Timeline

### Week 1: Security Critical
| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 1-2 | REM-001: Fix pickle vulnerability | Backend | ⬜ |
| 2-3 | REM-002: npm audit fix | Frontend | ⬜ |
| 3-4 | REM-003: Remove dangerouslySetInnerHTML | Frontend | ⬜ |
| 5 | Verification and testing | QA | ⬜ |

### Week 2-3: Stability
| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 1-3 | REM-004: Subprocess audit | Security | ⬜ |
| 4-6 | REM-005: Test consolidation | Platform | ⬜ |
| 7-8 | CI/CD updates | DevOps | ⬜ |

### Week 4: Code Quality
| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 1-2 | REM-006: Agent consolidation | Backend | ⬜ |
| 3 | REM-007: Env cleanup | DevOps | ⬜ |
| 4 | REM-008: Generated projects | Platform | ⬜ |
| 5 | Documentation updates | Docs | ⬜ |

---

## 🎯 Success Metrics

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Critical vulnerabilities | 3 | 0 | Week 1 |
| High severity npm issues | 6 | 0 | Week 1 |
| Test directories | 3+ | 1 | Week 3 |
| Duplicate agent dirs | 2 | 1 | Week 4 |
| Env config files | 6 | 2 | Week 4 |

---

*Generated by EventRelay Remediation Planning*
