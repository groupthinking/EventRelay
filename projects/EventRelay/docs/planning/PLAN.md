# TASK: Duplicate File & Near-Duplicate Discovery

## 1. Goal & Scope
* **Objective:** Automatically discover exact and near-duplicate files in the repository and output a probability-scored report so we can clean redundancies with confidence.
* **Context:** Duplicates bloat the codebase, hinder maintenance, and violate the clean-indexing rule. We need an automated scanner integrated into the project toolchain.
* **Scope:**
    * Create `scripts/duplicate_scan.py` (new).
    * Modify `Makefile` to add `scan-dupes` target.
    * Output report in `reports/duplicate_report.md`.
    * *Initial Check:* No existing duplicate-scan script found; creating new file.

## 2. Execution Plan
- [ ] Write Python script to:
  - Walk repo, group files by (size, extension).
  - Hash files (SHA-256) → exact duplicate detection.
  - For size-match but hash-different groups, compute difflib `SequenceMatcher` ratio → near-duplicate score.
  - Produce Markdown table with probability estimates (`prob_duplicate = max(hash_match?1 : ratio)`).
- [ ] Add CLI args: `--root`, `--threshold` (near-dup cutoff, default 0.9).
- [ ] Makefile target `scan-dupes` → `python3 scripts/duplicate_scan.py --root . > reports/duplicate_report.md`.
- [ ] Write minimal unit test under `tests/test_duplicate_scan.py` verifying detection on synthetic files.

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Running `make scan-dupes` generates `reports/duplicate_report.md` listing duplicates with probability scores, and exits 0.
* **Verification Method:**
  1. Create temp folder with intentionally duplicated/near-duplicated files inside tests; run scanner; assert correct rows.
  2. Execute on full repo; ensure report not empty and script finishes under 60 s.
* **Proof Artifact:** Will attach snippet of report and test log after completion.

## 4. Post-Task Reflection
* **What was done:** _TBD_
* **Why it was needed:** _TBD_
* **How it was tested:** _TBD_