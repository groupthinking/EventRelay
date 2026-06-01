---
description: Context Window (Active Session) - Claude Verification Protocol
---

## ##memory - Claude Verification Protocol

**MANDATORY FOR EVERY OUTPUT**

### Step 1: Verification Matrix

After generating any output (code, document, plan, response), Claude MUST:

1.  **Capture User Intent**: What did the user explicitly ask for?
2.  **Recall Written Plan**: What did Claude commit to in `task.md` or `implementation_plan.md`?
3.  **Measure Output**: What was actually delivered?

### Step 2: Alignment Calculation

| Dimension                                                | Weight | Score (0-100%) |
| -------------------------------------------------------- | ------ | -------------- |
| **Functionality**: Does the output work as requested?    | 40%    | ?              |
| **Completeness**: Are all requested items addressed?     | 30%    | ?              |
| **Schema/Format**: Does output match expected structure? | 20%    | ?              |
| **Edge Cases**: Are failures/fallbacks handled?          | 10%    | ?              |

**Total Alignment Score** = Weighted Average

### Step 3: Misalignment Protocol

> [!CAUTION]
> If Total Alignment Score < 100%, Claude MUST:

1.  **Identify the Gap**: Which dimension(s) scored below 100%? Why?
2.  **Reason**: Is refactoring feasible within the current turn?
    - **YES**: Refactor immediately. Loop back to Step 1.
    - **NO**: Proceed to Step 4.

### Step 4: Mathematical Justification for Proceeding (If Refactoring Skipped)

Claude must argue why proceeding is mathematically sound:

- **Cost of Delay**: Does refactoring block higher-priority work?
- **Diminishing Returns**: Is the gap in a low-weight dimension (e.g., Edge Cases < Functionality)?
- **Known Limitation**: Is the gap due to an external constraint (e.g., missing API key, dependency)?
- **Probability of Success on Next Turn**: Can the gap be easily fixed in a follow-up?

**Example Justification**:

> "Alignment: 95%. Gap: Edge Cases (missing fallback for `yt_dlp` failure). Proceeding because:
>
> 1. Core functionality (40%) is 100%.
> 2. Edge case failure is non-blocking; user can retry.
> 3. Cost of delay (adding fallback) > benefit for this turn (estimated 15 mins vs. 2% alignment gain)."

### Application

This protocol applies to:

- Code edits
- File creations
- Terminal commands
- Architectural plans
- Responses to complex questions
