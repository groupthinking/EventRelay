#!/usr/bin/env bash
#
# branch-fail-test.sh — data-driven branch-cleanup assessment harness for EventRelay.
#
# Runs a battery of pass/fail "gates" against every remote branch and emits a
# decision matrix (markdown + CSV) so a keep/close call is backed by evidence
# rather than guesswork. Built to stay honest across a rewritten `main` history
# (a secret-purge force-push orphaned older branches), where naive three-dot
# git diffs lie — so the verdict leans on PR state + a real merge probe.
#
# Usage:
#   scripts/maintenance/branch-fail-test.sh                 # cheap gates only (seconds)
#   scripts/maintenance/branch-fail-test.sh --build         # also run the CI fail-test per branch (slow)
#   scripts/maintenance/branch-fail-test.sh --pr-json FILE  # enrich with GitHub PR state (head.ref|state|number per line)
#
# Output: docs/branch-cleanup-matrix.md and docs/branch-cleanup-matrix.csv
#
# Gates (each contributes evidence to the verdict):
#   G1 PR-STATE     open PR -> KEEP; closed PR -> decision already made, ref preserved by GitHub;
#                   no PR -> ambiguous, lean on the other gates.
#   G2 REDUNDANCY   is the branch tip an ancestor of main / fully cherry-absorbed? (zero unique work)
#   G3 MERGE-CLEAN  does `git merge-tree` against main produce conflicts? (stale/un-landable)
#   G4 UNIQUE-DIFF  two-dot file/LOC delta vs main (how much would actually be lost)
#   G5 STALENESS    age of last commit + commits-behind-main
#   G6 CI-FAILTEST  (optional, --build) checkout + install + lint/type/test; a branch that
#                   fails its own CI, has no open PR and is stale is not salvageable as-is.
#
# Verdict rule:
#   KEEP            -> open PR, OR recent (<14d) with unique unmerged work that merges clean
#   CLOSE-SAFE      -> closed PR, OR fully redundant (ancestor/absorbed, zero unique diff)
#   CLOSE-STALE     -> no PR, stale (>30d), superseded/duplicate, doesn't merge clean
#   REVIEW          -> no PR but recent and/or carries unique clean-merging work
#
set -uo pipefail

MAIN="origin/main"
RUN_BUILD=0
PR_JSON=""
OUT_MD="docs/branch-cleanup-matrix.md"
OUT_CSV="docs/branch-cleanup-matrix.csv"
STALE_DAYS=30
RECENT_DAYS=14

while [ $# -gt 0 ]; do
  case "$1" in
    --build) RUN_BUILD=1 ;;
    --pr-json) PR_JSON="$2"; shift ;;
    --out-md) OUT_MD="$2"; shift ;;
    --out-csv) OUT_CSV="$2"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

git fetch --all --prune --quiet 2>/dev/null || echo "warn: fetch failed, using local refs" >&2
now=$(date +%s)

pr_state() { # $1 = branch ; echoes "state #num" or "none"
  [ -z "$PR_JSON" ] && { echo "none"; return; }
  local hit; hit=$(grep -F "$1|" "$PR_JSON" | head -1)
  [ -z "$hit" ] && { echo "none"; return; }
  echo "$hit" | awk -F'|' '{print $2" #"$3}'
}

ci_failtest() { # $1 = branch ; echoes pass|fail|skip  (heavy)
  [ "$RUN_BUILD" -eq 0 ] && { echo "skip"; return; }
  local wt; wt=$(mktemp -d)
  if ! git worktree add --quiet --detach "$wt" "origin/$1" 2>/dev/null; then echo "skip"; return; fi
  ( cd "$wt"
    local ok=1
    if [ -f pyproject.toml ]; then
      python -m pip install -e '.[dev]' --quiet 2>/dev/null || ok=0
      ruff check src/ 2>/dev/null || ok=0
      pytest -q -m "not slow" 2>/dev/null || ok=0
    fi
    if [ -f package.json ]; then
      npm install --silent 2>/dev/null || ok=0
      npx turbo run build lint 2>/dev/null || ok=0
    fi
    [ "$ok" -eq 1 ] && echo pass || echo fail
  )
  git worktree remove --force "$wt" 2>/dev/null
  rm -rf "$wt"
}

verdict() { # args: pr ancestor uniqfiles cleanmerge agedays behind
  local pr="$1" anc="$2" uf="$3" clean="$4" age="$5" behind="$6"
  case "$pr" in
    open*) echo "KEEP"; return ;;
    closed*) echo "CLOSE-SAFE"; return ;;
  esac
  [ "$anc" = "yes" ] && { echo "CLOSE-SAFE"; return; }                      # fully contained in main
  [ "$uf" = "0" ] && { echo "CLOSE-SAFE"; return; }                        # no unique content
  # Pre-rewrite orphan: very stale AND far behind main. `clean=yes` is a false
  # positive here (unrelated trees don't textually conflict), so trust age+behind.
  if [ "$age" -gt "$STALE_DAYS" ] && [ "$behind" -gt 50 ]; then echo "CLOSE-STALE"; return; fi
  if [ "$age" -gt "$STALE_DAYS" ] && [ "$clean" = "no" ]; then echo "CLOSE-STALE"; return; fi
  echo "REVIEW"
}

printf "branch,pr,ancestor_of_main,cherry_unmerged,merges_clean,uniq_files,uniq_loc,behind,age_days,ci_failtest,verdict\n" > "$OUT_CSV"

{
echo "# EventRelay — Branch Cleanup Decision Matrix"
echo
echo "_Generated $(date -u +%Y-%m-%dT%H:%MZ) by \`scripts/maintenance/branch-fail-test.sh\`._"
echo
echo "| Branch | PR | Ancestor | Cherry≠main | Clean-merge | Δfiles | Δloc | Behind | Age(d) | CI | Verdict |"
echo "|---|---|---|---|---|---|---|---|---|---|---|"
} > "$OUT_MD"

for b in $(git branch -r | grep -v HEAD | grep -v "$MAIN\$" | sed 's#origin/##' | sort); do
  tip="origin/$b"
  pr=$(pr_state "$b")
  # G2 redundancy
  if git merge-base --is-ancestor "$tip" "$MAIN" 2>/dev/null; then anc="yes"; else anc="no"; fi
  cherry=$(git cherry "$MAIN" "$tip" 2>/dev/null | grep -c '^+')
  # G3 clean-merge probe
  conf=$(git merge-tree --write-tree "$MAIN" "$tip" 2>/dev/null | grep -c '^CONFLICT')
  [ "$conf" -gt 0 ] && clean="no" || clean="yes"
  # G4 unique diff (two-dot full-tree delta; --diff-filter to ignore deletions caused by branch lacking main's progress)
  stat=$(git diff --shortstat "$MAIN" "$tip" 2>/dev/null)
  uf=$(echo "$stat" | grep -oE '[0-9]+ file' | grep -oE '[0-9]+'); uf=${uf:-0}
  ul=$(echo "$stat" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+'); ul=${ul:-0}
  # G5 staleness
  behind=$(git rev-list --count "$tip..$MAIN" 2>/dev/null); behind=${behind:-0}
  cdate=$(git log -1 --format=%ct "$tip" 2>/dev/null); cdate=${cdate:-$now}
  age=$(( (now - cdate) / 86400 ))
  # G6 ci
  ci=$(ci_failtest "$b")
  v=$(verdict "$pr" "$anc" "$uf" "$clean" "$age" "$behind")

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$b" "${pr// /}" "$anc" "$cherry" "$clean" "$uf" "$ul" "$behind" "$age" "$ci" "$v" >> "$OUT_CSV"
  printf '| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | **%s** |\n' \
    "$b" "$pr" "$anc" "$cherry" "$clean" "$uf" "$ul" "$behind" "$age" "$ci" "$v" >> "$OUT_MD"
done

{
echo
echo "## Verdict tally"
echo '```'
awk -F, 'NR>1{c[$NF]++} END{for(k in c) printf "%-12s %d\n", k, c[k]}' "$OUT_CSV" | sort
echo '```'
echo
echo "Legend — **KEEP**: active/open PR or recent unique work · **CLOSE-SAFE**: PR already closed, or"
echo "tip fully contained in \`main\` (zero unique work to lose) · **CLOSE-STALE**: no PR, stale,"
echo "superseded, won't merge clean · **REVIEW**: no PR but recent/unique — needs a human glance."
} >> "$OUT_MD"

echo "Wrote $OUT_MD and $OUT_CSV"
