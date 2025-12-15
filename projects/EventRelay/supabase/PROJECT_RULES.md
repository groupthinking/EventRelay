# Project Rules (Minimum Viable Set)

## 1. Purpose-First Mandate

- Every new feature, agent, or workflow must start with a clear statement of its core problem and intended user impact.
- All major decisions must be traceable to these objectives.

## 2. Zero Placeholder Policy

- No placeholder, mock, or scaffolding code is allowed in production or beta.
- All temporary code must be flagged and removed before deployment.

## 3. Coverage, Traceability, and Proof

- All features must be operational, testable, and traceable.
- No feature is "done" until it is covered by automated or manual tests that prove its integrity.

## 4. Debug & Failure Mode Readiness

- All systems must have robust error handling, logging, and fallback mechanisms.
- Simulate/document failure modes (API errors, network loss, invalid input) before release.

## 5. Documentation Synchronization

- All .md files (README, implementation guide, next steps) must reflect the current system state.
- Documentation must be updated with every major change or deployment.

## 6. CI/CD & Containerization

- Every project must have a CI pipeline (lint, type check, tests, build) and be containerized (Docker) for reproducibility.

## 7. Meta-Rule: Rule Expansion Notification

- The system (or AI assistant) will notify the project owner when it is time to formalize or expand the ruleset, based on project growth, team size, or complexity.

---

*Other rules (performance, security, edge cases, cross-platform, etc.) will be formalized as the project scales or as needs arise.* 