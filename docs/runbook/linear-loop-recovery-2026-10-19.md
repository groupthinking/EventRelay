# Linear loop recovery runbook — 2026-10-19 audit (#2449)

## Purpose

This runbook is the execution gate for the Linear loop recovery audit dated 2026-10-19.
Do not mark recovery complete until funding and all three retained-loop verification runs are recorded with evidence.

## Scope and fixed constraints

- Workspace: `myxstack`.
- Keep auto reload OFF.
- Stop immediately if the checkout total exceeds the approved amount.
- Do not replay historical failed runs.
- Run only one retained workflow at a time via `Run now`.
- Keep the 13 paused recurrences paused.

## Funding approval gate (must pass first)

| Field | Required value |
| --- | --- |
| Outstanding balance | `$76.50` (usage page shows `$77` rounded) |
| Additional funds shown in approved scenario | `$10` custom add |
| Checkout total shown in approved scenario | `$87` |
| Auto reload | Disabled |
| Plan change | Not required (Enterprise `$30/user/month` billed annually, 1 user) |

Record approval before purchase:

| Field | Value |
| --- | --- |
| Approver | `PENDING` |
| Approved max charge | `PENDING` |
| Approval timestamp (UTC) | `PENDING` |
| Terms accepted and purchase submitted | `PENDING` |
| Actual final charge shown at checkout | `PENDING` |
| Stop-condition check (`actual <= approved`) | `PENDING` |

If `actual > approved`, stop and escalate before any run.

## Retained loops allowed in this recovery

| Priority | Loop | URL |
| --- | --- | --- |
| 1 | EventRelay daily control review (3am schedule retained) | https://linear.app/myxstack/loop/eventrelay-daily-control-review-e205542b281b |
| 2 | High-priority stale issue review - daily 1pm | https://linear.app/myxstack/loop/high-priority-stale-issue-review-daily-1pm-d1bef9d1b4a8 |
| 3 | Stuck review follow-up - daily 1pm | https://linear.app/myxstack/loop/stuck-review-follow-up-daily-1pm-e682f1ea0e54 |

## Verification protocol (run after funding gate passes)

For each retained loop, in order:

1. Recheck positive balance, spend limits, and saved read-only prompt before clicking `Run now`.
2. Execute one loop only.
3. Require terminal success.
4. Require source-linked findings, or a justified zero-item result.
5. Require explicit scope/coverage statement in output.
6. Confirm no unintended issue writes and no unintended code writes.
7. Record actual run cost from usage analytics.
8. If any requirement fails, stop and remediate before running the next loop.

## Evidence log (fill as executed)

| Loop | Run URL | Terminal status | Findings evidence | Scope/coverage stated | No unintended writes confirmed | Actual cost | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EventRelay daily control review | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| High-priority stale issue review | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |
| Stuck review follow-up | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` |

## Required paused state (must remain unchanged during recovery)

Keep these 13 schedules paused:

- 3 extra review-follow-up times.
- 3 extra high-priority stale times.
- 4 lower-priority stale times.
- Daily stale issue intervention summary.
- Official Linear Self Index.
- Get shit done.

Any restoration is a separate decision per loop after this recovery is complete.

## Prior failure evidence (reference)

- Credit failure: https://linear.app/myxstack/loop/eventrelay-daily-control-review-e205542b281b/run/872ac8a5-df00-448d-8ecc-aa14fe43dec3
- Credit failure: https://linear.app/myxstack/loop/2-official-linear-self-index-8c0a318308ae/run/4b38bdbb-2b00-4066-832c-4ba29ed918af
- Credit failure: https://linear.app/myxstack/loop/follow-up-on-issues-stuck-in-review-every-6h-1pm-e682f1ea0e54/run/58bdda10-820b-47b8-a416-43ee2d74349a
- Skill dependency failure: https://linear.app/myxstack/loop/resolve-stale-issues-every-6h-1pm-d1bef9d1b4a8/run/78411f5a-018b-49d7-939b-dec2e9cca1df
- Balance and pricing: https://linear.app/myxstack/settings/usage
- Actual costs: https://linear.app/myxstack/settings/usage/analytics
- Spend limits: https://linear.app/myxstack/settings/usage/spend-limits

## Completion rule

Recovery is complete only when all are true:

- Funding approval record is filled and charge is within approval.
- Three retained loops each have one evidence-backed successful run.
- Each run records actual cost and either source-linked findings or justified zero items.
- No unintended writes occurred.
- The 13 paused recurrences stayed paused.
