"""Minimal Deep MCP Agent example.

See README in project root for overall project; this file is a standalone
example that can be executed directly with the prepared venv.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import sys
import importlib.util as _importlib_util
from typing import Dict

from deepmcpagent import (
    build_deep_agent,
    HTTPServerSpec,
    StdioServerSpec,
)
from deepmcpagent.prompt import DEFAULT_SYSTEM_PROMPT
from langgraph.prebuilt import create_react_agent


def _detect_default_model() -> str:
    explicit_model = os.getenv("MODEL")
    if explicit_model:
        return explicit_model
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-3-5-sonnet-latest"
    has_openai_pkg = _importlib_util.find_spec("langchain_openai") is not None
    if os.getenv("OPENAI_API_KEY") and has_openai_pkg:
        return "openai:gpt-4o-mini"
    return "anthropic:claude-3-5-sonnet-latest"


def _build_servers_from_env() -> Dict[str, object]:
    servers: Dict[str, object] = {}
    http_url = os.getenv("MCP_HTTP_URL")
    if http_url:
        transport = os.getenv("MCP_HTTP_TRANSPORT", "sse")
        servers["http-default"] = HTTPServerSpec(url=http_url, transport=transport)
    stdio_cmd = os.getenv("MCP_STDIO_COMMAND")
    if stdio_cmd:
        args_str = os.getenv("MCP_STDIO_ARGS", "").strip()
        args_list = shlex.split(args_str) if args_str else []
        servers["stdio-default"] = StdioServerSpec(command=stdio_cmd, args=args_list)
    return servers


async def _run(args: argparse.Namespace) -> int:
    servers = _build_servers_from_env()
    model_str = _detect_default_model()

    if not args.dry_run:
        if model_str.startswith("anthropic:") and not os.getenv("ANTHROPIC_API_KEY"):
            print("Missing ANTHROPIC_API_KEY; set it or pass MODEL env. Use --dry-run to just build.", file=sys.stderr)
            return 2
        if model_str.startswith("openai:") and not os.getenv("OPENAI_API_KEY"):
            print("Missing OPENAI_API_KEY; set it or pass MODEL env. Use --dry-run to just build.", file=sys.stderr)
            return 2

    system_instructions = os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

    graph = None
    loader = None
    if servers:
        graph, loader = await build_deep_agent(
            servers=servers,
            model=model_str,
            instructions=system_instructions,
            trace_tools=args.trace_tools,
        )
    else:
        # Fallback: build a simple agent without tools so dry-run works
        graph = create_react_agent(model=model_str, tools=[], prompt=system_instructions)

    if args.list_tools:
        try:
            if loader is None:
                print("No MCP servers configured; no tools available.")
            else:
                tools = await loader.get_all_tools()
                if not tools:
                    print("No tools discovered from configured MCP servers.")
                else:
                    print("Discovered tools:")
                    for t in tools:
                        print(f"- {getattr(t, 'name', '<unnamed>')}: {getattr(t, 'description', '')}")
        except Exception as exc:
            print(f"Failed to list tools: {exc}", file=sys.stderr)

    if args.dry_run:
        print("Graph built successfully (dry run).")
        return 0

    user_input = args.prompt
    if not user_input:
        print("No prompt provided. See --help.", file=sys.stderr)
        return 2

    state = {"messages": [("user", user_input)]}
    result = await graph.ainvoke(state)
    try:
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            content = getattr(last, "content", last)
            print(str(content))
        else:
            print(str(result))
    except Exception:
        print(str(result))
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal Deep MCP Agent.")
    parser.add_argument("prompt", nargs="?", help="User input for the agent.")
    parser.add_argument("--dry-run", action="store_true", help="Build the agent without invoking the model.")
    parser.add_argument("--list-tools", action="store_true", help="List discovered tools from MCP servers.")
    parser.add_argument("--trace-tools", action="store_true", help="Print tool calls and results.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        exit_code = asyncio.run(_run(args))
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

