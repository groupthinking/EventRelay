---
policy_version: v2
supersedes: v1 (Notion, 2026-08-03)
status: active
---

# EventRelay Merge Policy v2

## Why v2 exists

v1 defined nine default-deny admission gates. Of its eleven implementation
tasks (MG-1 … MG-11), **none shipped**: no `MERGE_POLICY.md` was committed, no
merge queue was enabled, and branch protection never required the six checks.
What actually ran was an agent reading the Notion page and returning pull
requests to draft.

The measured result over the following week: **61 open pull requests, 59 of
them draft, at a median 44 commits behind `main`**, while 44 *other* pull
requests merged in four days with red checks. Two populations, one repo. Work
that could not leave draft was re-cut as fresh pull requests — #869 and #1376
are the same change 17 days apart, and #1317, #1320 and #1342 were three pull
requests for one cleanup, of which only the third merged.

Three v1 rules caused that, and v2 is mostly about not repeating them.

**Evidence reset on every push.** v1: *"any new commit resets all gates."*
Combined with the zero-commits-behind rule, and a `main` moving ~5.5
commits/day, the loop never closes: you rebase to satisfy freshness, which
discards the review approval and preview you just earned, and by the time you
re-earn them `main` has moved again. Only a pull request born and merged inside
one quiet window could pass.

**Gates nobody could satisfy.** v1 required a Vercel preview READY on the exact
SHA; previews are routinely canceled for reasons unrelated to the change. It
required independent review approval; CodeRabbit skips any pull request without
one of 26 labels, so an unlabeled pull request could never obtain the approval
the gate demanded. `agent-completion/truth-gate` failed `invalid_payload` on
every pull request that had no dispatch contract — including #1368, which
merged and became the tip of `main` with that status red.

**Mutual quarantine.** v1 gate 6 quarantined *both* pull requests whenever two
touched the same surface. Every duplicate pair therefore blocked itself
permanently, and duplicates were exactly what the draft backlog kept producing.

## Governing principle

> Every gate must name an action the author can take to satisfy it, and
> evidence may only be invalidated by a change to the thing it attests to.

A gate that cannot be satisfied is not strict — it is broken, and it teaches
everyone to merge around it.

## Gates

A pull request may merge when all of the following hold.

### 1. Binding
Exactly one `Closes #<issue>` reference, and the pull request description
follows `.github/pull_request_template.md`.

*Already enforced by the `PR Governance` and `Canonical issue and evidence`
checks. These work — keep them.*

### 2. Required checks green on the head commit

Branch protection matches **check-run names** (a job's `name:`, or its job id),
not workflow names. v1 listed workflow names — `CI`, `Coverage`, `Security`,
`Secret Scan`, `Dependency Review` — none of which can be selected as a
required check. Only `CodeQL` happens to match. Configuring branch protection
from that list is impossible, which is why nobody ever did (MG-2).

The real contexts, as observed on live pull requests:

| Surface | Check-run names |
| --- | --- |
| CI | `validate`, `guards`, `lint-python`, `lint-frontend`, `build`, `test` |
| Static analysis | `CodeQL` |
| Security | `Security Scan - python`, `Security Scan - javascript`, `bandit`, `python-safety`, `npm-audit`, `trivy` |
| Secrets | `gitleaks (working tree)` |
| Dependencies | `dependency-review` |
| Binding | `PR Governance`, `Canonical issue and evidence` |

Required for every pull request: `validate`, `guards`, `lint-python`,
`lint-frontend`, `build`, `test`, `CodeQL`, `gitleaks (working tree)`,
`dependency-review`, `PR Governance`, `Canonical issue and evidence`,
`Security Scan - python`, `Security Scan - javascript`, `bandit`,
`python-safety`, `npm-audit`, `trivy`.

All six security contexts were verified to report `success` on a
documentation-only pull request (#1408, head `27b2ecf`), so none of them can
strand a change permanently pending. They are required unconditionally: v1
listed `Security` among its required six, and dropping every security scan out
of the required set would be a weakening introduced by the rewrite that set out
to make this gate precise.

> **What these six actually gate.** They attest that each scan *ran* — not that
> it found nothing. Every one of them reports `success` with findings present:
>
> | Check | Fails the job on | Why findings don't fail it |
> | --- | --- | --- |
> | `npm-audit` | `npm install` breaking | `continue-on-error: true` on the `npm audit` step |
> | `python-safety` | `pip install safety` breaking | `\|\| true` *and* `continue-on-error: true` |
> | `bandit` | `pip install bandit` breaking | `\|\| true` on the `bandit -r src` step |
> | `trivy` | the `docker build` breaking | `exit-code: '0'` passed to `trivy-action` |
> | `Security Scan - python`, `Security Scan - javascript` | CodeQL itself erroring | alerts route to the Security tab; blocking on them is code-scanning merge protection, which is not a required-check setting |
>
> So requiring these six catches a scanner that broke or stopped running, which
> is a real regression this gate can detect. It does **not** mean "no
> HIGH/CRITICAL finding can merge." Making findings block is a change to
> `security.yml` and to code-scanning merge protection — not a branch-protection
> edit, and not something adding a name to the list above achieves.

> **`trivy` is lowercase.** Two distinct check-runs exist on the same head —
> `trivy` reports `success`, `Trivy` reports `neutral`. Selecting the
> capitalised one requires a check that never passes. This is exactly the trap
> the confirmation rule below exists to catch.

**Conditionally required — never require these unconditionally:**

- `Generate and Upload Coverage` — does not run on documentation-only changes.
  A required check that never reports leaves the pull request *permanently
  pending*, which blocks harder than failing. Required only when the diff
  touches `src/**`, `apps/**`, or `tests/**`.
- `E2E Pipeline Tests` — passing or repository-skipped.

Before adding any check to branch protection, confirm the exact string appears
in GitHub's required-checks picker, and confirm it reports on a
documentation-only pull request. If it does not report, it belongs in the
conditional list.

These re-run automatically on push, which is correct: they attest to the code,
and the code changed. **No other evidence resets on push** — see gate 3.

### 3. Review
An automated reviewer has been requested, and either approved or reported no
actionable findings.

- A reviewer that **skips** for configuration reasons (label rules, path
  filters) satisfies this gate. A tool declining to look is not a finding.
- No response within **24 hours** satisfies this gate.
- A review is invalidated **only by a change to the files it reviewed.** A
  merge or rebase from `main` that leaves the pull request's own diff unchanged
  does not invalidate it.

### 4. Preview
Required **only for pull requests touching `apps/web/**`**, and satisfied by a
READY preview on any commit whose `apps/web` tree matches the head.

A canceled preview on a backend-only change is not evidence of anything and
does not block.

### 5. Provenance
Declared file scope matches the actual diff. No unexplained co-mingled changes.

### 6. Overlap
If another open pull request touches the same surface, both are **labeled
`needs-reconciliation` and assigned**, not blocked. Reconciliation picks one
implementation; the other closes with a pointer to the winner.

Deadline: **72 hours**, after which the fresher pull request wins by default.
Never leave both open indefinitely — that is the failure this replaces.

### 7. Freshness
`main` must merge into the pull request cleanly. **There is no
zero-commits-behind requirement.**

Correctness against a moving `main` is what a merge queue is for; enable
GitHub's (it re-runs required checks on the merge result). Until then, gate 2
on the head plus a clean merge is the honest approximation. Demanding
zero-behind without a queue just races the author against the repo.

### 8. Risk class
- **Class A** — docs, tests, CI config, dependency patch/minor. Auto-merge on
  gates 1–7.
- **Class B** — feature code, refactors, non-security-critical majors. Same
  gates plus one approval, batched daily.
- **Class C** — auth, secrets, payments, production infra, data migration, and
  majors of auth/crypto/secret-scanning packages. Individual human approval,
  never auto-merged.

Unclassifiable defaults to **B**, not C. v1 defaulted to C, and everything
unfamiliar silently became a human bottleneck — the exact backlog the policy
was written to remove.

## The rule that would have caught all of this

> **Any required check failing on more than 50% of pull requests over 7
> consecutive days is automatically demoted to advisory (`neutral`), and an
> issue is opened against its owner.**

A check red on everything has zero signal and actively hides real failures.
`agent-completion/truth-gate` was red on ~100% of pull requests for weeks,
including merged ones, and nobody noticed because everyone had learned to
ignore it. `.github/workflows/agent-completion-enforcement.yml` even documents
this failure mode in its own comments while its sibling did exactly that.

Demotion is not forgiveness. It is refusing to let a broken gate keep
laundering itself as enforcement.

## What is deliberately not here

- **No per-PR human merge clicks.** The gates authorize; humans approve
  policy versions and Class C.
- **No retroactive-intent rule.** v1 forbade issues created after their pull
  request. Combined with a snapshot job that only runs on `issues` events, this
  made pull requests unmergeable with no remedy (#1132, parked since Jul 31).
  Gate 1 asks for a linked issue, which an author can always provide.
- **No evidence ledger requirement.** v1 mandated a receipt comment on #898 for
  every gate evaluation. Nothing consumed those receipts. Git history and
  check runs are the ledger.

## Review clock

Re-reviewed every **30 days or 50 merges**, whichever comes first:

- Are pull requests being split to duck the Class A cap?
- Do new surfaces have a class, or is everything defaulting?
- Are Class B batch approvals becoming a rubber stamp? (batch size up while
  review time down ⇒ tighten)
- Is the security-critical package list current?
- **Is any required check trending toward the 50% failure demotion rule?**

A policy without a review cadence becomes v1 again. The settings are not the
protection; the re-examination is.

## Adopting this

1. Commit this file. ✅ *(this pull request)*
2. Retire the v1 Notion page — link here, mark superseded. Any agent still
   reading v1 will keep returning pull requests to draft.
3. Enable branch protection: the six checks from gate 2, block direct pushes.
4. Enable the merge queue (makes gate 7 structural).
5. Implement the 50% demotion rule as a scheduled workflow.
6. Enable Class A auto-merge. Two clean weeks later, Class B batches.

Steps 3–6 are not prerequisites. Steps 1–2 alone stop the livelock, because the
livelock was a document being enforced by an agent, not a system.
