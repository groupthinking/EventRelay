import argparse
import hashlib
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple


BUFFER_SIZE = 65536  # 64 KiB


def sha256_for_file(path: Path) -> str:
    """Compute SHA-256 hash for a file efficiently."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(BUFFER_SIZE):
            h.update(chunk)
    return h.hexdigest()


def walk_files(root: Path) -> List[Path]:
    """Yield all regular files under root, ignoring common VCS/build dirs."""
    ignore_dirs = {".git", "__pycache__", ".venv", "node_modules", ".idea", ".cache"}
    paths: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # mutate dirnames in-place to prune walk
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fname in filenames:
            path = Path(dirpath) / fname
            if path.is_file():
                paths.append(path)
    return paths


def group_by_size(files: List[Path]) -> Dict[int, List[Path]]:
    groups: Dict[int, List[Path]] = defaultdict(list)
    for p in files:
        try:
            size = p.stat().st_size
        except (OSError, FileNotFoundError):
            continue
        groups[size].append(p)
    # discard groups of size 1 (unique sizes cannot be duplicates)
    return {s: g for s, g in groups.items() if len(g) > 1}


def compute_exact_duplicates(size_groups: Dict[int, List[Path]]) -> Tuple[Dict[str, List[Path]], List[Path]]:
    """Return mapping hash -> files (exact duplicates) and leftovers for near-dup check."""
    exact: Dict[str, List[Path]] = defaultdict(list)
    leftovers: List[Path] = []
    for files in size_groups.values():
        hash_map: Dict[str, List[Path]] = defaultdict(list)
        for p in files:
            file_hash = sha256_for_file(p)
            hash_map[file_hash].append(p)
        for h, paths in hash_map.items():
            if len(paths) > 1:
                exact[h].extend(paths)
            else:
                leftovers.extend(paths)
    return exact, leftovers


def similarity_score(a: Path, b: Path) -> float:
    """Compute similarity ratio between two text files with difflib. Binary files fallback to 0."""
    try:
        with a.open("r", encoding="utf-8", errors="ignore") as fa, b.open("r", encoding="utf-8", errors="ignore") as fb:
            return SequenceMatcher(None, fa.read(), fb.read()).ratio()
    except Exception:
        return 0.0


def detect_near_duplicates(candidates: List[Path], threshold: float) -> List[Tuple[Path, Path, float]]:
    """Brute-force compare candidate files and return pairs exceeding threshold."""
    pairs: List[Tuple[Path, Path, float]] = []
    n = len(candidates)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = candidates[i], candidates[j]
            score = similarity_score(a, b)
            if score >= threshold:
                pairs.append((a, b, score))
    return pairs


def generate_markdown_report(exact: Dict[str, List[Path]], near: List[Tuple[Path, Path, float]]) -> str:
    lines: List[str] = [
        "# Duplicate Scan Report",
        "",
        "## Exact Duplicates",
    ]
    if exact:
        lines.append("| Hash | Count | Files |")
        lines.append("|------|-------|-------|")
        for h, paths in exact.items():
            files_str = ", ".join(str(p) for p in paths)
            lines.append(f"| {h[:10]}… | {len(paths)} | {files_str} |")
    else:
        lines.append("No exact duplicates found.")

    lines.extend(["", "## Near Duplicates (Similarity ≥ threshold)", "| File A | File B | Similarity |", "|--------|--------|-----------|"])
    if near:
        for a, b, score in near:
            lines.append(f"| {a} | {b} | {score:.2%} |")
    else:
        lines.append("| ― | ― | ― |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect exact and near-duplicate files.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root directory to scan (default: current working dir)")
    parser.add_argument("--threshold", type=float, default=0.9, help="Similarity threshold for near duplicates (0-1)")
    args = parser.parse_args()

    if not args.root.exists():
        print(f"Error: root path {args.root} does not exist.", file=sys.stderr)
        sys.exit(1)

    all_files = walk_files(args.root)
    size_groups = group_by_size(all_files)
    exact, leftovers = compute_exact_duplicates(size_groups)
    near = detect_near_duplicates(leftovers, args.threshold)

    report = generate_markdown_report(exact, near)
    print(report)


if __name__ == "__main__":
    main()
