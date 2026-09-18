# Sprint demo agenda

_Internal agenda for the UVAI sprint demonstration. This plan separates verified local behavior from draft pull-request evidence and does not represent a production deployment._

---

## 📋 Purpose and boundaries

The demonstration introduces the public workflow from a YouTube URL on the UVAI home page to the Studio workbench. The primary observable outcome is a local navigation toward Studio after a valid YouTube URL is submitted. It is not a claim that every video produces a complete transcript, analysis, payment, or production result. The home page itself states that transcript quality varies by source. [1]

The Google sign-in retry change is recorded in draft PR #1978. [2] Its branch contains local verification evidence at commit `c145b57f3b28b072daecf5a21420fe7c3ce62c45`, but the pull request is unmerged and awaits Class C authentication review. The sign-in behavior is therefore not a live-demo claim. Do not enter credentials, modify provider settings, initiate checkout, deploy, or change production configuration during this agenda.

## 🎯 Agenda

| Owner and segment | Minutes | Demo action | Expected visible result | Fallback |
|---|---:|---|---|---|
| `[Demo lead]` — opening and goal | 1 | State the workflow: paste a valid YouTube URL on `/`, then continue to Studio. | Audience understands that the session demonstrates local interaction, not a production outcome. | Read the purpose and boundaries section. |
| `[Product demonstrator]` — public Home-to-Studio handoff | 3 | In a local non-production environment, submit a valid YouTube URL through `HomePasteForm`. | The app initiates the existing pack-emission path and navigates toward `/studio?video=...`. Do not claim that a transcript or analysis completes. | Show the current-main source and the focused handoff test results in the evidence register. |
| `[Engineering presenter]` — Studio context | 2 | Show the Studio destination and explain that the URL is handed off as a canonical watch URL. | Audience can see the Studio entry point and the supplied video query. | Use the unit-test assertion for `resolveStudioHandoff()` and `submitHomePaste()` rather than a live processing run. |
| `[Quality owner]` — verification and limits | 3 | Review the local Home handoff tests, then state the OAuth change’s review boundary. | Audience sees which checks substantiate the Home handoff and understands that PR #1978 is still draft. | Read the evidence register and close without an OAuth interaction. |
| `[Demo lead]` — close and next decisions | 1 | Summarize unresolved items and name the evidence required for future demos. | Audience leaves with a clear distinction between current-main behavior, draft changes, and deployment readiness. | Share this document and the linked tasks. |

## 🔍 Evidence register

The following evidence supports the limited claims in this agenda. A presenter must not extend any claim beyond the stated boundary.

| Claim | Evidence | Demonstration limit |
|---|---|---|
| The public home page contains `HomePasteForm` and describes a YouTube URL-to-Studio workflow. | [`apps/web/src/app/page.tsx`](../apps/web/src/app/page.tsx) and [`apps/web/src/lib/__tests__/home-sell-surface.test.ts`](../apps/web/src/lib/__tests__/home-sell-surface.test.ts) | This supports the current source structure and related test assertions. It is not a production availability claim. |
| A valid YouTube input is normalized, requests pack emission, and yields a `/studio?video=...` handoff path. | [`apps/web/src/lib/studio-handoff.ts`](../apps/web/src/lib/studio-handoff.ts) and [`apps/web/src/lib/__tests__/studio-handoff.test.ts`](../apps/web/src/lib/__tests__/studio-handoff.test.ts) | The agenda may demonstrate the local handoff only. Do not promise analysis completion for an arbitrary video. |
| Invalid Home input is rejected with an accessible alert. | [`apps/web/src/components/home/HomePasteForm.tsx`](../apps/web/src/components/home/HomePasteForm.tsx) | If the local form cannot run, show the component source and omit interactive validation. |
| A failed or non-navigating Google sign-in initiation becomes retryable and displays a generic alert. | Draft PR #1978, its linked issue #1977, and the focused test in that draft branch. [2] [3] | This is local draft-branch evidence only. PR #1978 is not merged, approved, or deployed; omit a live OAuth interaction. |
| The OAuth draft branch’s focused authentication suite, type check, and lint completed locally. | The verification section of PR #1978 reports 42 passing tests across 4 files, a successful type check, and lint with 0 errors plus 3 unrelated existing warnings. [2] | Quote the result as local evidence at the PR head only. Do not represent it as current-main CI, a review approval, or a deployed result. |

## 📌 Presenter controls

Before the session, the owner should verify that the planned environment is local and non-production. The presenter must use no real customer data, credentials, payment actions, or production configuration. The sign-in retry update stays in the fallback material until the draft pull request receives the applicable human review and lands through the repository process.

If the Home handoff does not behave as described in the local environment, stop the live interaction. Use the exact test evidence in the register, state that the interactive demonstration is unavailable, and do not diagnose or change configuration during the demo. If the OAuth draft pull request remains open, retain its status as **draft** and describe it as an unmerged change with local verification evidence only.

## ✍️ Known limitations and next decisions

The current sprint still has a landing-page design task in progress. Its scope defines an improvement to the existing UVAI home page, but this agenda contains no landing-page implementation claim. [4] The task remains outside the live demonstration until separate implementation and acceptance evidence exist.

The launch checklist is a configuration and release reference. It is not evidence that a production deployment has been executed for this sprint. Future release activity must be authorized under its own process and must not be inferred from this agenda or from either draft pull request.

The next decision is whether to proceed with the internal Home-to-Studio demo using only the evidence described here. Separately, a reviewer must evaluate PR #1978 before any authentication-change merge decision. No agenda action authorizes a merge, deployment, payment action, credential entry, or production setting change.

## 🔗 References

[1]: https://github.com/groupthinking/EventRelay/blob/c2a262abdca91f431166a308110f53d15178115e/apps/web/src/app/page.tsx "UVAI home page"
[2]: https://github.com/groupthinking/EventRelay/pull/1978 "Draft PR #1978: recover failed Google sign-in initiation"
[3]: https://github.com/groupthinking/EventRelay/issues/1977 "Issue #1977: recover Google sign-in initiation failures"
[4]: https://app.notion.com/p/3dd3c2339c0481439d43eafdeacd4136?pvs=204 "Notion task: Design sprint landing page"
