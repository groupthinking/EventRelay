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

Custom-command format and extension validation follow the official Gemini CLI
documentation:

- https://geminicli.com/docs/cli/custom-commands/
- https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/reference.md
