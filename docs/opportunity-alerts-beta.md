# Opportunity alerts beta and executable recipe contract

**Issue:** [groupthinking/EventRelay#2368](https://github.com/groupthinking/EventRelay/issues/2368) (Linear GRV-789)
**Status:** **Proposal for maintainer review.** Held behind Origin G.A.T.E.
**Date:** 2026-11-09

> This document authorizes nothing. [AGENTS.md](../AGENTS.md) limits the authorized cut to **Origin G.A.T.E.** only; this proposal does not start an adjacent cut, add a route, schedule a job, contact a partner, or change any deployment. It adds **no price**: the opportunity alerts beta has no price, plan, SKU, or checkout, and nothing here amends the locked pricing table. Building any part of it needs a separate UVAI Loop approval.

## 1. Beta product definition

### What an opportunity alert is

An **opportunity alert** is a verified, personalized notice that an external change creates an action for a specific stack. External changes include a new model or model version, an API or SDK change, a published price change, a default-behavior change, and a deprecation or removal.

An alert exists only when all three hold:

1. **Verified change.** A primary source (the provider's changelog, documentation, announcement, or report) is cited by URL with its publication date and the date we retrieved it. Secondary coverage can prompt a search, but it is never the evidence. In G.A.T.E. vocabulary, the evidence must be Zero-Sim `real`; `unverified` or `unreal` evidence never becomes an alert.
2. **Applicability to this stack.** Evidence pinned to a commit shows the change touches something the recipient actually uses: a manifest entry, a call path, a configuration, or a locked product fact.
3. **An action.** There is a concrete next step, delivered as an executable recipe (section 3). A change that is interesting but asks nothing of the recipient is not an alert.

The three existing items reviewed in section 4 are the working examples: a published agent-safety report that led to a deployment-probe hardening ([#2394](https://github.com/groupthinking/EventRelay/issues/2394) / [#2395](https://github.com/groupthinking/EventRelay/pull/2395)), a Gemini storage-default change ([#2471](https://github.com/groupthinking/EventRelay/issues/2471)), and a new model evaluated as an Agent Factory backend ([#1662](https://github.com/groupthinking/EventRelay/issues/1662) / GRV-486).

### Who the beta is for

1. **EventRelay itself first.** The internal runtime is the only recipient until the recipe contract has been met by real alerts and the open decisions in section 5 are made. Alerts arrive as GitHub issues in this repository (the current practice), with the Linear sync as a mirror.
2. **Invited partners second.** A small, named cohort that has explicitly agreed to share a stack description. There is no self-serve sign-up, no public listing, and no partner outreach under this document. Cohort size, eligibility, and delivery channel are open decisions (section 5).

### What personalization is based on

Only on evidence the recipient owns and has shared, read at a pinned commit:

- **Dependency manifests and lockfiles** (for EventRelay: [package.json](../package.json), [apps/web/package.json](../apps/web/package.json), [pyproject.toml](../pyproject.toml)). A manifest floor is reported as a floor, never as the deployed version.
- **Provider call paths in code**, such as [gemini_service.py](../src/youtube_extension/services/ai/gemini_service.py), which imports the legacy `google.generativeai` client.
- **Locked product facts** in [AGENTS.md](../AGENTS.md): Gemini via Vercel AI Gateway, Upstash REST as the only pack store, and Origin G.A.T.E. as the current cut.
- **Open work and decisions** in issues, the [roadmap](MASTER_ROADMAP.md), and [NEXT-PHASE.md](NEXT-PHASE.md), so that an alert connects to work already in flight instead of opening a parallel track.

Anything that cannot be read from these sources (account tier, project creation date, live logging settings, deployed versions, gateway forwarding) is stated as **UNKNOWN** in the alert. It is not inferred.

### Non-goals

- No general AI news feed, digest, or trend commentary.
- No alert without a primary source, and no alert for a change that does not apply (section 2).
- No automatic changes. Alerts and recipes never merge, deploy, change account settings, make live provider calls, or spend money. Consequential transitions stay with G.A.T.E.
- No invented prices, savings, revenue, or buyer demand. Commercial upside appears only as a labelled hypothesis.
- No new public brand. EventRelay remains the internal runtime.
- No new gate, decision engine, or project database. The alert lifecycle uses the existing decision words, and G.A.T.E. keeps its own.

## 2. Alert lifecycle

Opportunity decisions use the words already used in the repository's recipes and watch documents (for example [mcp-skills-sep-2640-watch.md](mcp-skills-sep-2640-watch.md)):

| Decision | Meaning for the recipient |
| --- | --- |
| **ADOPT** | The change applies and the evidence supports taking it. Its recipe states the change to make through the normal reviewed PR path. |
| **TEST** | The change applies, but bounded verification comes first: offline, fixture, or disposable checkout. No live call or account change. |
| **WATCH** | The change applies, but there is no action yet because a precondition is missing or unknown. It must name what would move it to TEST or ADOPT and a re-check date. |

These are **advice about an external change**. They are separate from G.A.T.E.'s **PASS | HOLD | REJECT | ESCALATE**, which decides whether verified evidence and authority permit one specific state transition ([gate-transition-contract.md](gate-transition-contract.md), [`gate-transition.ts`](../apps/web/src/lib/gate-transition.ts)). An ADOPT never stands in for a PASS. If carrying out a recipe would change deployment state, that step goes to G.A.T.E. and gets its own decision. The two vocabularies never share a field or a label.

**A change that does not apply produces no alert.** There is no fourth label such as "IGNORE" or "N/A". The non-applicable result is recorded only as a dedupe entry (key, sources, date, and reason) so that it is not re-investigated. It is not delivered.

### Stages

1. **Detect.** A candidate external change is noticed by a person, a scheduled scan, or a report.
2. **Verify the source.** Fetch the primary source and record its URL, publication date, and retrieval date. If no primary source is available, stop with no alert.
3. **Dedupe.** Assign a stable key, `provider:product:change:date` (for example `google:gemini:generate-content:storage-default:2026-10-26`), and look for an existing issue with that key. Update that issue rather than opening a duplicate. Compare keys from the GitHub copy, because the Linear sync can rewrite colon-delimited tokens (see section 4).
4. **Check applicability.** Pin evidence to a commit. If nothing in the stack is touched, record the dedupe entry and close with no alert.
5. **Decide** ADOPT, TEST, or WATCH. There is exactly one current decision per alert. A later change of decision is recorded as a dated update that keeps the earlier one.
6. **Write the recipe** to the contract in section 3.
7. **Contract check.** Any missing or unverified section means the recipe is **withheld**. The alert can stay in progress, but it is not delivered as actionable.
8. **Deliver** to the recipient (an issue in this repository during the internal phase).
9. **Act.** The recipient follows the recipe. Any consequential transition goes through G.A.T.E.
10. **Re-check** on the expiry date: re-fetch the source and re-run applicability. A WATCH either advances or gets a new date. A source that changed supersedes the recipe.
11. **Close** with one of four outcomes: **completed** (with a receipt link), **superseded** (with a link to the newer alert), **expired** (re-check found the action no longer applies), or **declined** by the owner (with a reason). Closing an issue or moving a Linear card to Done is not a receipt.

## 3. Executable recipe contract

A recipe is the actionable body of an alert. It may live in an issue body or in a versioned file under `artifacts/`. A file is preferred because issue bodies can be edited and are rewritten by sync. Every recipe has these **11 required sections**:

| # | Section | Required content |
| --- | --- | --- |
| 1 | **Trigger and source** | The external change in one sentence. Primary-source URL(s), publication date, retrieval date, and the stable dedupe key. |
| 2 | **Applicability evidence** | Links pinned to commits for the manifest, code, or config that the change touches. Facts that cannot be established are listed as UNKNOWN, and a manifest floor is not treated as a deployed version. |
| 3 | **Decision** | Exactly one of ADOPT, TEST, or WATCH, with its date and the reason. For WATCH, the condition that would move it forward. |
| 4 | **Exact commands or steps** | Copy-paste commands or numbered steps that still exist at the stated commit or branch. A plan or checklist is not a recipe. |
| 5 | **Preconditions** | Runtime and versions, access, environment (disposable or isolated), and what is explicitly not needed (keys, accounts, spend). |
| 6 | **Verification and expected output** | The command that proves the result, its expected output, and what it does **not** prove. |
| 7 | **Rollback** | How to undo each step, including a pre-merge and a post-merge path where relevant, with no automatic deploy. |
| 8 | **Cost and quota impact** | Provider calls, quota, compute, and effort. A provider price may appear only when quoted verbatim from a cited primary source with its retrieval date. Otherwise write UNKNOWN. No invented prices, savings, or revenue. |
| 9 | **Owner** | One accountable owner, using a role from the operating model in [AGENTS.md](../AGENTS.md) (for example UVAI Loop) or a named person. |
| 10 | **Expiry and re-check date** | A calendar date when the source and applicability must be re-verified, and what triggers an earlier re-check. |
| 11 | **Receipt** | A link to the retained evidence that the verification ran: a CI run, a PR comment, or a committed log at an exact head. "VERIFIED" in prose without a locator does not count. |

**Withholding rule.** If any section is missing, empty, or unverified (a dead branch, a link to a moving target where a pin is required, prose claims with no receipt, or a price with no source), the recipe is **withheld** and the alert is not delivered as actionable. A withheld recipe is reported with its gaps, not padded. Withholding is an alert-side result. It is not a G.A.T.E. HOLD and does not create one.

## 4. Conformance of the existing items

Each item was read in full on 2026-11-09. "Present" means the section exists and its repository-checkable claims hold at current `main`. External primary sources were not re-fetched for this review.

### A. Exact deployment probe recipe ([artifacts/security/exact-deployment-probe-recipe-20261010.md](../artifacts/security/exact-deployment-probe-recipe-20261010.md))

Tracking issue [#2394](https://github.com/groupthinking/EventRelay/issues/2394) (closed); PR [#2395](https://github.com/groupthinking/EventRelay/pull/2395), merged 2026-10-12. Decision: **TEST**.

| # | Section | Result |
| --- | --- | --- |
| 1 | Trigger and source | Present. Anthropic report, 2026-10-09, primary URL, evidence key `anthropic:claude:restriction-bypass-and-live-form-fallback:report-2026-10-09`. |
| 2 | Applicability | Present. Source links pinned at `bd0f437`, plus an offline before/after fixture and a repository finding key. |
| 3 | Decision | Present. TEST. |
| 4 | Commands | **Gap.** Step 1 checks out branch `security/exact-deployment-probe-20261010`, which no longer exists on the remote. The harness scripts it runs (`scripts/security/verify_deployment_probe_offline.mjs`, `verify_manual_redirect_semantics.mjs`) are on `main`, so the step should pin the merge instead. |
| 5 | Preconditions | Present. Node 24+, disposable checkout, no credentials. |
| 6 | Verification | Present. Expected `passed: 27`, `networkRequests: 0`, `realDnsRequests: 0`, plus stated limits. |
| 7 | Rollback | Present. Pre-merge and post-merge revert path. |
| 8 | Cost and quota | Present. Zero provider requests, compute UNKNOWN, no saving claimed. |
| 9 | Owner | Present. UVAI Loop. |
| 10 | Expiry and re-check | **Missing.** |
| 11 | Receipt | **Gap.** The recipe says "NOT RUN locally" for Vitest, type-check, and lint, and defers to "the PR receipt" without linking it. The final receipt exists only in the PR body ([comment 6094922209](https://github.com/groupthinking/EventRelay/pull/2395#issuecomment-6094922209)). |

Verdict: **withheld under this contract** (three gaps). It is the closest to conforming and needs a pinned step 1, a re-check date, and a receipt link.

### B. Gemini new-project storage defaults ([#2471](https://github.com/groupthinking/EventRelay/issues/2471) / GRV-842)

The recipe lives only in the issue body (open, `needs-triage`; Linear GRV-842 in Triage).

| # | Section | Result |
| --- | --- | --- |
| 1 | Trigger and source | Present. Google changelog and logging docs, change dated 2026-10-26, retrieved 2026-10-27. The **GitHub copy** carries the intended key `google:gemini:generate-content:storage-default:2026-10-26`. **The Linear copy is corrupted:** the sync turned `:gemini:` into an emoji, so GRV-842 reads `google♊generate-content:storage-default:2026-10-26` and would not dedupe against the real key. |
| 2 | Applicability | Present but partial, and stated honestly. Pinned at `e93fd0e`: `pyproject.toml` floor `google-genai>=2.21.0` (still the floor at current `main`) and the legacy `google.generativeai` import in `gemini_service.py`. Account tier, project age, logging settings, and the deployed path are marked UNKNOWN. |
| 3 | Decision | **Gap.** Two decisions at once: "TEST complete for bounded offline transport verification" and "WATCH for deployment applicability." The contract needs one current decision (here, WATCH with its advance condition) plus the TEST result as history. |
| 4 | Commands | Present. venv, pinned `google-genai==2.33.0`, a full offline script, and a run command. |
| 5 | Preconditions | Present. Python 3.11+, package install access, no key or billable call. |
| 6 | Verification | Present. Expected PASS ×3 and `provider_calls: 0`, with NOT RUN limits listed. |
| 7 | Rollback | Present. Discard the isolated environment. |
| 8 | Cost and quota | Present. No billable call and no price. Integration effort UNKNOWN. |
| 9 | Owner | Present but split ("Hayden / EventRelay"). The contract asks for one accountable owner. |
| 10 | Expiry and re-check | **Missing.** Only an event trigger ("before using a newly created paid Gemini project"), no date. |
| 11 | Receipt | **Missing.** "VERIFIED" and "exited 0" appear in prose with no retained log, run, or committed artifact. |

Verdict: **withheld** (decision, expiry, and receipt gaps, plus the Linear key corruption). Note also that the recipe exists only in an issue body, not in a versioned file.

### C. GPT-6 Astra async backend test plan (GRV-486 / [#1662](https://github.com/groupthinking/EventRelay/issues/1662))

Linear Done; GitHub closed as completed on 2026-09-12. The implementation landed in [#1809](https://github.com/groupthinking/EventRelay/pull/1809) (merge `291f73bf`): [`astra_backend.py`](../src/youtube_extension/services/agents/astra_backend.py), disabled by default (`enabled=False`, `allow_live_execution=False`), with [`test_astra_backend.py`](../tests/unit/test_astra_backend.py) and [`test_astra_lifecycle.py`](../tests/unit/test_astra_lifecycle.py).

| # | Section | Result |
| --- | --- | --- |
| 1 | Trigger and source | Present. OpenAI announcement, model contract, and model guide, dated 2026-09-07. No retrieval date and **no dedupe key**. |
| 2 | Applicability | **Gap.** The case is argued ("why this belongs in Agent Factory") but cites no repository file at a commit. |
| 3 | Decision | Present. TEST. |
| 4 | Commands | **Missing.** The body is an implementation checklist with no runnable steps. The merged tests above could serve as the commands, but the plan does not reference them. |
| 5 | Preconditions | Partial. "No live call" and "separate capped approval" are stated; no runtime or versions. |
| 6 | Verification | **Gap.** The acceptance tests are listed as **unchecked** checkboxes, with no expected output. |
| 7 | Rollback | **Missing.** Disabled-by-default limits exposure but is not stated as rollback. |
| 8 | Cost and quota | Present with a caveat. It quotes the provider's per-token prices and the >272K-input tier from the cited model page. Those are sourced, not invented, but they have no retrieval date, so they must be re-verified at re-check before use. No EventRelay price. |
| 9 | Owner | **Missing.** |
| 10 | Expiry and re-check | **Missing.** |
| 11 | Receipt | **Missing.** The issue was closed by the PR, but the checklist is still unchecked and no test run or receipt is linked. Closure is not a receipt. |

Verdict: **withheld.** This is a test plan, not an executable recipe. The useful follow-up is a short recipe that runs the merged fixture tests at `291f73bf` and links their result.

### Summary

| Item | Decision | Missing or unverified sections | Result |
| --- | --- | --- | --- |
| A. Deployment probe (#2394 / #2395) | TEST | 4 (dead branch), 10, 11 (unlinked) | Withheld; small fix |
| B. Gemini storage (#2471 / GRV-842) | TEST + WATCH | 3 (two decisions), 10, 11; Linear key corrupted | Withheld |
| C. GPT-6 Astra (#1662 / GRV-486) | TEST | 2, 4, 6, 7, 9, 10, 11 (5 partial) | Withheld; plan, not recipe |

None of the three conforms today. That is expected for a contract written after the fact. No item is being edited by this change.

## 5. Open decisions for Hayden

1. **Partner cohort size.** How many invited partners, if any, after the internal phase. Proposal: decide only after at least one alert conforms end to end internally.
2. **Eligibility.** What a partner must provide (for example a shared manifest at a pinned commit and a named owner) and what disqualifies them (for example no primary owner or no consent to read the stack).
3. **Delivery channel.** GitHub issues in this repository (current), Linear, email, or a Studio surface. Any channel beyond issues is a new surface and needs its own approval under the Origin G.A.T.E.-only rule.
4. **Optional CI check.** Whether to add a check that fails when a file under `artifacts/` that declares itself a recipe lacks one of the 11 section headings. This is not proposed for this PR. It would need an agreed heading format first, and it would check only that sections are present, not that their content is true.
5. **Back-fill.** Whether to bring items A–C into conformance, close them as historical, or leave them as they are.

## Verification of this document

- All relative links in this file resolve at the PR head. The checks run are listed in the PR body.
- This change adds documentation only: this file and one index row in [REPO_MAP.md](REPO_MAP.md). No code, workflow, label, or deployment changes.
