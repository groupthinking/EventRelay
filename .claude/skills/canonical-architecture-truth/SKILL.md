---
name: canonical-architecture-truth
description: >-
  Determine what is current, canonical, and live versus legacy, redirect-only,
  historical, or prototype. Use for entrypoint truth, runtime boundaries,
  deployment truth, and public product naming.
---

# Canonical Architecture Truth

## Purpose
Establish the current, active architecture of UVAI/EventRelay before any
broader audit, implementation, or remediation work begins.

## When to Use
- Mapping the canonical web and backend entrypoints
- Distinguishing live paths from redirect-only or historical paths
- Verifying the current authority chain for product and runtime truth
- Resolving disputes about what is production, legacy, or prototype

## Required Evidence
- Anchor conclusions to `/home/runner/work/EventRelay/EventRelay/AGENTS.md`
- Cross-check `/home/runner/work/EventRelay/EventRelay/README.md`
- Use `/home/runner/work/EventRelay/EventRelay/docs/REPO_MAP.md` for current
  source navigation
- Cite exact files and line numbers for frontend entrypoints, backend
  entrypoints, workflow paths, redirects, and deployment boundaries
- Treat historical architecture records as history unless current code confirms
  them

## Outputs
- Canonical-vs-legacy map
- Frontend entrypoint map
- Backend entrypoint map
- Deployment truth summary
- Runtime boundary notes with citations
