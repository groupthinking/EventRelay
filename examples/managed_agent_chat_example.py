#!/usr/bin/env python3
"""
Managed Agent Chat (scaffold)
=============================

Talks to a pre-created Anthropic Managed Agent: opens a Session, streams the
agent's replies, and (optionally) holds a multi-turn conversation. The agent and
environment are persistent, server-side objects — referenced by ID, never
created here.

Configuration (precedence: flag > env var > built-in default)
-------------------------------------------------------------
  agent id        --agent  /  MANAGED_AGENT_ID        /  DEFAULT_AGENT_ID below
  environment id  --env    /  MANAGED_ENVIRONMENT_ID  /  DEFAULT_ENVIRONMENT_ID below

Auth: export ANTHROPIC_API_KEY=sk-ant-...
A RECENT `anthropic` SDK is required — the Managed Agents beta namespace
(client.beta.sessions) landed long after 0.7.0. `pip install -U anthropic`.

Usage
-----
    # single message, then exit (good for scripts / pipes)
    python examples/managed_agent_chat_example.py "Summarize today's standup"

    # interactive multi-turn REPL (Ctrl-D or /quit to exit)
    python examples/managed_agent_chat_example.py
    python examples/managed_agent_chat_example.py -i "first message"

    # point at a different agent/env without editing this file
    MANAGED_AGENT_ID=agent_xxx MANAGED_ENVIRONMENT_ID=env_yyy \
        python examples/managed_agent_chat_example.py
"""

import argparse
import os
import sys
from typing import List, Optional, Tuple

import anthropic

# Built-in defaults — overridable via --agent/--env or env vars (see docstring).
DEFAULT_AGENT_ID = "agent_01Vu9GHpHwKuvxgdLkFD57W4"
DEFAULT_ENVIRONMENT_ID = "env_01Ch7xi9bKAofLCEAccF2dJw"


# --- Custom-tool extension point ---------------------------------------------
def handle_custom_tool(name: str, tool_input: dict) -> Tuple[str, bool]:
    """Resolve a custom (client-side) tool call. Returns (result_text, is_error).

    Only YOUR application knows how to fulfil a custom tool, so this is the hook
    to extend. The safe default reports "not implemented" (is_error=True) so the
    agent can adapt instead of the session hanging forever waiting on a result.

    Example:
        if name == "get_weather":
            return json.dumps(lookup_weather(tool_input["city"])), False
    """
    return f"Custom tool {name!r} is not implemented in this client.", True


def user_message_event(text: str) -> dict:
    return {"type": "user.message", "content": [{"type": "text", "text": text}]}


def is_terminal_idle(event) -> bool:
    """True only for a *terminal* idle — not a transient 'requires_action' idle.

    The session also goes idle while waiting on us (a tool confirmation or a
    custom-tool result); those carry stop_reason.type == 'requires_action' and
    must be answered, not treated as "done". end_turn = finished,
    retries_exhausted = terminal failure — both are terminal.
    """
    stop_reason = getattr(event, "stop_reason", None)
    return getattr(stop_reason, "type", None) != "requires_action"


def confirm_tool(event) -> dict:
    """Prompt the human to allow/deny an `always_ask` tool call."""
    name = getattr(event, "name", "<tool>")
    answer = input(f"\n[confirm] allow tool {name!r}? [y/N] ").strip().lower()
    allow = answer in ("y", "yes")
    print(f"[confirm] {'allowed' if allow else 'denied'}", file=sys.stderr)
    return {
        "type": "user.tool_confirmation",
        "tool_use_id": event.id,  # the sevt_ event id, NOT a toolu_ id
        "result": "allow" if allow else "deny",
    }


def drive_turn(client, session_id: str, initial_events: List[dict]) -> str:
    """Drive one agent turn to completion, handling any requires_action pauses.

    Streams agent text to stdout, answers tool confirmations / custom-tool calls,
    and re-opens the stream after each batch of responses (stream-first each
    time). Returns 'idle' when the turn finishes normally, or 'terminated' on
    session end / error.
    """
    next_events: Optional[List[dict]] = initial_events
    while True:
        confirms: List = []
        customs: List = []
        terminal: Optional[str] = None

        with client.beta.sessions.events.stream(session_id=session_id) as stream:
            # Stream-first: the stream is open, now (re)send queued events into it.
            if next_events:
                client.beta.sessions.events.send(
                    session_id=session_id, events=next_events
                )
                next_events = None

            for event in stream:
                etype = getattr(event, "type", "")
                if etype == "agent.message":
                    for block in event.content:
                        if block.type == "text":
                            print(block.text, end="", flush=True)
                elif etype == "agent.custom_tool_use":
                    print(
                        f"\n[custom_tool_use] {getattr(event, 'name', '?')}",
                        file=sys.stderr,
                    )
                    customs.append(event)
                elif getattr(event, "evaluated_permission", None) == "ask":
                    # An always_ask built-in/MCP tool is waiting for approval.
                    confirms.append(event)
                elif etype == "session.error":
                    err = getattr(event, "error", None)
                    msg = getattr(err, "message", None) or repr(event)
                    print(f"\n[session.error] {msg}", file=sys.stderr, flush=True)
                    terminal = "terminated"
                    break
                elif etype == "session.status_terminated":
                    terminal = "terminated"
                    break
                elif etype == "session.status_idle":
                    # Done if terminal; otherwise leave the stream to respond.
                    if is_terminal_idle(event):
                        terminal = "idle"
                    break

        if terminal:
            return terminal

        # Paused on requires_action — build responses, then loop to re-stream.
        responses: List[dict] = [confirm_tool(c) for c in confirms]
        for c in customs:
            text, is_error = handle_custom_tool(
                getattr(c, "name", ""), getattr(c, "input", {}) or {}
            )
            responses.append(
                {
                    "type": "user.custom_tool_result",
                    "custom_tool_use_id": c.id,
                    "content": [{"type": "text", "text": text}],
                    "is_error": is_error,
                }
            )
        if not responses:
            # Idle/requires_action but nothing actionable recognized — bail
            # rather than spin forever.
            return "idle"
        next_events = responses


def repl(client, session_id: str) -> int:
    """Interactive multi-turn loop over a single, persistent session."""
    print("Entering chat. Ctrl-D or /quit to exit.", file=sys.stderr)
    while True:
        try:
            line = input("\nyou> ").strip()
        except EOFError:
            print(file=sys.stderr)
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return 0
        state = drive_turn(client, session_id, [user_message_event(line)])
        print()  # newline after the streamed reply
        if state == "terminated":
            print("[session terminated]", file=sys.stderr)
            return 1


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Chat with a pre-created Anthropic Managed Agent."
    )
    p.add_argument(
        "message", nargs="?", help="message to send; omit for an interactive REPL"
    )
    p.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="stay in a multi-turn REPL after sending MESSAGE",
    )
    p.add_argument(
        "--agent",
        default=os.environ.get("MANAGED_AGENT_ID", DEFAULT_AGENT_ID),
        help="agent id (env: MANAGED_AGENT_ID)",
    )
    p.add_argument(
        "--env",
        default=os.environ.get("MANAGED_ENVIRONMENT_ID", DEFAULT_ENVIRONMENT_ID),
        help="environment id (env: MANAGED_ENVIRONMENT_ID)",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    try:
        session = client.beta.sessions.create(
            agent=args.agent,  # bare string == latest version of that agent
            environment_id=args.env,
            title="managed-agent-chat scaffold",
        )
        print(
            "Watch in Console: "
            f"https://platform.claude.com/workspaces/default/sessions/{session.id}\n",
            file=sys.stderr,
        )

        if args.message:
            state = drive_turn(client, session.id, [user_message_event(args.message)])
            print()  # newline after the streamed reply
            if state == "terminated":
                return 1
            if not args.interactive:
                return 0

        return repl(client, session.id)

    except anthropic.APIError as exc:
        # Base class for auth, rate-limit, bad-request, connection, and 5xx
        # errors — one catch exits cleanly (no traceback to the user).
        print(f"\n[fatal] Anthropic API error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[interrupted]", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
