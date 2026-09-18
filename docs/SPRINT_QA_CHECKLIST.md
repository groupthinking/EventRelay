# Sprint QA Checklist

_Evidence-oriented quality assurance checklist for the current EventRelay sprint tasks. This document relies on existing repository commands and controls; it does not modify application behavior._

---

## 📋 Overview

This checklist verifies the responsive landing-page behavior, the Google sign-in retry flow, security regression boundaries, and repository hygiene. It separates release blockers from informational warnings and relies on exact automated commands or manual observations.

## 🎯 Responsive Landing Page

- [ ] **Viewport Integrity:** At 360px and 1280px widths, verify there is no horizontal scrolling.
  - *Evidence:* Manual observation in browser dev tools.
- [ ] **Element Visibility:** Confirm the heading, URL form, pricing summary, and checkout call to action are visible.
  - *Evidence:* Manual observation.
- [ ] **Keyboard Navigation:** Verify the URL input, submit button, billing cadence controls, checkout action, and pricing link are reachable via `Tab` with a visible focus state.
  - *Evidence:* Manual keyboard navigation.
- [ ] **URL Handoff:** Submit a valid YouTube URL and confirm it navigates to `/studio?video=...`.
  - *Evidence:* `npm --workspace=eventrelay-web test -- src/lib/__tests__/studio-handoff.test.ts`
- [ ] **Invalid Input:** Submit an invalid URL and confirm the existing error renders as an accessible alert.
  - *Evidence:* Manual observation and `HomePasteForm` component tests.

## 🔐 Google Sign-in Retry

- [ ] **Retry State Recovery:** Ensure a failed or non-navigating `signIn('google')` initiation restores a retryable button.
  - *Evidence:* `npm --workspace=eventrelay-web test -- src/app/login/GoogleSignInButton.test.tsx`
- [ ] **Accessible Error:** Verify the error text is accessible and non-sensitive (no OAuth credentials or tokens exposed).
  - *Evidence:* `GoogleSignInButton.test.tsx` assertions on `role="alert"`.
- [ ] **Duplicate Prevention:** Confirm a successful initiation prevents duplicate submission while navigation is occurring.
  - *Evidence:* `GoogleSignInButton.test.tsx` assertions on the disabled state while in flight.

## 🛡️ Security Regression Boundaries

- [ ] **Callback Sanitization:** Verify `safeCallbackPath()` prevents open redirects to untrusted domains.
  - *Evidence:* `npm --workspace=eventrelay-web test -- src/lib/__tests__/auth-paths.test.ts`
- [ ] **Public Routes:** Confirm `/api/auth/*` and other explicitly public routes remain accessible without a session.
  - *Evidence:* `auth-paths.test.ts`
- [ ] **Origin G.A.T.E.:** Verify signed artifact-bound transitions require valid cryptographic attestations.
  - *Evidence:* `npm --workspace=eventrelay-web test -- src/lib/__tests__/origin-gate.test.ts`
- [ ] **Sandbox Origin:** Confirm cross-origin requests are correctly rejected.
  - *Evidence:* `npm --workspace=eventrelay-web test -- src/lib/__tests__/sandbox-origin.test.ts` (if applicable) or manual CORS verification.
- [ ] **Protected Previews:** If a check depends on Vercel preview credentials, use local test substitutes. Do not weaken the control.
  - *Evidence:* Documented local test equivalents for preview environments.

## 🧹 Repository Hygiene

- [ ] **Branch Isolation:** Work is isolated on a dedicated feature branch.
  - *Evidence:* `git branch --show-current`
- [ ] **Draft PRs:** Changes are submitted as draft pull requests only.
  - *Evidence:* `gh pr view <number> --json isDraft`
- [ ] **No Secrets:** No credentials or deployment changes are committed.
  - *Evidence:* `git diff --check` and manual review of the diff.
- [ ] **Static Analysis:** Type checking and linting pass.
  - *Evidence:* `npm --workspace=eventrelay-web run type-check` and `npm --workspace=eventrelay-web run lint`

## ⚠️ Release Blockers vs. Limitations

### Blockers
- **Backend Coverage Gate:** The backend test suite executed successfully, but aggregate coverage (77.29%) fell below the `fail_under = 88.1833` threshold in `pyproject.toml`. This blocks a clean CI pipeline.
- **Unmerged Drafts:** PR #1978 (OAuth fix) and PR #1980 (Agenda) remain unmerged drafts.

### Known Limitations
- **Landing Page Implementation:** The design task is scoped but not yet implemented.
- **Production Access:** This checklist relies on local verification; it does not authorize or execute a production deployment. See [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) for production provisioning.

## 🔗 References

- [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)
- [Draft PR #1978: recover failed Google sign-in initiation](https://github.com/groupthinking/EventRelay/pull/1978)
- [Draft PR #1980: add evidence-backed sprint demo agenda](https://github.com/groupthinking/EventRelay/pull/1980)
- [Notion task: Prepare QA checklist](https://app.notion.com/p/3dd3c2339c0481019c8fdf22053d0a4d?pvs=204)
