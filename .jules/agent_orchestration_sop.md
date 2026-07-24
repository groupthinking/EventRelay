# EventRelay Agent Orchestration SOP

## Purpose

EventRelay uses agents to turn one focused issue into one verified pull request. The source of current delivery truth is GitHub issue #898 and the exact state of its linked issues, pull requests, checks, reviews, and deployments. This document defines durable operating rules; it must not contain a copied PR inventory that becomes stale.

## Operating contract

1. Decide the smallest useful action.
2. Perform the action on the existing canonical branch.
3. Call it complete only when a machine-verifiable artifact exists.
4. Record the exact head, checks, reviews, deployment applicability, and next action.
5. Keep incomplete work draft. Never substitute narration, assignment, or an @mention for progress.

Valid progress is a new exact head, a completed exact-head workflow, a resolved and verified review finding, deployment evidence, or a confirmed state mutation.

## Canonical execution unit

Every executable unit has:

- one focused child issue of #898;
- one canonical branch and pull request;
- a declared file and test scope;
- an execution receipt;
- a closing reference only for its focused child issue.

A partial implementation progresses #898 and closes only its focused child issue after all acceptance gates pass. Evidence-only branches must say so and must not compete with the canonical implementation.

## Execution receipt

Every active execution records:

- agent login;
- run ID;
- focused issue;
- canonical branch and PR;
- claimed timestamp;
- latest heartbeat;
- exact head SHA;
- declared scope and focused tests;
- artifact or workflow URLs.

A dispatch is not active execution until the connector accepts it and a run or heartbeat is observable.

## Roles and authority

Agents are capabilities, not authorities. A working model remains enabled unless a repository owner explicitly changes its access. Authority is granted by action type:

- Implementation agents may change only the declared scope on the canonical branch.
- Review agents may report findings but may not certify their own implementation.
- The controller may make safe, reversible metadata corrections, apply focused fixes, return incomplete work to draft, resolve findings proven fixed, and rerun transient failures.
- Final merge, irreversible infrastructure, production activation, credential changes, billing, security exceptions, and ruleset weakening require explicit human authority.

No agent may merge, close useful work, delete an unmerged branch, or mark a PR ready merely because it created or reviewed the change.

## Verification gates

Before a PR advances:

- the observed PR head equals the tested head;
- required CI, security, secret, dependency, and focused workflows pass on that head; coverage is explicitly non-applicable for documentation-only diffs;
- all current review findings are fixed and resolved with evidence;
- a current-head independent review exists;
- deployment evidence is bound to the same head, or deployment is explicitly non-applicable;
- the truth gate reports the real remaining blockers;
- the focused issue and #898 are updated with exact evidence.

Vercel proves the Next.js application build and runtime only. It does not prove Python, Cloud Run, Cloud SQL, worker, webhook, or credential behavior unless those paths are explicitly exercised.

## Handoff format

A handoff contains:

- Current state: exact head and completed artifacts.
- Blockers: verified failures or missing authority.
- Next action: one executable step.
- Owner: the agent or human authority required.

Handoffs without artifacts are planning notes, not progress.

## Safe controller loop

`detect → validate canonical unit → claim with receipt → act → verify exact head → update issue and #898 → stop`

The controller exits without invoking an agent when nothing changed. It does not create duplicate status issues or comments for unchanged healthy state.

## Prohibited shortcuts

- no competing implementation PR;
- no retroactive or invented provenance;
- no self-certified green result;
- no floating `@latest` workflow dependencies;
- no unrestricted shell, network, or repository permissions;
- no automatic merge or approval;
- no production deployment through repository agents;
- no credential exposure or mutation;
- no destructive branch cleanup;
- no static “current inventory” copied into this SOP.

## Current-state lookup

Read #898, then re-read every currently open PR and its focused issue. Bind all claims to the exact live head. If #898 disagrees with GitHub or Vercel, repair #898 from live evidence rather than treating the mirror as authoritative.
