# Remotes Migration Single Source of Truth

This document is the definitive single source of truth (SSOT) for the remotes migration, tracking all remote branches, active/resolved status, and their respective parallel execution packages as part of the Phase 4 MVP YouTube-to-Repo framework.

## 1. Local and Remote Branch Inventory

Based on a repository-wide git scan and audit matrix, here is the full inventory of remote branches, correlated with their PR status, age, and remediation verdicts.

| Branch Category | Remote Name | Associated PR | Verdict / Status | Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **Performance (Bolt)** | `bolt-fix-database-optimizer-n1-queries-14843617805558882255` | - | **REVIEW** | Merge clean optimizations |
| | `bolt-memoize-segment-row-14076716723355865204` | - | **REVIEW** | Trace segment row optimizations |
| | `bolt/fix-batch-query-n1-bottleneck-16664381751066617032` | - | **REVIEW** | Superseded by #749 batch queries |
| **UX/UI (Palette)** | `palette-a11y-improvements-8526728425873563248` | #811 (Open) | **ACTIVE** | UX and A11y enhancements |
| | `palette-add-aria-label-search-input-11565478109907226861` | #812 (Open) | **ACTIVE** | Search input accessibility labels |
| | `palette/a11y-video-generator-15541785465389385126` | - | **REVIEW** | Accessibility audits |
| **Security (Sentinel)** | `sentinel-security-fix-md5-6305435416460063457` | #651 (Open) | **ACTIVE** | SHA-256 migration and secure hash check |
| **Feature (Vera)** | `feat/vera-platform` | #297 (Closed) | **RESOLVED** | Already merged to main |
| | `feat/sentry-nextjs` | #296 (Closed) | **RESOLVED** | Already merged to main |
| **Agent Prototyping (Claude)**| `claude/dazzling-edison-0468aj` | #388 (Closed) | **RESOLVED** | Already merged / superseded |
| | `claude/dazzling-edison-ntgy52` | #389 (Closed) | **RESOLVED** | Already merged / superseded |
| | `claude/determined-maxwell-06popt` | #442 (Open) | **ACTIVE** | Continue Maxwell session integrations |
| | `claude/evaluate-unused-folders` | #439 (Open) | **ACTIVE** | Clean up bloat in directories |
| **V0 Exploration** | `v0/ultrathinking-6aaf1beb` | #441 (Closed) | **RESOLVED** | Already merged to main |
| | `v0/ultrathinking-588aba59` | - | **REVIEW** | Stale architectural exploration |

---

## 2. Project Tab Work Packages

To avoid conflicting work packages, tasks are organized into four parallel, distinct sessions mapped below. Each package has its own playbook, tags, and ACU (Agent Compute Unit) limits.

```
       [Main Remotes Migration]
                  │
 ┌────────────────┼────────────────┬────────────────┐
 ▼                ▼                ▼                ▼
[Package-01]     [Package-02]     [Package-03]     [Package-04]
Performance      Security         UX/A11y          Clean-Up
```

### Package-01: Performance Optimization (Bolt)
*   **Prompt**: Identify, measure, and optimize all batch and database queries. Mitigate N+1 database queries inside transcript active segment calculations. Ensure O(log N) binary search handles time-series transcript segment matching.
*   **Playbook**: `bolt-performance-remediation`
*   **Tags**: `performance`, `db-optimization`, `time-series`
*   **ACU Limit**: 150 ACUs
*   **Assigned Branches**: `bolt-fix-database-optimizer-n1-queries...`, `bolt/fix-batch-query-n1-bottleneck...`

### Package-02: Security Hardening (Sentinel)
*   **Prompt**: Audit codebase for insecure MD5 hashes. Replace all occurrences with SHA-256 hex digests. Ensure secure headers (X-Frame-Options, X-Content-Type-Options) are strictly enforced in the production server gateway, and resolve all insecure exception handling.
*   **Playbook**: `sentinel-security-audit-and-remediation`
*   **Tags**: `security`, `sha256-migration`, `gateway-hardening`
*   **ACU Limit**: 120 ACUs
*   **Assigned Branches**: `sentinel-security-fix-md5-6305435416460063457`

### Package-03: User Experience & Accessibility (Palette)
*   **Prompt**: Enhance active player keyboard navigation, focus indicators, and screen reader announcements. Add complete aria-labels and descriptions to search fields, media buttons, and video transcript controls to ensure full WCAG 2.1 AA compliance.
*   **Playbook**: `palette-a11y-standards-remediation`
*   **Tags**: `ux`, `accessibility`, `wcag-compliance`
*   **ACU Limit**: 100 ACUs
*   **Assigned Branches**: `palette-a11y-improvements...`, `palette-add-aria-label-search-input...`

### Package-04: Directory Cleanup and Refactoring
*   **Prompt**: Audit and migrate unused root directories and legacy prototypes into standard project hierarchies. Safely delete empty directories, remove duplicated or stale scripts, and archive deprecated modules to improve codebase understandability.
*   **Playbook**: `repository-clean-and-audit`
*   **Tags**: `refactoring`, `code-health`, `cleanup`
*   **ACU Limit**: 80 ACUs
*   **Assigned Branches**: `claude/evaluate-unused-folders`, `claude/explore-codebase-implementation-plan`

---

## 3. Parallel Session Launch Strategy

These parallel sessions can be launched programmatically using the `SessionOrchestrationManager`. The orchestration script will schedule and monitor all 4 packages simultaneously and wait for complete execution, logging stats and ensuring complete compliance with the Phase 4 MVP blueprint.
