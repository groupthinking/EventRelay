# Copilot User Persona Map

Use this map to adapt explanations, implementation choices, and questions to the
person the user is helping. The persona describes the user's working context; it
does not override repository instructions, security policy, or the single
YouTube-link-to-agent-execution workflow.

## The Builder

- **Context:** A developer who wants to turn a YouTube walkthrough into working
  code, architecture, or a deployable build rail.
- **Needs:** Concrete implementation steps, type-safe examples, tests, and clear
  handoff points from extracted events to agents.
- **Copilot response:** Prefer existing repository patterns and minimal patches.
  Explain assumptions and show how to verify the result.

## The Product/Technical Founder

- **Context:** A founder or technical product owner validating an idea and
  moving from video-derived insight to a shippable product direction.
- **Needs:** Outcome-oriented architecture, trade-offs, scope boundaries, and
  honest evidence about what is implemented.
- **Copilot response:** Connect recommendations to user value and shipping
  outcomes without inventing pricing, integrations, or product capabilities.

## The Automation or Operations Lead

- **Context:** A team member translating a process demonstrated in a video into
  repeatable workflows and agent actions.
- **Needs:** Event definitions, orchestration behavior, observability, failure
  handling, and safe operational boundaries.
- **Copilot response:** Keep the YouTube context, event extraction, agent
  dispatch, and output publication traceable. Call out retries, permissions,
  and rollback concerns.

## The Educator or Researcher

- **Context:** A learner, instructor, or analyst using video content to
  understand a technical subject and its practical applications.
- **Needs:** Plain-language explanations, source context, progressive detail,
  and examples that distinguish facts from generated suggestions.
- **Copilot response:** Define unfamiliar terms, preserve transcript grounding,
  and label uncertainty rather than presenting inference as evidence.

## The Enterprise Engineering Team

- **Context:** Engineers evaluating EventRelay for secure, multi-provider,
  production workflows.
- **Needs:** API contracts, authentication, data isolation, reliability,
  compliance considerations, and deployment constraints.
- **Copilot response:** Use validated inputs, environment-based configuration,
  least privilege, structured errors, and existing MCP/API patterns. Never
  expose credentials or claim an integration exists without repository evidence.

## The EventRelay Contributor

- **Context:** A maintainer extending the backend, frontend, MCP servers, or
  documentation.
- **Needs:** Repository conventions, focused tests, backward compatibility, and
  a small, reviewable change.
- **Copilot response:** Follow the project workflow and local instructions,
  inspect existing code before changing it, add regression coverage for
  behavior changes, and run the narrowest relevant checks first.

## Persona selection rules

1. Infer a persona only from the user's request and available repository
   context; if more than one fits, ask a short clarifying question.
2. Treat persona-specific guidance as communication context, not authorization
   to bypass validation, authentication, safety checks, or review.
3. Keep the core workflow intact: YouTube link → context extraction → events →
   agent dispatch → outputs.
4. When a request conflicts with repository evidence, state the conflict and
   defer to the code and documented project policy.
