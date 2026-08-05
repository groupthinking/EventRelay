#!/usr/bin/env bash
#
# archive-and-prune-branches.sh — archive-tag then delete the branches the
# 2026-08-05 audit found unrecoverable, and nothing else.
#
# WHY THIS EXISTS AS A SCRIPT RATHER THAN AN APPLIED CHANGE
# ---------------------------------------------------------
# The audit ran in a Claude Code session whose git credentials are scoped to a
# single feature branch. Creating the archive tags failed there:
#
#   $ git push origin refs/tags/archive/addressing-issues-grv-194-a1c2
#   error: RPC failed; HTTP 403
#
# Branch deletion appeared to be permitted (a --dry-run succeeded), but
# deleting without the archive tags in place would remove the only durable
# recovery path, so nothing was deleted. Run this with credentials that can
# write tags.
#
# WHAT THE VERDICTS MEAN
# ----------------------
# `main` was force-pushed for a secret purge (see CLAUDE.md -> Repo Hygiene).
# Branches created before that share NO ancestry with today's `main`:
#
#   $ git merge-base origin/main origin/<branch>
#   (empty)
#
# That emptiness is the verdict signal, and it is the one that stays honest
# after a rewrite. The usual signals do not:
#   * `git merge-tree` reports these orphans as merging CLEAN (unrelated trees
#     do not textually conflict -- they would clobber).
#   * A two-dot diff against an empty merge base silently degrades to a
#     working-tree diff, which is why a two-line Dependabot bump measures as
#     111 files / 15,650 lines.
#   * The purge rewrote committer dates, so every branch looks "recent" and
#     staleness thresholds never fire.
#
#   KEEP-OPEN-PR    28  open PR -- never touched by this script
#   REVIEW-SHARED   29  real shared ancestry, no open PR -- NOT deleted here
#   CLOSE-MERGED     2  tip is an ancestor of main -- nothing to lose
#   CLOSE-ORPHANED 275  no common ancestor with main -- no rebase recovers them
#
# Only CLOSE-MERGED and CLOSE-ORPHANED are pruned: 277 branches.
#
# RECOVERY
# --------
#   git push origin archive/<branch>:refs/heads/<branch>
# GitHub also restores deleted branches through the UI for ~90 days.
#
# USAGE
#   ./scripts/maintenance/archive-and-prune-branches.sh            # dry run (default)
#   ./scripts/maintenance/archive-and-prune-branches.sh --execute  # tag, verify, then delete

set -euo pipefail

CSV="${CSV:-docs/branch-audit-2026-08-05.csv}"
REMOTE="${REMOTE:-origin}"
BATCH="${BATCH:-15}"
EXECUTE=0
[ "${1:-}" = "--execute" ] && EXECUTE=1

[ -f "$CSV" ] || { echo "missing $CSV" >&2; exit 1; }

# Protected refs are filtered here and re-checked below. The audit that
# produced this CSV originally classified `main` itself as CLOSE-MERGED --
# `git merge-base --is-ancestor origin/main origin/main` is trivially true --
# which would have deleted the default branch. The row is gone from the CSV,
# and this guard makes the mistake unrepeatable no matter what the CSV says.
PROTECTED_RE='^(main|master|HEAD)$'

mapfile -t TARGETS < <(
  awk -F, 'NR>1 && ($2=="CLOSE-ORPHANED" || $2=="CLOSE-MERGED"){print $1}' "$CSV" \
    | grep -Ev "$PROTECTED_RE"
)

for b in "${TARGETS[@]}"; do
  if [[ "$b" =~ $PROTECTED_RE ]]; then
    echo "ABORT: protected branch '$b' reached the delete list." >&2
    exit 1
  fi
done

DEFAULT_REF="$(git symbolic-ref -q "refs/remotes/$REMOTE/HEAD" 2>/dev/null || true)"
DEFAULT_BRANCH="${DEFAULT_REF##*/}"
if [ -n "$DEFAULT_BRANCH" ]; then
  for b in "${TARGETS[@]}"; do
    if [ "$b" = "$DEFAULT_BRANCH" ]; then
      echo "ABORT: '$b' is $REMOTE's default branch." >&2
      exit 1
    fi
  done
fi

echo "branches selected for pruning: ${#TARGETS[@]}"
if [ "${#TARGETS[@]}" -eq 0 ]; then echo "nothing to do"; exit 0; fi

if [ "$EXECUTE" -eq 0 ]; then
  echo
  echo "DRY RUN -- nothing will change. Re-run with --execute to apply."
  echo "First 10 targets:"
  printf '  %s\n' "${TARGETS[@]:0:10}"
  echo "  ..."
  echo
  echo "Each target would get: git tag archive/<b> origin/<b>; push tag; push --delete <b>"
  exit 0
fi

# --- phase 1: create and push archive tags -------------------------------
echo "== phase 1: archive tags =="
for b in "${TARGETS[@]}"; do
  git tag -f "archive/$b" "refs/remotes/$REMOTE/$b" >/dev/null
done

pending=()
for b in "${TARGETS[@]}"; do pending+=("refs/tags/archive/$b"); done

for ((i = 0; i < ${#pending[@]}; i += BATCH)); do
  chunk=("${pending[@]:i:BATCH}")
  if ! git push "$REMOTE" "${chunk[@]}" >/dev/null 2>&1; then
    for ref in "${chunk[@]}"; do
      git push "$REMOTE" "$ref" >/dev/null 2>&1 || echo "  tag push FAILED: $ref" >&2
    done
  fi
done

# --- phase 2: verify every tag landed before deleting anything -----------
echo "== phase 2: verify =="
git ls-remote --tags "$REMOTE" 'refs/tags/archive/*' \
  | sed 's/\^{}//' | awk '{print $2}' | sed 's#refs/tags/##' | sort -u > /tmp/.archived_ok

missing=0
for b in "${TARGETS[@]}"; do
  grep -qxF "archive/$b" /tmp/.archived_ok || { echo "  NOT ARCHIVED: $b" >&2; missing=$((missing + 1)); }
done

if [ "$missing" -gt 0 ]; then
  echo "ABORT: $missing branch(es) have no archive tag on $REMOTE. Nothing deleted." >&2
  exit 1
fi
echo "  all ${#TARGETS[@]} archive tags confirmed on $REMOTE"

# --- phase 3: delete ------------------------------------------------------
echo "== phase 3: delete =="
for ((i = 0; i < ${#TARGETS[@]}; i += BATCH)); do
  chunk=("${TARGETS[@]:i:BATCH}")
  if ! git push "$REMOTE" --delete "${chunk[@]}" >/dev/null 2>&1; then
    for b in "${chunk[@]}"; do
      git push "$REMOTE" --delete "$b" >/dev/null 2>&1 || echo "  delete FAILED: $b" >&2
    done
  fi
done

echo "done. recover any branch with:"
echo "  git push $REMOTE archive/<branch>:refs/heads/<branch>"
