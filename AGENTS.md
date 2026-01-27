# Jules Agent System: Architectural Axioms & Protocol

**Role:** High-Integrity Systems Auditor & First-Principles Engineer
**Objective:** Maintain a clean, scalable, and logic-driven codebase.

## 1. Architectural Geography (The "Where")

Any code added to this repository MUST inhabit one of the following domains. **Root-level directories are strictly forbidden** without a Request for Comments (RFC).

### ✅ `apps/` (The Runnable)
*   **Purpose:** End-user applications, services, and deployed agents.
*   **Examples:** Web dashboards, Mobile apps, Python Agent Runners, Electron apps.
*   **Rule:** If it runs, it lives here.

### ✅ `packages/` (The Shared - TypeScript/Node)
*   **Purpose:** Shared libraries, UI components, utilities, and schemas.
*   **Examples:** `ui-kit`, `logger`, `database-client`.
*   **Rule:** If it's imported by multiple `apps`, it lives here.

### ✅ `mcp-servers/` (The Protocol)
*   **Purpose:** Model Context Protocol (MCP) servers and connectors.
*   **Examples:** `github-mcp`, `grok-server`, `filesystem-mcp`.
*   **Rule:** If it exposes tools via MCP, it lives here.

### ✅ `shared/` (The Shared - Polyglot/Python)
*   **Purpose:** Shared libraries that are not strictly Node.js packages.
*   **Examples:** `shared/libs/python-utils`, `shared/libs/xai-grok-wrapper`.
*   **Rule:** Python libraries and cross-language assets live here.

### ✅ `infrastructure/` (The Foundation)
*   **Purpose:** Infrastructure as Code (IaC), Docker configurations, CI/CD pipelines, and Service definitions.
*   **Examples:** `dataconnect`, `kubernetes`, `terraform`.
*   **Rule:** If it configures the environment, it lives here.

### ✅ `docs/` (The Knowledge)
*   **Purpose:** Documentation, architectural decision records (ADRs), and knowledge bases.
*   **Rule:** If it explains "Why" or "How", it lives here.

---

## 2. Ruthless Remediation Protocol (The "How")

When an Agent encounters a violation of these axioms:
1.  **Identify:** Flag the file/directory.
2.  **Interrogate:** Why is it here? (5 Whys).
3.  **Remediate:** Move it to its correct domain immediately.
4.  **Fortify:** Update this document or add programmatic checks to prevent recurrence.

## 3. Nightly Audit Checklist

*   [ ] No loose directories in root (except `apps`, `packages`, `mcp-servers`, `shared`, `infrastructure`, `docs`, `config`, `scripts`, `tools`, `tests`).
*   [ ] All new Python code is either in `apps/` (runnable) or `shared/libs/` (importable).
*   [ ] All new TypeScript code is in `apps/` or `packages/`.
