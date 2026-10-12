# EventRelay engineering Gemini extension

Repository-specific Gemini CLI commands for evidence-backed EventRelay
engineering work.

## Validate and link locally

From the repository root:

```bash
gemini extensions validate .gemini/extensions/eventrelay-engineering
gemini extensions link .gemini/extensions/eventrelay-engineering
```

After linking, start Gemini CLI from the EventRelay repository. If a running
session does not show the command, run `/commands reload`.

## Analyze code

Gemini CLI custom commands use a slash. The requested `@analyze-code` concept is
therefore exposed as `/analyze-code` and invoked as:

```text
/analyze-code src/youtube_extension/services/ai/gemini_service.py
/analyze-code origin/main...HEAD
```

With no argument, the command analyzes the smallest available local change set
and asks for a scope if there is no diff. It is intentionally read-only: it does
not edit code, install packages, call production services, or treat static
analysis as runtime proof.

## Generate tests

The requested `@generate-tests` concept is exposed as `/generate-tests`:

```text
/generate-tests src/youtube_extension/services/ai/gemini_service.py unit
/generate-tests apps/web/src/lib/gate-transition.ts unit
```

The command inspects the nearest existing test conventions, defaults to the
smallest hermetic unit tests, and runs the narrowest existing affected test
command. It modifies test files only. Integration or E2E coverage is selected
only when requested or when an observed boundary cannot be covered lower in the
test pyramid. Existing test files, shared fixtures, and snapshots require an
explicit confirmation before modification.

Generated files are not reported as passing behavior unless the exact test
command succeeds. The command does not call production services, install
dependencies, edit application code, or treat a test run as deployment proof.

Custom-command format and extension validation follow the official Gemini CLI
documentation:

- https://geminicli.com/docs/cli/custom-commands/
- https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/reference.md
