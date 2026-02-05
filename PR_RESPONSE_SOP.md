# Standard Operating Procedure: Responding to Open Pull Requests

**Document Version:** 1.0  
**Last Updated:** 2026-02-05  
**Scope:** EventRelay Repository PR Management

---

## Overview

This SOP provides guidelines for responding to open pull requests in the groupthinking/EventRelay repository, particularly in light of recent code quality improvements.

---

## Quick Reference

### Current State (As of 2026-02-05):
- **Base Branch:** copilot/close-all-open-prs → copilot/manage-open-pull-requests
- **Status:** ✅ Ready for merge
- **Code Quality:** 25% improvement (205→154 linting errors)
- **Critical Fixes:** Python 3.9+ compatibility restored
- **Risk Level:** Very Low

---

## Response Templates

### Template 1: For Active PRs (Modified Python Files)

```markdown
## 🎉 Code Quality Improvements Available

Hi @{AUTHOR},

We've made improvements to the codebase that will benefit your PR:

### What's New:
- ✅ **51 linting errors fixed** (25% improvement)
- ✅ **Python 3.9+ compatibility** restored
- ✅ **Import organization** standardized across 17 files
- ✅ **8 syntax errors** resolved

### How This Helps You:
1. **Fewer merge conflicts** with organized imports
2. **Faster CI runs** with 25% fewer errors
3. **Cleaner reviews** - focus on your changes
4. **No regressions** from syntax issues

### Recommended Next Steps:
1. Rebase on latest `main` (after merge)
2. Run `ruff check src` before committing
3. Follow the [import organization pattern](FINAL_SUMMARY.md#import-organization)

### Need Help?
- Check [FINAL_SUMMARY.md](FINAL_SUMMARY.md) for complete details
- Review [CONTRIBUTING.md](CONTRIBUTING.md) for style guide
- Ask questions in this PR thread

Thanks for your contribution! 🚀
```

### Template 2: For Stale PRs (>30 days)

```markdown
## 👋 PR Status Check

Hi @{AUTHOR},

This PR has been open for {DAYS} days. We've recently improved the codebase:

### Recent Improvements:
- 25% reduction in linting errors
- Python 3.9+ compatibility fixes
- Better import organization

### Options:
1. **Rebase & Continue** - We'd love to merge this!
2. **Need Help?** - We can assist with rebasing/conflicts
3. **Close** - If this is no longer relevant, that's okay too

Please let us know your preferred path forward within 7 days.

Best regards,
EventRelay Team
```

### Template 3: For PRs with Merge Conflicts

```markdown
## 🔀 Merge Conflict Resolution

Hi @{AUTHOR},

Your PR has merge conflicts. Good news - we can help!

### What Caused This:
Recent code quality improvements including:
- Import reorganization (17 files)
- Syntax fixes (8 files)
- Formatting cleanup

### Resolution Steps:
1. **Fetch latest:** `git fetch origin main`
2. **Rebase:** `git rebase origin/main`
3. **Resolve conflicts** (likely imports/formatting)
4. **Verify:** `ruff check src`
5. **Push:** `git push --force-with-lease`

### Need Help?
- Conflicts in imports? Use the [new pattern](FINAL_SUMMARY.md#import-organization)
- Stuck? Comment here and we'll assist
- Alternative: We can rebase for you (with permission)

Let us know how we can help! 🤝
```

### Template 4: For PRs Ready to Merge

```markdown
## ✅ Ready for Final Review

Hi @{AUTHOR},

Great work! This PR looks ready to merge.

### Pre-Merge Checklist:
- [ ] Rebased on latest `main`
- [ ] All CI checks passing
- [ ] No merge conflicts
- [ ] Code reviewed by maintainer
- [ ] Tests passing (if applicable)

### Timeline:
We aim to merge approved PRs within 3 business days.

### Next Steps:
A maintainer will conduct final review and merge. Thank you for your contribution! 🎊

---
*Note: Recent code quality improvements mean your PR benefits from a cleaner baseline!*
```

---

## Response Decision Tree

```
START: New PR Comment/Update
    │
    ├─→ Is PR < 7 days old?
    │   └─→ YES: Use Template 1 (if Python files affected)
    │   └─→ NO: Continue
    │
    ├─→ Is PR > 30 days old?
    │   └─→ YES: Use Template 2 (Status Check)
    │   └─→ NO: Continue
    │
    ├─→ Does PR have merge conflicts?
    │   └─→ YES: Use Template 3 (Resolution Help)
    │   └─→ NO: Continue
    │
    ├─→ All checks passing + approved?
    │   └─→ YES: Use Template 4 (Ready to Merge)
    │   └─→ NO: Standard review process
```

---

## Automation Opportunities

### GitHub Actions Workflow for Auto-Commenting:

```yaml
name: PR Auto-Comment
on:
  pull_request:
    types: [opened, reopened, synchronize]

jobs:
  comment:
    runs-on: ubuntu-latest
    steps:
      - name: Check if Python files modified
        id: check
        uses: dorny/paths-filter@v2
        with:
          filters: |
            python:
              - 'src/**/*.py'
              - 'tests/**/*.py'
      
      - name: Comment on PR
        if: steps.check.outputs.python == 'true'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## 🎉 Python PR Detected\n\nGreat! This PR modifies Python files. Please ensure:\n- [ ] `ruff check src` passes\n- [ ] Imports are organized per PEP 8\n- [ ] Tests updated (if applicable)\n\nSee [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.'
            })
```

### Stale PR Checker:

```yaml
name: Stale PR Check
on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday

jobs:
  stale:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/stale@v8
        with:
          stale-pr-message: >
            This PR has been open for 30+ days. Recent code improvements
            may require rebasing. Please update or close within 7 days.
          days-before-stale: 30
          days-before-close: 7
          stale-pr-label: 'stale'
```

---

## Manual Review Checklist

When reviewing PRs manually, verify:

### Code Quality:
- [ ] Passes `ruff check src`
- [ ] Imports organized per PEP 8
- [ ] No syntax errors (Python compilation succeeds)
- [ ] Type hints used where appropriate
- [ ] No security vulnerabilities introduced

### Testing:
- [ ] Existing tests pass
- [ ] New tests added for new features
- [ ] Test coverage maintained or improved
- [ ] Edge cases considered

### Documentation:
- [ ] README updated (if public API changed)
- [ ] Docstrings added/updated
- [ ] CHANGELOG.md updated (for releases)
- [ ] Comments added for complex logic

### Git Hygiene:
- [ ] Clean commit history (squash if needed)
- [ ] Descriptive commit messages
- [ ] No merge commits (rebase preferred)
- [ ] Branch up-to-date with main

### CI/CD:
- [ ] All workflow checks passing
- [ ] Build succeeds
- [ ] No new linting errors introduced
- [ ] Security scans pass (CodeQL, Trivy)

---

## Escalation Process

### When to Escalate:

1. **Security Issues:** Immediately notify @groupthinking
2. **Breaking Changes:** Require maintainer approval
3. **Large Refactors:** Schedule review meeting
4. **Controversial Changes:** Seek team consensus
5. **Dependency Updates:** Verify compatibility first

### Contact Points:
- **General Questions:** PR comments
- **Security Issues:** security@eventrelay.io (if available)
- **Urgent Issues:** @groupthinking on GitHub
- **Team Discussion:** GitHub Discussions or Slack

---

## Metrics to Track

### PR Health Indicators:
- **Time to First Response:** Target < 24 hours
- **Time to Merge:** Target < 7 days (for approved PRs)
- **Stale PR Rate:** Target < 10% over 30 days
- **Merge Conflict Rate:** Track after improvements
- **Rebase Success Rate:** Monitor after code quality changes

### Code Quality Metrics:
- **Linting Errors:** Currently 154 (down from 205)
- **Test Coverage:** Track per PR
- **Security Vulnerabilities:** 0 critical/high target
- **Build Success Rate:** Target > 95%

---

## Best Practices

### For PR Authors:
1. **Keep PRs Small:** < 400 lines of code ideal
2. **One Feature Per PR:** Easier to review
3. **Update Tests:** Always include test coverage
4. **Run Linting:** Use `ruff check src` before committing
5. **Descriptive Titles:** Use conventional commits format

### For Reviewers:
1. **Timely Reviews:** Respond within 24 hours
2. **Constructive Feedback:** Be specific and helpful
3. **Approve When Ready:** Don't block unnecessarily
4. **Use Templates:** Consistent communication
5. **Track Follow-ups:** Ensure action items completed

### For Maintainers:
1. **Merge Promptly:** Don't let approved PRs languish
2. **Communicate Changes:** Use templates above
3. **Monitor Metrics:** Track PR health indicators
4. **Update SOP:** Revise based on experience
5. **Celebrate Contributors:** Recognize good work

---

## Appendix A: Quick Commands

### For PR Authors:
```bash
# Rebase on main
git fetch origin main
git rebase origin/main

# Check linting
ruff check src

# Run tests
pytest tests/

# Force push after rebase
git push --force-with-lease
```

### For Reviewers:
```bash
# Checkout PR
gh pr checkout {PR_NUMBER}

# Review changes
git diff main...HEAD

# Check linting
ruff check src

# Run tests
pytest tests/

# Comment on PR
gh pr comment {PR_NUMBER} -b "LGTM! 🎉"
```

### For Maintainers:
```bash
# List open PRs
gh pr list --limit 20

# View PR details
gh pr view {PR_NUMBER}

# Merge PR
gh pr merge {PR_NUMBER} --squash --delete-branch

# Check CI status
gh pr checks {PR_NUMBER}
```

---

## Appendix B: Related Documentation

- [FINAL_SUMMARY.md](FINAL_SUMMARY.md) - Complete improvement summary
- [PROGRESS_REPORT.md](PROGRESS_REPORT.md) - Detailed progress tracking
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CI_BUILD_INVESTIGATION_REPORT.md](CI_BUILD_INVESTIGATION_REPORT.md) - Full CI analysis

---

## Revision History

| Version | Date       | Author         | Changes                    |
|---------|------------|----------------|----------------------------|
| 1.0     | 2026-02-05 | GitHub Actions | Initial SOP creation       |

---

**Questions or Feedback?**  
Open an issue or discussion in the EventRelay repository.
