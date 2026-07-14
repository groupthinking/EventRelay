import json
import re
from collections import defaultdict

def analyze_prs(file_path):
    with open(file_path) as f:
        prs = json.load(f)

    open_numbers = {pr["number"] for pr in prs}
    pr_map = {pr["number"]: pr for pr in prs}

    stale_candidates = {} # stale_num -> {newer_num: reason}

    # 1. Explicit references
    for pr in prs:
        num = pr["number"]
        body = pr.get("body") or ""
        title = pr.get("title") or ""
        text = (title + " " + body).lower()

        # Pattern: "supersedes #123"
        matches = re.findall(r"supersedes\s+(?:PR\s+)?#(\d+)", text)
        for m in matches:
            stale_num = int(m)
            if stale_num in open_numbers:
                stale_candidates[stale_num] = {"newer": num, "reason": "Explicitly superseded in PR description"}

        # Pattern: "superseded by #123"
        matches = re.findall(r"superseded\s+by\s+(?:PR\s+)?#(\d+)", text)
        for m in matches:
            newer_num = int(m)
            if newer_num in open_numbers:
                stale_candidates[num] = {"newer": newer_num, "reason": "Self-identified as superseded in PR description"}

    # 2. Group by author and find similar titles
    author_prs = defaultdict(list)
    for pr in prs:
        author_prs[pr["user"]["login"]].append(pr)

    for author, author_list in author_prs.items():
        # Sort by number (ascending, so older first)
        author_list.sort(key=lambda x: x["number"])

        for i in range(len(author_list)):
            for j in range(i + 1, len(author_list)):
                pr_old = author_list[i]
                pr_new = author_list[j]

                title_old = pr_old["title"].lower()
                title_new = pr_new["title"].lower()

                # Simple similarity: if one title is a substring of another or they share significant keywords
                # Especially if they contain "Implement Redis consumer for orchestrator" etc.

                # Normalize titles for comparison (remove "WIP", tags, etc)
                def normalize(t):
                    t = re.sub(r"\[.*?\]", "", t)
                    t = re.sub(r"\(.*?\)", "", t)
                    t = re.sub(r"feat:|fix:|chore:|test:|refactor:|🧪|⚡|🔒|🎨|🧹", "", t)
                    return t.strip().lower()

                norm_old = normalize(title_old)
                norm_new = normalize(title_new)

                if norm_old == norm_new and norm_old != "":
                    if pr_old["number"] not in stale_candidates:
                        stale_candidates[pr_old["number"]] = {"newer": pr_new["number"], "reason": f"Duplicate title from same author ({author})"}

                # Check for "Implement Redis consumer for orchestrator" similarity
                if "redis consumer" in norm_old and "redis consumer" in norm_new:
                     if pr_old["number"] not in stale_candidates:
                        stale_candidates[pr_old["number"]] = {"newer": pr_new["number"], "reason": f"Similar content: Redis consumer ({author})"}

    # 3. Specifically check the merge-conflict clusters
    # Titles: "fix(main): resolve committed merge-conflict markers..."
    # #735, #736, #737, #695, #700
    conflict_prs = [pr for pr in prs if "merge-conflict markers" in pr["title"].lower() or "merge conflicts" in pr["title"].lower()]
    conflict_prs.sort(key=lambda x: x["number"])
    if len(conflict_prs) > 1:
        newest_conflict = conflict_prs[-1]
        for pr in conflict_prs[:-1]:
            if pr["number"] not in stale_candidates:
                stale_candidates[pr["number"]] = {"newer": newest_conflict["number"], "reason": "Superseded by more comprehensive merge conflict fix"}

    # 4. Specifically check batch query execution
    # #716, #747, #749
    batch_query_prs = [pr for pr in prs if "batch query execution" in pr["title"].lower()]
    batch_query_prs.sort(key=lambda x: x["number"])
    if len(batch_query_prs) > 1:
        newest_batch = batch_query_prs[-1]
        for pr in batch_query_prs[:-1]:
            if pr["number"] not in stale_candidates:
                 stale_candidates[pr["number"]] = {"newer": newest_batch["number"], "reason": "Superseded by newer batch query optimization"}

    # Output results
    results = []
    for stale_num, info in stale_candidates.items():
        stale_pr = pr_map[stale_num]
        newer_pr = pr_map[info["newer"]]
        results.append({
            "stale_number": stale_num,
            "stale_title": stale_pr["title"],
            "newer_number": info["newer"],
            "newer_title": newer_pr["title"],
            "reason": info["reason"]
        })

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    analyze_prs("open_prs_full.json")
