# How to Create Production Phase Issues

This guide shows how to create the 3 production preparation issues from the templates.

## 🚀 Quick Start (Recommended)

Use the automated script to create all 3 issues at once:

```bash
cd /home/runner/work/EventRelay/EventRelay/.github/ISSUE_TEMPLATE
./create-production-issues.sh
```

This script will:
1. Check if GitHub CLI is installed and authenticated
2. Create all 3 phase issues with proper labels
3. Display the issue numbers for easy access
4. Provide next steps

## 📋 Manual Creation (Alternative)

If you prefer to create issues manually or the script doesn't work:

### Method 1: GitHub Web Interface

1. Go to: https://github.com/groupthinking/EventRelay/issues/new/choose
2. You'll see the three phase templates listed
3. Click on the template you want to use
4. Review and submit the issue

### Method 2: GitHub CLI

```bash
# Make sure you're authenticated
gh auth login

# Create Phase 1
gh issue create --repo groupthinking/EventRelay \
  --title "[PHASE 1] Security & Environment Setup" \
  --label "phase-1,security,environment,production" \
  --body-file .github/ISSUE_TEMPLATE/phase-1-security-environment.md

# Create Phase 2
gh issue create --repo groupthinking/EventRelay \
  --title "[PHASE 2] Monitoring & CI/CD Setup" \
  --label "phase-2,monitoring,cicd,infrastructure" \
  --body-file .github/ISSUE_TEMPLATE/phase-2-monitoring-cicd.md

# Create Phase 3
gh issue create --repo groupthinking/EventRelay \
  --title "[PHASE 3] Testing & Production Launch" \
  --label "phase-3,testing,production,launch" \
  --body-file .github/ISSUE_TEMPLATE/phase-3-testing-launch.md
```

## ✅ After Creating Issues

Once the issues are created:

1. **Assign to team members:**
   ```bash
   gh issue edit <issue-number> --add-assignee <username>
   ```

2. **Add to project board:**
   ```bash
   gh issue edit <issue-number> --add-project "Production Deployment"
   ```

3. **Set milestones:**
   ```bash
   gh issue edit <issue-number> --milestone "v1.0 Production"
   ```

4. **Start working on Phase 1:**
   ```bash
   gh issue view <phase-1-issue-number> --web
   ```

## 🔗 Issue Workflow

```
Phase 1 (Security) → Phase 2 (Monitoring) → Phase 3 (Testing & Launch)
     ↓                    ↓                         ↓
  Issue #X             Issue #Y                 Issue #Z
     ↓                    ↓                         ↓
  8 hours              8 hours                  8 hours
```

## 💡 Tips

- **Complete in order:** Finish Phase 1 before starting Phase 2
- **Track progress:** Use the checkboxes in each issue
- **Update regularly:** Comment on issues as you complete tasks
- **Document issues:** If you encounter problems, add comments
- **Close when done:** Only close after all success criteria are met

## 🆘 Troubleshooting

### Script fails: "gh not found"

Install GitHub CLI:
```bash
# macOS
brew install gh

# Linux
sudo apt install gh  # or yum install gh

# Windows
winget install GitHub.cli
```

### Script fails: "Not authenticated"

Authenticate with GitHub:
```bash
gh auth login
# Follow the prompts
```

### Can't find templates in web UI

Make sure the files exist:
```bash
ls -la .github/ISSUE_TEMPLATE/
```

If files are missing, pull the latest changes:
```bash
git pull origin main
```

## 📞 Need Help?

- Check `.github/ISSUE_TEMPLATE/README.md` for detailed information
- Ask in team chat or create a discussion
- Tag @groupthinking for repository owner assistance

---

**Remember:** These issues guide the production preparation. Follow them carefully and check off tasks as you complete them!
