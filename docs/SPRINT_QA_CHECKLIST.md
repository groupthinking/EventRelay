# Sprint QA Checklist

**Purpose.** This checklist records the evidence a reviewer needs to evaluate the current EventRelay sprint safely. It covers the landing-page and Google sign-in changes without authorizing a deployment, a payment, an OAuth credential change, or a merge. Run the commands from the repository root after checking out the branch or pull-request head under review.

## Scope and evidence map

| Work item | Review source | What is being verified |
|---|---|---|
| Landing-page clarity and focus states | [Landing task](https://app.notion.com/p/3dd3c2339c0481439d43eafdeacd4136?pvs=204) and [canonical PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) | The existing Home-to-Studio handoff, billing presentation, responsive layout, and keyboard focus remain intact. |
| Google sign-in retry | [Login task](https://app.notion.com/p/3dd3c2339c0481a2a35dce563f281ab1?pvs=204) and [draft PR #1984](https://github.com/groupthinking/EventRelay/pull/1984) | A failed or non-navigating Google sign-in initiation returns the button to a retryable state without exposing failure details. |
| Sprint demo agenda | [Agenda task](https://app.notion.com/p/3dd3c2339c04810ca45be4d289f3e240?pvs=204) | The demonstration uses only current local evidence and names fallbacks for unavailable remote checks. |

> **Control boundary:** A local test, a draft pull request, or a rendered checkout control does not prove a production deployment, a paid subscription, an OAuth completion, or an Origin G.A.T.E. authorization.

## Required release blockers

### 1. Landing-page interaction and accessibility

| Check | Exact evidence command or observation | Pass condition |
|---|---|---|
| Home copy and checkout boundaries | Run the focused [Home sell-surface test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/__tests__/home-sell-surface.test.ts), [Studio handoff test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/__tests__/studio-handoff.test.ts), and [checkout configuration test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/billing/__tests__/checkout-config.test.ts): `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/home-sell-surface.test.ts src/lib/__tests__/studio-handoff.test.ts src/lib/billing/__tests__/checkout-config.test.ts` | The suite passes, and the source continues to use `HomePasteForm`, `HomeProCheckout`, and shared price configuration. |
| Responsive Home experience | In one terminal run `npm --workspace=eventrelay-web run dev`; in another run `BASE_URL=http://127.0.0.1:3000 npm --workspace=eventrelay-web exec -- playwright test playwright/home-sell-surface.spec.ts` | At 360 px and 1280 px, the heading, form, pricing summary, and checkout surface are visible with no horizontal scrolling. |
| Valid and invalid URL behavior | In the same local browser session, submit `not a YouTube URL`, then a valid YouTube URL. | Invalid input produces the existing accessible alert. A valid URL changes the route to `/studio?video=...`. Do not claim downstream analysis succeeds. |
| Keyboard path | With the local Home page open, use Tab to reach the URL input, Run in Studio button, monthly and annual controls, checkout action, and pricing link. | Each control receives a visible focus indicator. Do not activate checkout. |

### 2. Google sign-in retry behavior

| Check | Exact evidence command or observation | Pass condition |
|---|---|---|
| Component retry regression | On `feature/fix-login-bug-8f3b6e9a`, run the [Google sign-in component test](https://github.com/groupthinking/EventRelay/blob/feature/fix-login-bug-8f3b6e9a/apps/web/src/app/login/GoogleSignInButton.test.tsx): `npm --workspace=eventrelay-web exec -- vitest run src/app/login/GoogleSignInButton.test.tsx` | The rejected initiation and non-navigating handoff cases display a generic accessible error and restore an enabled retry button. |
| Duplicate-submission guard | The same focused test command above | A second click during the initiation state does not create a second sign-in request. |
| Error safety | Inspect the focused test and the rendered alert in [`apps/web/src/app/login/GoogleSignInButton.tsx`](https://github.com/groupthinking/EventRelay/blob/feature/fix-login-bug-8f3b6e9a/apps/web/src/app/login/GoogleSignInButton.tsx). | Error text is generic and does not echo provider, token, callback, or network details. |
| Callback sanitization and public auth routes | Run the [auth-path test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/__tests__/auth-paths.test.ts) and [proxy-auth gate test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/__tests__/proxy-auth-gate.test.ts): `npm --workspace=eventrelay-web exec -- vitest run src/lib/__tests__/auth-paths.test.ts src/__tests__/proxy-auth-gate.test.ts` | Callback handling stays sanitized and NextAuth endpoints remain reachable while protected API routes fail closed when configuration is missing. |

### 3. Security and workflow boundaries

| Check | Exact evidence command | Pass condition |
|---|---|---|
| Origin G.A.T.E. and sandbox origin controls | Run `npm --workspace=eventrelay-web run test:gate`, which includes the [Origin G.A.T.E. test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/__tests__/origin-gate.test.ts) and [gate-transition test](https://github.com/groupthinking/EventRelay/blob/main/apps/web/src/lib/__tests__/gate-transition.test.ts). | The named gate, transition, Studio workflow, and sandbox-origin tests pass. This is local contract evidence only. |
| Static quality checks | `npm --workspace=eventrelay-web run type-check` followed by `npm --workspace=eventrelay-web run lint` | Type checking reports no errors. Lint has no errors; record any pre-existing warnings separately. |
| Repository hygiene | `git status --short --branch` followed by `git diff --check` | Work happens on a dedicated branch, the intended diff is reviewable, and there is no whitespace error. |
| Secret and scope review | Review `git diff --cached` or the pull-request Files changed tab before approval. | No secret, environment file, production setting, deployment configuration, checkout behavior, or unrelated source file is included. |

## Remote and production prerequisites

The checks below are release blockers but are deliberately **not runnable from a credential-free local checkout**. Do not bypass them or mark them successful from a local test result.

| Blocker | Required evidence | Safe local substitute |
|---|---|---|
| Preview-dependent end-to-end check | A ready Vercel Preview for the current PR head, followed by the PR’s E2E job completing against that preview. | Run the local Playwright Home test. Record that it is local-only evidence. |
| Google OAuth completion | An approved, configured preview or production environment and a real authorized test account. | Verify the component’s rejected and stalled-initiation behavior with the focused Vitest test. |
| Stripe checkout and entitlement | Approved Stripe test-mode configuration, an authorized test card, webhook delivery, and durable entitlement evidence. | Inspect existing checkout component and configuration tests. Do not begin checkout. |
| Production launch configuration | The explicit launch-go/no-go controls in [the launch checklist](LAUNCH_CHECKLIST.md). | No substitute; leave this blocker open until an authorized operator records the required environment evidence. |

## Informational warnings and known limitations

The landing branch formerly represented by [PR #1976](https://github.com/groupthinking/EventRelay/pull/1976) is closed as a duplicate. The landing Notion task names [PR #1981](https://github.com/groupthinking/EventRelay/pull/1981) as its canonical implementation and records that preview-dependent evidence is still unavailable. Review the canonical PR rather than reopening or merging the duplicate.

Draft [PR #1984](https://github.com/groupthinking/EventRelay/pull/1984) has passing build, test, lint, security, dependency-review, and CodeQL checks recorded by GitHub. It also has failed Vercel and E2E checks, so it remains **not ready for merge** until the remote preview and E2E failures are resolved or explicitly dispositioned by the repository owners.

`docs/LAUNCH_CHECKLIST.md` is the authoritative source for subscription-launch configuration. Its live-secret, webhook, Redis, OAuth, and provider-key sections must not be copied into a pull request or used as a reason to change environment settings during this documentation task.

## Reviewer record

Record the branch or PR head SHA, command output, date, and reviewer for every passing check. For a failed or unavailable check, record the exact prerequisite and the safest local substitute that was run. Do not convert an unavailable check into a pass.

## References

[1]: https://app.notion.com/p/3dd3c2339c0481019c8fdf22053d0a4d?pvs=204 "Prepare QA checklist task"
[2]: https://github.com/groupthinking/EventRelay/pull/1984 "Draft Google sign-in retry pull request"
[3]: https://github.com/groupthinking/EventRelay/pull/1981 "Canonical landing-page pull request"
[4]: https://github.com/groupthinking/EventRelay/pull/1976 "Closed duplicate landing-page pull request"
