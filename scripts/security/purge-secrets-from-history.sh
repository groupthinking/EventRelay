#!/usr/bin/env bash
#
# Purge committed secrets from git history.
#
# DESTRUCTIVE: this rewrites history and REQUIRES a force-push afterward.
# Run ONLY after every exposed credential has already been rotated/revoked —
# rewriting history does not un-leak a key that an attacker already copied.
#
# Prereq:  pip install git-filter-repo   (https://github.com/newren/git-filter-repo)
#
set -euo pipefail

# Refuse to run outside a git repo, and warn on a dirty tree before rewriting history.
git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not in a git repository."; exit 1; }
if ! git diff-index --quiet HEAD 2>/dev/null; then
  echo "⚠️  Uncommitted changes detected — commit or stash them before rewriting history."
fi

echo "⚠️  This rewrites the entire git history and will require:"
echo "      git push --force-with-lease --all && git push --force-with-lease --tags"
echo "    Confirm every exposed key has ALREADY been rotated before continuing."
read -r -p "Type 'rewrite-history' to proceed: " confirm
[ "$confirm" = "rewrite-history" ] || { echo "aborted."; exit 1; }

command -v git-filter-repo >/dev/null 2>&1 || {
  echo "git-filter-repo not found. Install with: pip install git-filter-repo"; exit 1; }

# Capture the current origin URL before filter-repo strips the remote; the URL
# varies per clone (HTTPS/SSH, fork, remote name), so re-add exactly what was set.
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo 'git@github.com:groupthinking/EventRelay.git')"

# 1) Remove files that never belonged in the repo, across ALL history.
git filter-repo --force --invert-paths \
  --path docs/ob.txt \
  --path-glob 'src/utils/notebooklm_profile/*' \
  --path-glob 'src/utils/notebooklm_profile_v2/*'

# 2) Redact secret patterns left behind in any remaining historical blobs.
REPL="$(mktemp)"
cat > "$REPL" <<'PATTERNS'
regex:AIza[0-9A-Za-z_-]{30,}==>REDACTED_GOOGLE_API_KEY
regex:sk-(proj-|ant-)?[A-Za-z0-9_-]{20,}==>REDACTED_API_KEY
regex:eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}==>REDACTED_JWT
PATTERNS
git filter-repo --force --replace-text "$REPL"
rm -f "$REPL"

cat <<DONE

✅ History rewritten locally. Next steps:
   1. Inspect: git log --stat | head, and re-run a gitleaks scan over history.
   2. Re-add the remote if filter-repo removed it:
        git remote add origin ${REMOTE_URL}
   3. Force-push:
        git push --force-with-lease --all
        git push --force-with-lease --tags
   4. Tell collaborators to re-clone (old clones still contain the secrets).
   Rotated credentials remain the real protection — history rewriting is cleanup.
DONE
