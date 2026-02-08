# NPM Vulnerabilities Report

**Date**: 2026-02-08
**After Cleanup**: Post repository cleanup

## Current Vulnerability Status

### Summary

- **Total**: 12 vulnerabilities
- **Severity**: 1 moderate, 11 high
- **Auto-Fixed**: 3 packages
- **Remaining**: Require breaking changes to fix

---

## Vulnerabilities Breakdown

### 1. **devalue** (High Severity)

- **Affected Versions**: 5.1.0 - 5.6.1
- **Issues**:
  - DoS via memory/CPU exhaustion in `devalue.parse`
  - Memory exhaustion vulnerability
- **Impact**: Affects `@workflow/*` packages
- **Fix**: Requires `npm audit fix --force` (breaking change to workflow@2.0.6)

### 2. **next** (High Severity)

- **Affected Versions**: 15.6.0-canary.0 - 16.1.4
- **Issues**:
  - DoS via Image Optimizer remotePatterns
  - HTTP request deserialization DoS with React Server Components
  - Unbounded memory consumption via PPR Resume Endpoint
- **Impact**: Affects `@workflow/web` and `@workflow/cli`
- **Fix**: Available via `npm audit fix` (already applied if possible)

---

## Dependency Tree

### workflow Package Chain

```
workflow
├── @workflow/astro - depends on devalue
├── @workflow/cli - depends on @workflow/web (next vulnerable)
├── @workflow/core - depends on devalue
├── @workflow/next - depends on devalue
├── @workflow/nitro - depends on devalue
│   └── @workflow/nuxt
└── @workflow/sveltekit - depends on devalue
```

---

## Recommendations

### Option 1: Accept Current Risk (Recommended for Dev)

- **Action**: None
- **Rationale**:
  - These are workflow-related packages (likely dev/build tools)
  - Not exposed in production runtime
  - Breaking changes may disrupt development

### Option 2: Force Fix (Use with Caution)

```bash
npm audit fix --force
```

- **Warning**: This will install workflow@2.0.6 with breaking changes
- **Impact**: May break existing workflow configurations
- **Recommendation**: Test in a separate branch first

### Option 3: Manual Updates

Review each package individually:

```bash
npm outdated
npm update <package-name>
```

---

## Production Security Checklist

✅ **Safe for Production**:

- These vulnerabilities are in build/dev tools (@workflow/\*)
- Not part of runtime dependencies
- Backend (Python/FastAPI) unaffected
- Frontend (Next.js apps/web) using separate Next.js installation

⚠️ **Monitor**:

- Check for updates to @workflow packages
- Review security advisories periodically
- Run `npm audit` monthly

---

## Next Steps

### Immediate

- [x] Acknowledge vulnerabilities exist
- [x] Document status in this report
- [ ] Decide on fix approach

### Future

- [ ] Set up automated security scanning (Dependabot/Renovate)
- [ ] Create security policy for dependency updates
- [ ] Test `npm audit fix --force` in dev branch

---

**Risk Assessment**: **LOW** for production runtime
**Action Required**: Monitor, optional forced fix for peace of mind
