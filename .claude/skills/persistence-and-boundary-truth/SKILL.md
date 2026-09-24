---
name: persistence-and-boundary-truth
description: >-
  Map every real persistence surface and security boundary. Use for storage
  truth, middleware/auth boundaries, public-vs-gated APIs, and contradictions
  across runtime layers.
---

# Persistence and Boundary Truth

## Purpose
Produce one evidence-backed map of storage systems, state boundaries, and
security controls across the UVAI/EventRelay runtime.

## When to Use
- Auditing persistent state ownership
- Verifying pack-storage truth
- Mapping public versus protected routes
- Reviewing middleware, auth, rate-limit, and store contradictions

## Required Evidence
- Verify Video Pack persistence from the active web store implementation
- Verify backend SQL state from active database configuration and models
- Verify local or file-backed stores separately from production stores
- Cite auth and middleware policy from route and middleware source, not docs
- Explicitly call out contradictions such as web Upstash pack truth versus
  backend filesystem VideoPack paths

## Outputs
- Persistence truth map
- Security boundary map
- Public-vs-gated API list
- Middleware/auth summary
- Contradiction list with citations
