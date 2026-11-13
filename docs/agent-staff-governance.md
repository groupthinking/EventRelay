---
policy_version: v1
status: proposed
owner: Hayden Garvey
adopted: pending merge
---

# Agent Staff Governance

Five rules, one approval gate, and a policy loop for every agent that works in
this repo (Claude, Gemini, Grok, Jules, Copilot, Hark, and any agent declared in
`config/agent_network.json`). Adapted from "Hire Agents Like Staff" and "From
Inconsistency to Policy". This doc complements [MERGE_POLICY.md](../MERGE_POLICY.md)
and does not replace it. Where they overlap, MERGE_POLICY.md governs merge
mechanics and this doc governs authority.

## Why the gate is narrow

A human yes on every change to `main` was tried and it stalled the work. In one
24-hour window an always-on agent woke 47 times and acted on nothing, because
every next step was waiting on an approval. MERGE_POLICY.md v2 already
documents the same failure for unsatisfiable gates: work piles up in draft, and
people learn to merge around the gate. So the human gate covers the
irreversible and the expensive. Everything else runs on policies the owner
approves once.

## 1. The five rules

1. **No action without permission.** Agents may analyze, plan, draft, and work
   in branches or worktrees freely. A state-changing action outside the repo
   (a send, a post, a purchase, a deploy, an external API write) needs either an
   approved standing policy that covers it or explicit task authorization.
2. **One approval gate for production.** Hayden's explicit approval is
   required for:
   - deploys or promotions to production (live `uvai.io` / Vercel production),
   - live database changes (migrations, data writes, RLS changes on any
     production Supabase project),
   - billing, entitlements, pricing, or any spend,
   - credentials, secrets, and access settings (repo settings, branch
     protection, tokens).

   Merges to `main` that touch none of the above are covered by the standing
   merge policy below. They still go through the MERGE_POLICY.md gates and must
   pass Staging/Judge verification.
3. **All work backed up to GitHub.** Every code change, skill, harness, and
   config change is committed and pushed to a tracked branch. Nothing lives only
   in an ephemeral sandbox.
4. **A changelog for everything.** Every merged PR and every state transition
   records why it happened and links the issue, PR, or Video Pack hash that
   triggered it (PR body plus a `CHANGELOG.md` entry for user-visible changes).
5. **Everything gets documented.** Every fix or incident leaves a short SOP
   (what happened, how it was caught, how to prevent it, how to handle it next
   time) and a regression test or CI check, so the fix compounds.

## 2. Standing merge policy (approved once)

An agent may merge a PR to `main` without a per-PR approval when all of these
hold:

- Every required check is green on the exact head SHA, re-read just before
  merge (a green historical run is not current verification).
- No unresolved review threads, and no changes requested.
- The PR binds exactly one issue (`Closes #N`) and follows MERGE_POLICY.md.
- The diff touches nothing behind the approval gate (section 1, rule 2), and no
  hold applies (for example a hold that waits on another PR leaving draft).
- No force-push, no history rewrite, and merge with expected-head protection.

After merging, the agent reports what merged and the merge commit.

## 3. From inconsistency to policy

1. **Spot the inconsistency.** Drift, a silent dependency or model update, a
   spec mismatch, or a repeated manual approval.
2. **Propose a policy.** A deterministic rule plus the test or CI check that
   enforces it. Fix the class of problem, not just the one instance.
3. **Hayden approves it once.** He signs off on the policy, not on each
   individual patch.
4. **Make it official.** Write the rule into this doc or AGENTS.md, add the
   CI or eval gate, and enforce it automatically from then on.

Approved policies are listed in the Policy register below, newest first.

## 4. Hiring brief for every agent role

Every agent role (Design, Code, Agent, Maintainer, Owner, Operator, and
Staging/Judge) is defined by a three-part brief, and must state its limits
before it takes work:

- **Owns:** the whole surface it is responsible for, end to end.
- **Thinks:** verifies from first principles, prefers structured evidence to
  narrative, fails closed on unimplemented routes, and never fabricates a
  success state. This is consistent with Zero-Sim and G.A.T.E. in AGENTS.md.
- **Accountable for:**
  - *Done* means it builds and type-checks (`tsc --noEmit`, `ruff`, `pytest` as
    applicable), passes Staging/Judge, matches provenance where a Video Pack
    applies, and ships with a changelog entry and an SOP.
  - *Never touch without asking:* anything behind the approval gate.

**Limit disclosure:** at the start of a task, an agent says what it can execute
directly and what needs staging or a human handoff. It never claims write or
deploy access it does not have.

## Policy register

| ID | Policy | Approved |
| --- | --- | --- |
| POL-001 | Standing merge policy (section 2) | On merge of this doc |
