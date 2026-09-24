---
name: engineering-risk-and-duplication-audit
description: >-
  Produce a severity-ranked, evidence-backed risk register for duplication, doc
  drift, silent failures, overlapping systems, and dead or parallel surfaces.
---

# Engineering Risk and Duplication Audit

## Purpose
Identify the highest-confidence engineering risks in the repository and rank
them by severity and likely operational impact.

## When to Use
- Building a risk register
- Auditing duplicated code or docs
- Investigating broad exception handling and silent failure patterns
- Reviewing multiple entrypoints, overlapping orchestrators, or dead paths

## Required Evidence
- Cite duplicated route trees, duplicate documents, and parallel implementations
- Count or sample broad exception patterns from active code paths
- Verify multiple entrypoints and orchestrators from source
- Verify model/migration ambiguity from the committed schema and migrations
- Distinguish active production surfaces from experimental or historical ones

## Outputs
- Severity-ranked risk register
- Duplication table
- Documentation drift list
- Overlapping subsystem list
- Remediation priorities with citations
