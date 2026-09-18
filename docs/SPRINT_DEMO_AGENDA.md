# Sprint Demo Agenda

**Purpose.** This internal agenda demonstrates the public UVAI Home-to-Studio path and reports sprint evidence accurately. It does not authorize production deployment, payment, OAuth configuration, Origin G.A.T.E. transitions, or a merge. Assign the owner placeholders before the meeting.

## Evidence boundary

Only demonstrate a behavior as verified when the listed command passed on the branch or pull-request head being discussed. A local interaction is not production evidence. A draft pull request is not a reviewed change. If a required check is unavailable, use the named fallback and state the limitation plainly.

## Run of show

| Time | Owner | Demo action | Observable result | Evidence command | Fallback language (read verbatim if evidence is missing) |
|---|---|---|---|---|---|
| 0:00–1:00 | **Demo lead: _assign_** | Open `/` and state the goal: a visitor can understand the YouTube URL-to-Studio workflow. | Primary heading and URL input are visible. | `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/home-sell-surface.test.ts` | “We can show the page, but we do not have fresh passing evidence for this segment on the current head.” |
| 1:00–3:00 | **Product owner: _assign_** | Enter the standard safe fixture URL in the Home form and submit it. | Route becomes `/studio?video=...`. | `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/studio-handoff.test.ts src/lib/__tests__/home-sell-surface.test.ts` | “The Home-to-Studio handoff is implemented, but fresh passing verification is pending for this branch.” |
| 3:00–4:30 | **Product owner: _assign_** | Enter an invalid non-YouTube value; show pricing summary and cadence controls without starting checkout. | Accessible invalid-URL message appears; monthly/annual controls and pricing link are visible. | `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/home-sell-surface.test.ts src/lib/billing/__tests__/checkout-config.test.ts` | “Validation and pricing controls are shown as expected, but this demo does not claim checkout readiness.” |
| 4:30–6:00 | **Engineering owner: _assign_** | Explain Google sign-in recovery behavior for rejected or non-navigating initiation. | Audience sees code/test evidence only; no real OAuth completion. | `npm --workspace=eventrelay-web exec -- vitest run src/app/login/GoogleSignInButton.test.tsx src/lib/__tests__/auth-paths.test.ts src/__tests__/proxy-auth-gate.test.ts` | “Sign-in retry behavior is a tested candidate and is not presented as merged or production-ready in this demo.” |
| 6:00–7:30 | **QA owner: _assign_** | Summarize local quality gates for sprint changes. | Team sees exact command outputs and local-vs-remote distinction. | `npm --workspace=eventrelay-web run type-check && npm --workspace=eventrelay-web run lint && git diff --check` | “These are local quality signals only; remote preview and CI evidence are still required for readiness.” |
| 7:30–9:00 | **Engineering owner: _assign_** | State Origin G.A.T.E. boundary and production launch limitations. | Audience understands no consequential transition was demonstrated. | `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/origin-gate.test.ts src/lib/__tests__/gate-transition.test.ts` | “No live deployment or consequential state transition is being claimed in this sprint demo.” |
| 9:00–10:00 | **Demo lead: _assign_** | Close with current PR status, blockers, and reviewer decisions needed. | Team leaves with a precise next-step record. | `git rev-parse --short HEAD && git status --short` | “Status readout is current to this commit only; reviewer outcomes can change after this meeting.” |

## Presenter checklist

Before the meeting, record the relevant pull-request head and the terminal output from these commands. Run the landing checks on the [canonical landing PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) head and the sign-in checks on [PR #1984](https://github.com/groupthinking/EventRelay/pull/1984) head.

```bash
npm --workspace=eventrelay-web exec -- vitest run \
  src/lib/__tests__/studio-handoff.test.ts \
  src/lib/__tests__/home-sell-surface.test.ts \
  src/lib/billing/__tests__/checkout-config.test.ts

npm --workspace=eventrelay-web exec -- vitest run \
  src/app/login/GoogleSignInButton.test.tsx \
  src/lib/__tests__/auth-paths.test.ts \
  src/__tests__/proxy-auth-gate.test.ts

npm --workspace=eventrelay-web run type-check
npm --workspace=eventrelay-web run lint
git diff --check
```

For a local responsive demonstration, use the Home Playwright specification present on the branch being demonstrated. This is local UI evidence only; it does not replace preview-dependent end-to-end evidence.

## Required fallback language

**Local URL handoff unavailable:** “The Home-to-Studio route is implemented, but we do not have fresh local verification for this demo. The exact test command is listed in the agenda.”

**Google sign-in change not yet reviewed:** “The retry behavior is a tested candidate in draft PR #1984. It does not change OAuth credentials, callback policy, or the server authentication gate, and it is not presented as a merged result.”

**Remote preview unavailable:** “Remote preview-dependent checks are blocked. We are showing local evidence only and are not asserting production readiness.”

**Checkout request:** “The checkout component is shown without initiating payment. Billing and entitlements require the separately authorized test-mode and production evidence in the launch checklist.”

## Closing record

At the end of the meeting, record these facts:

1. The landing-page Notion task remains **In progress**. [PR #1976](https://github.com/groupthinking/EventRelay/pull/1976) is closed as a duplicate; [PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) is the canonical landing-page implementation and remains blocked on preview-dependent evidence.
2. Google sign-in recovery is represented by draft [PR #1984](https://github.com/groupthinking/EventRelay/pull/1984). The local test coverage is relevant evidence, but open remote Vercel and E2E failures prevent a readiness claim.
3. The [QA checklist task](https://app.notion.com/p/3dd3c2339c0481019c8fdf22053d0a4d?pvs=204) and this agenda are documentation-only follow-ups. They do not change application behavior or production configuration.
4. No merge, deployment, payment, secret change, access change, or public release follows from this meeting.

## References

[1]: https://app.notion.com/p/3dd3c2339c0481439d43eafdeacd4136?pvs=204 "Design sprint landing page task"
[2]: https://app.notion.com/p/3dd3c2339c0481a2a35dce563f281ab1?pvs=204 "Fix login bug task"
[3]: https://app.notion.com/p/3dd3c2339c04810ca45be4d289f3e240?pvs=204 "Confirm sprint demo agenda task"
[4]: https://app.notion.com/p/3dd3c2339c0481019c8fdf22053d0a4d?pvs=204 "Prepare QA checklist task"
