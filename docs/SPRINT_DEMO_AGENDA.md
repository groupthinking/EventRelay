# UVAI Home-to-Studio Sprint Demo Agenda

**Purpose.** This internal agenda demonstrates the public UVAI Home-to-Studio path and reports sprint evidence accurately. This agenda does not authorize production deployment, payment, OAuth configuration, Origin G.A.T.E. transitions, or a merge. Assign the owner placeholders before the meeting.

## Evidence boundary

Only demonstrate a behavior as verified when the listed command passed on the branch or pull-request head being discussed. We are showing local or branch evidence only unless a separately cited remote check is current and green. A local interaction is not production evidence. A draft pull request is not a reviewed change. If a required check is unavailable, use the named fallback and state the limitation plainly.

## Run of show

| Time | Owner | Demo action | Expected result | Evidence | Fallback |
|---|---|---|---|---|---|
| 0:00–1:00 | **Demo lead: _assign_** | Open `/` and state the demo goal: a prospective visitor can understand the YouTube URL-to-Studio workflow. | The primary heading and URL input are visible. | Source: [`apps/web/src/app/page.tsx`](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/app/page.tsx). | If no local server is available, use a code walkthrough and do not make a hosted-product claim. |
| 1:00–3:00 | **Product owner: _assign_** | Enter the standard safe fixture URL in the Home form and submit it. | The route becomes `/studio?video=...`. | Run the command on the [canonical landing-page PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) head: `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/studio-handoff.test.ts src/lib/__tests__/home-sell-surface.test.ts`. | If the check is unavailable or failing, show the form and explain that the fresh handoff result is pending. |
| 3:00–4:30 | **Product owner: _assign_** | Enter an invalid non-YouTube value. Then show the pricing summary and cadence controls without starting checkout. | An accessible invalid-URL message appears; monthly and annual controls plus the pricing link are visible. | Use the same landing PR head and add `src/lib/billing/__tests__/checkout-config.test.ts`. Do not trigger Turnstile or checkout. | If the check is unavailable, describe the expected control only. |
| 4:30–6:00 | **Engineering owner: _assign_** | Explain the Google sign-in recovery behavior: rejected or non-navigating initiation returns the button to a retryable state with generic error copy. | The audience sees the code or test narrative, not a real OAuth completion. | Draft [PR #1984](https://github.com/groupthinking/EventRelay/pull/1984) contains the implementation and its component test. | Only demonstrate it as a reviewed outcome after review and its remote check failures are resolved. Until then, explain it as a tested candidate. |
| 6:00–7:30 | **QA owner: _assign_** | Summarize the local quality gates for the two sprint changes. | The team sees exact commands and the distinction between local tests and remote checks. | Reference [draft QA checklist PR #1993](https://github.com/groupthinking/EventRelay/pull/1993). | If that document is still pending review, present the commands directly and do not claim full release readiness. |
| 7:30–9:00 | **Engineering owner: _assign_** | State the Origin G.A.T.E. boundary and the production launch limitations. | The audience understands that consequential workflow transitions and production readiness were not demonstrated. | Reference [`docs/gate-transition-contract.md`](https://github.com/groupthinking/EventRelay/blob/main/docs/gate-transition-contract.md) and [`docs/LAUNCH_CHECKLIST.md`](https://github.com/groupthinking/EventRelay/blob/main/docs/LAUNCH_CHECKLIST.md). | Do not attempt a live deployment, provider action, payment, or configuration change. |
| 9:00–10:00 | **Demo lead: _assign_** | Close with the active PR status, known blockers, and decisions needed from reviewers. | The team receives a precise next-step record. | Use the closing record below. | If a status changes during the meeting, read the current PR status rather than relying on this document. |

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
