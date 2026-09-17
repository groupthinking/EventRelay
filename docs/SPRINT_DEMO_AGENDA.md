# EventRelay Sprint Demo Agenda

> **Demo boundary:** This is an internal walkthrough of repository behavior and local/test evidence. It is **not** a production deployment, a payment demonstration, or authorization to change authentication, billing, deployment, or production configuration.

**Demo owner:** `Assign before meeting`
**Target duration:** 15 minutes
**Source task:** [Confirm sprint demo agenda](https://app.notion.com/p/3dd3c2339c04810ca45be4d289f3e240)

## Evidence status at preparation

| Area | Evidence | Qualification for the demo |
|---|---|---|
| Public Home-to-Studio handoff | [`HomePasteForm`](../apps/web/src/components/home/HomePasteForm.tsx), [`studio-handoff`](../apps/web/src/lib/studio-handoff.ts), and [`studio-handoff.test.ts`](../apps/web/src/lib/__tests__/studio-handoff.test.ts) | Demonstrate locally or describe through test evidence. The path validates a YouTube source, requests a Video Pack, and routes to `/studio?video=...`; no production result is implied. |
| Public Home sell surface | [`page.tsx`](../apps/web/src/app/page.tsx), [`home-sell-surface.test.ts`](../apps/web/src/lib/__tests__/home-sell-surface.test.ts), and [`landing-style-safety.test.ts`](../apps/web/src/lib/__tests__/landing-style-safety.test.ts) | Source and automated-test evidence from the current base branch. |
| Landing-page refinement | [Draft PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) | Draft only. At preparation, `test-frontend` and `test` are successful, while `E2E Pipeline Tests`, `report`, and `Vercel` are failing. Do not present the refinement as reviewed, deployed, or production-ready. |
| Google sign-in retry | [Draft PR #1971](https://github.com/groupthinking/EventRelay/pull/1971) | Do **not** demonstrate. The PR is draft with no review decision, a failed Vercel check, a canceled report, and pending checks at preparation. |
| Production readiness | [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md) and [`RUNBOOK.md`](guides/RUNBOOK.md) | These documents identify configuration and backend prerequisites; they do not prove that the demonstrated behavior is deployed. |

## Timed run sheet

| Minutes | Segment owner | Demo action | Expected visible result | Evidence | Fallback |
|---:|---|---|---|---|---|
| 0–2 | `Assign owner` | State the demo boundary and explain the UVAI YouTube URL-to-Studio goal. | The audience understands that the session is a local/test walkthrough, not a production launch or checkout demonstration. | This boundary; [`page.tsx`](../apps/web/src/app/page.tsx) | Read this opening statement and proceed to the evidence table. Do not make a live service claim. |
| 2–6 | `Assign owner` | In a local environment, enter the fixture URL `https://www.youtube.com/watch?v=auJzb1D-fag` on `/` and submit the public form. | The form builds a canonical YouTube watch URL, initiates the Video Pack request, and routes to `/studio?video=...`. | [`HomePasteForm`](../apps/web/src/components/home/HomePasteForm.tsx); [`studio-handoff`](../apps/web/src/lib/studio-handoff.ts); [`studio-handoff.test.ts`](../apps/web/src/lib/__tests__/studio-handoff.test.ts) | Show the focused test output and source links. Do not claim that an external backend analysis or deployment completed. |
| 6–8 | `Assign owner` | Enter a non-YouTube value in the same form. | The form keeps the visitor on Home and exposes the accessible message “Need a valid YouTube URL.”; no pack request should be initiated. | [`HomePasteForm`](../apps/web/src/components/home/HomePasteForm.tsx); [`studio-handoff.test.ts`](../apps/web/src/lib/__tests__/studio-handoff.test.ts) | Read the invalid-input test assertion. Do not bypass validation or invent a destination. |
| 8–10 | `Assign owner` | Review the evidence for the public Home surface and its boundaries. Do not invoke checkout. | The audience can see that Home is the sell surface and Studio is the workbench, with no claim of a guaranteed transcript or arbitrary-video production E2E behavior. | [`home-sell-surface.test.ts`](../apps/web/src/lib/__tests__/home-sell-surface.test.ts); [`landing-style-safety.test.ts`](../apps/web/src/lib/__tests__/landing-style-safety.test.ts) | Read the recorded focused test results. Keep billing controls visible only; do not begin a checkout session. |
| 10–12 | `Assign owner` | State the authentication resilience status. | No sign-in retry interaction is shown. The audience sees that it remains a draft, pending-review item with incomplete checks. | [Draft PR #1971](https://github.com/groupthinking/EventRelay/pull/1971) | Record “authentication retry deferred pending passing checks and review” as a blocker. Do not represent the feature as complete. |
| 12–15 | `Assign owner` | Close with current draft PR status, limitations, and required decisions. | The audience leaves with the exact distinction between local/test evidence, draft changes, and production readiness prerequisites. | [Draft PR #1981](https://github.com/groupthinking/EventRelay/pull/1981); [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md); [`RUNBOOK.md`](guides/RUNBOOK.md) | End the walkthrough without deploying, publishing, modifying configuration, changing access, or charging a payment method. |

## Verification evidence for the walkthrough

Run these commands against the agenda branch immediately before the meeting and record their output in the meeting notes rather than changing this document mid-demo:

```bash
npm --workspace eventrelay-web exec -- vitest run \
  src/lib/__tests__/studio-handoff.test.ts \
  src/lib/__tests__/home-sell-surface.test.ts \
  src/lib/__tests__/landing-style-safety.test.ts
npm --workspace eventrelay-web run lint
npm --workspace eventrelay-web run type-check
npm run build:web
```

At agenda preparation, the focused command above passed **3 test files and 23 tests**. The full frontend lint command completed with no errors and reported three existing Studio navigation warnings on the base branch; those warnings are outside this documentation-only change. The frontend type check and production web build both passed. Re-run the commands before the meeting and treat the fresh output—not this timestamped preparation result—as the authoritative evidence.

The current focused evidence establishes the following limited claims. The handoff test covers canonical URL creation, valid Home submission to `/studio?video=...`, the Video Pack request, and rejection of invalid source input. The sell-surface test confirms that Home does not mount the Studio workbench and that it hands validated input to the canonical Studio path. The style-safety test protects the currently asserted component constraints. These checks do **not** establish external analysis completion, payment completion, production deployment, or production configuration readiness.

## Known limitations and blockers

| Item | Current status | Required handling |
|---|---|---|
| Landing-page refinement | [PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) is an open draft with no review decision. Its `test-frontend` and `test` checks are successful, but `E2E Pipeline Tests`, `report`, and `Vercel` are failing. | Reference it as draft evidence only. Do not demonstrate it as reviewed or deployed. |
| Google sign-in retry | [PR #1971](https://github.com/groupthinking/EventRelay/pull/1971) is an open draft with no review decision, a failed Vercel check, a canceled report, and pending checks. | Omit the interaction. Record the work as deferred until review and verification are complete. |
| Vercel deployment evidence | The separate Vercel deployment integration can succeed while the `v0-uvai` Vercel check fails or is canceled. | Treat neither status by itself as proof of a production deployment. Do not deploy during this agenda. |
| Durable backend and production configuration | The launch checklist identifies environment, entitlement durability, provider, and backend prerequisites. The runbook describes local backend operation and troubleshooting. | Do not change configuration or start an external deployment as part of the demo. |
| Billing | The Home surface may display Workflow Pro information. | Keep checkout out of scope; do not create a checkout session, charge a card, or modify billing configuration. |

## Close and next decisions

The closing speaker should ask the team to make only the following non-executing decisions after the demo: whether to prioritize remediation of the failing and pending checks on PRs #1981 and #1971; who will own a fresh review of those draft pull requests; and whether the production readiness prerequisites in the launch checklist have an approved owner and environment-specific evidence. The meeting must not approve itself as evidence for production readiness, billing activation, authentication changes, or deployment.
