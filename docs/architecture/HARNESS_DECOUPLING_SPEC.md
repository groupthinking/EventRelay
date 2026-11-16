# Decoupled Brain & Ephemeral Sandbox Specification (UVAI / EventRelay)

## 1. Context & Motivation

- **Primary Evidence Source**: Y Combinator Frontier Harness Deep Dive (Published: 2026-09-07T14:35:31.000Z, [YC Status 2096970626036855197](https://x.com/ycombinator/status/2096970626036855197)).
- **Stable Key**: `evidence:x:ycombinator:2096970626036855197`
- **Empirical Observation**: The same base model weights achieve massive performance deltas (e.g., 30% to 95%+ on ARC-AGI-3) when equipped with an expressive, decoupled harness versus minimal scaffolding (e.g., OpenAI GPT-6 Astra scored 62.7% under the minimal harness vs. 99.9% under the Provider Adapter harness with retained reasoning traces & compaction).

In monolithic agent architectures, the reasoning engine (state, trajectory, memory) and the tool execution runtime reside inside the same disposable container. When the sandbox terminates or errors out, session context is wiped out.

---

## 2. Core Architectural Principles for UVAI / EventRelay

### 2.1 Decoupling the "Brain" from the Sandbox
- **Persistent Orchestration Plane (Brain)**:
  - Maintains conversational context, execution trajectory, verified SOP steps, and event timelines.
  - Resides outside the ephemeral execution sandbox (in EventRelay's core coordinator / FastAPI orchestrator).
  - Immune to worker-level crashes, OOMs, and timeouts.
- **Disposable Execution Workers (Sandbox)**:
  - Ephemeral containers or isolated processes (Python code execution, browser automation, media processing / ASR).
  - Can be restarted, hot-swapped, or migrated dynamically without resetting the orchestrator's state.
  - Dynamically selectable by the agent depending on task security and resource requirements.

### 2.2 Hierarchical Context Management (L1 / L2 / L3 Cache)
Inspired by Prime Agent (RLM) & von Neumann computing architecture:
- **L1 Cache (Working Memory)**: Immediate working prompt, active tool call parameters, active plan, current SOP step.
- **L2 Cache (Session / Vector Store)**: Trajectory memory, parsed video transcripts, aligned timestamps, segment embeddings, recent tool outputs.
- **L3 Store (Durable Cold Archive)**: Execution receipts, durable database records (`neondb.concept_tracker`), changelog archives, git state.

### 2.3 The "Grind Guard": Hard Goal Budgets
To prevent infinite autonomous loops and runaway token/compute expenses:
- **Token Ceiling**: Strict input/output token maximums per task trajectory.
- **Tool Call Bound**: Maximum permissible tool iterations before mandatory human-in-the-loop review.
- **Time & Cost Limits**: Explicit wall-clock timeout and currency expenditure bounds.
- **Clean Escalation**: If a budget ceiling is approached, the agent must serialize its intermediate state, generate an execution receipt, and transition cleanly into `AWAITING_AUTHORIZATION` or `SUSPENDED_BUDGET_EXCEEDED` rather than crashing.

---

## 3. Ecosystem Mapping & Relationship Matrix

| Entity | Primary Concept | Relationship to EventRelay / UVAI | Confidence |
| :--- | :--- | :--- | :--- |
| **QM (Quartermaster)** | Multiplayer Enterprise Harness | *pattern similarity* / *architectural precursor* | 0.92 |
| **OpenClaw** | Local Multi-Agent Workstation Suite | *operational environment component* | 0.95 |
| **Prime Agent** | Self-improving RLM Harness | *pattern similarity* for Self-Correcting Executor | 0.90 |
| **OpenJarvis** | On-device Personal AI Stack | *pattern to watch* for local media extraction | 0.85 |
| **Hayden MHS** | User MHS Implementation | *strictly separate* from Anthropic MHS & Google video | 1.00 |
| **Anthropic MHS** | Vendor Model Harness Suite | *strictly separate* from Hayden MHS & Google video | 1.00 |
| **Google Agentic Video** | Multimodal Video Framework | *strictly separate* from MHS entities | 1.00 |
| **MDS** | Undefined Architecture Element | *undefined* (no speculation permitted) | 0.00 |

---

## 4. Verification & Operational Directives
- **Verification Rule**: No `SAME_AS` equivalence asserted without primary documentation, verified status, and $\ge 0.950$ confidence.
- **State Persistence**: Durable receipts must record exact mutations, inputs, decisions, blockers, and next actions.
