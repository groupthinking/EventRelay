# Sprint QA Checklist

_Internal, evidence-oriented QA checklist for sprint verification. Use exact command output and manual observations to decide whether a finding is a release blocker or a known limitation._

---

## How to use this checklist

- Do not mark an item complete without attached evidence.
- For command-based checks, save the exact command and whether it passed or failed.
- For manual checks, record the URL, browser width, and the observed result.
- Classify every failure before filing it:
  - **Release blocker:** breaks the shipped sprint scope, the core YouTube URL → Video Pack → studio loop, or a required security/control check.
  - **Known limitation:** already understood, out of scope for the sprint, or caused by missing local/prod-only access while the app still fails closed.

## Evidence capture

| Evidence type | What to record |
| --- | --- |
| Automated command | Full command, exit status, and the failing line or summary |
| Manual browser check | Page URL, viewport size, action taken, and observed result |
| Security/config check | Whether the system failed closed, plus any relevant log or response code |

---

## Release-blocking checks

### 1. Workspace hygiene

- [ ] **Clean branch context**
  - **Command:** `git branch --show-current`
  - **Pass when:** QA is run from the intended sprint branch.
- [ ] **No unexpected working tree changes**
  - **Command:** `git status --short`
  - **Pass when:** Only intended sprint files are modified.
- [ ] **No whitespace or merge-marker issues**
  - **Command:** `git diff --check`
  - **Pass when:** The command exits cleanly.
- [ ] **No secrets in the sprint diff**
  - **Observation:** Review the changed files for `.env` values, tokens, credentials, or copied production payloads.
  - **Pass when:** No secrets or sensitive values appear in the diff.

### 2. Automated verification

- [ ] **Python tests pass**
  - **Command:** `pytest tests/ -v`
  - **Pass when:** The suite exits successfully.
- [ ] **Python lint passes**
  - **Command:** `ruff check src/`
  - **Pass when:** No lint violations remain.
- [ ] **Web lint passes**
  - **Command:** `npm run lint`
  - **Pass when:** Turbo exits successfully with no lint failures.
- [ ] **Web type-check passes**
  - **Command:** `npm --workspace=apps/web run type-check`
  - **Pass when:** TypeScript exits successfully.
- [ ] **Web tests pass**
  - **Command:** `npm run test`
  - **Pass when:** Turbo exits successfully with no failing tests.
- [ ] **Production web build passes**
  - **Command:** `npm run build`
  - **Pass when:** The build completes without errors.

### 3. Manual sprint flow

Start the local stack before manual checks:

```bash
PYTHONPATH=src uvicorn youtube_extension.main:app --reload --port 8000
npm run dev:web
```

- [ ] **Entry page accepts a valid YouTube URL**
  - **Observation:** From `/`, submit a valid YouTube URL.
  - **Pass when:** The app advances into the canonical studio flow rather than a dead-end or alternate workflow.
- [ ] **Studio remains the canonical workspace**
  - **Observation:** Navigate to `/dashboard`.
  - **Pass when:** The app redirects into `/studio`.
- [ ] **Core loop starts from the video URL**
  - **Observation:** In `/studio`, confirm the selected video begins Video Pack processing or evidence loading.
  - **Pass when:** The sprint still follows YouTube URL → Video Pack → studio output.
- [ ] **Invalid input fails safely**
  - **Observation:** Submit an invalid URL.
  - **Pass when:** The UI shows a user-safe error and no raw stack trace or secret is exposed.
- [ ] **No false live/deploy claim**
  - **Observation:** If the sprint touches deploy or publish states, inspect the UI state shown to the operator.
  - **Pass when:** The app does not claim a live success without a verified `https://` receipt and the required G.A.T.E. pass.
- [ ] **Browser console and network stay clean**
  - **Observation:** Review DevTools console and failing network requests while exercising the sprint path.
  - **Pass when:** There are no uncaught errors, leaked credentials, or unexpected 5xx responses caused by the sprint change.

---

## Known limitations (do not block release by themselves)

- Missing production-only credentials or third-party accounts during local QA, **if** the product fails closed and does not claim success.
- External provider flakiness or rate limiting that cannot be reproduced as a code regression from the sprint diff.
- Historical docs, retired gates, or old PR references that do not describe the current release path.
- Out-of-scope roadmap work that was not part of the sprint's acceptance criteria.

If a limitation stops a required acceptance path from completing, reclassify it as a **release blocker**.

---

## QA evidence log template

| Item | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Example: `npm run build` | Pass / Fail | Terminal output or CI link | Include the key line |
| Example: `/studio` flow | Pass / Fail | URL + viewport + screenshot | Include observed behavior |

---

## References

- [AGENTS.md](../AGENTS.md)
- [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)
- [NEXT-PHASE.md](NEXT-PHASE.md)
