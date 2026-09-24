---
name: github-ops-and-workflow-health
description: >-
  Inspect workflow inventory, recent run health, stale or legacy workflows,
  branch/process drift, and governance overlap using GitHub metadata plus local
  workflow definitions.
---

# GitHub Ops and Workflow Health

## Purpose
Establish the real operational state of repository automation, CI, workflow
health, and GitHub governance.

## When to Use
- Investigating CI or workflow failures
- Auditing stale or redundant workflows
- Comparing local workflow files to remote GitHub workflow inventory
- Reviewing issue/PR linkage hygiene and automation overlap

## Required Evidence
- Use local workflow files under `/home/runner/work/EventRelay/EventRelay/.github/workflows`
- Use GitHub workflow metadata and recent run results
- Inspect failed job logs before attributing a workflow failure
- Separate current local workflow truth from historical workflows still present
  in GitHub metadata
- Cite issue and PR evidence when describing governance drift

## Outputs
- Workflow inventory
- Recent run health summary
- Workflow cleanup recommendations
- Branch/process drift notes
- GitHub governance overlap summary
