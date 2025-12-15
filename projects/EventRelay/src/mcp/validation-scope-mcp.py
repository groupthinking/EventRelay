#!/usr/bin/env python3
"""
Validation Scope Tracker MCP Server

Prevents false positives by tracking original validation scope and blocking
success declarations when scope drift is detected.

Usage:
1. start_validation_session(command, error_count) - Track baseline
2. check_scope_before_success(session_id, current_command, current_errors) - Validate scope
3. list_active_sessions() - Show current validation sessions
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import re
import shlex


class ValidationScopeTracker:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _normalize_command(self, command: str) -> str:
        """Normalize command for scope comparison"""
        # Remove common flags that don't change validation scope
        normalized = command.replace("--ignore-missing-imports", "").strip()
        normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace
        return normalized.lower()

    def _extract_command_core(self, command: str) -> tuple:
        """Extract core components: tool, targets, and scope-relevant flags"""
        parts = shlex.split(command.lower())
        if not parts:
            return (), ()

        # Find the main command (python3 -m mypy, eslint, etc.)
        tool_parts = []
        target_parts = []

        part_index = 0
        # Extract tool command (python3 -m mypy, eslint, etc.)
        while part_index < len(parts) and (
            not parts[part_index].endswith(".py")
            and not parts[part_index].endswith(".ts")
            and not parts[part_index].endswith(".js")
            and not parts[part_index].endswith("/")
            and not parts[part_index] in ["agents/", "utils/", "src/", "tests/"]
        ):
            if not parts[part_index].startswith("--"):
                tool_parts.append(parts[part_index])
            part_index += 1

        # Rest are targets and scope-relevant flags
        while part_index < len(parts):
            if not parts[part_index].startswith("--ignore"):  # Ignore non-scope flags
                target_parts.append(parts[part_index])
            part_index += 1

        return tuple(tool_parts), tuple(sorted(target_parts))

    def _commands_equivalent_scope(self, cmd1: str, cmd2: str) -> dict:
        """Check if commands test equivalent scope"""
        tool1, targets1 = self._extract_command_core(cmd1)
        tool2, targets2 = self._extract_command_core(cmd2)

        # Different tools = different scope
        if tool1 != tool2:
            return {
                "equivalent": False,
                "reason": "different_tool",
                "tool1": " ".join(tool1),
                "tool2": " ".join(tool2),
            }

        # Check if target scope is equivalent or broader
        targets1_set = set(targets1)
        targets2_set = set(targets2)

        # If current targets are subset of original, it's scope reduction
        if targets2_set < targets1_set:
            return {
                "equivalent": False,
                "reason": "scope_reduction",
                "original_scope": list(targets1),
                "current_scope": list(targets2),
                "missing_targets": list(targets1_set - targets2_set),
            }

        # If current includes all original targets (plus maybe more), it's valid
        if targets1_set <= targets2_set:
            return {
                "equivalent": True,
                "reason": "equivalent_or_broader_scope",
                "coverage": "full",
            }

        # Partial overlap
        overlap = targets1_set & targets2_set
        if overlap:
            return {
                "equivalent": False,
                "reason": "partial_overlap",
                "original_scope": list(targets1),
                "current_scope": list(targets2),
                "overlap": list(overlap),
                "missing_from_current": list(targets1_set - targets2_set),
            }

        # No overlap
        return {
            "equivalent": False,
            "reason": "completely_different_scope",
            "original_scope": list(targets1),
            "current_scope": list(targets2),
        }


# Initialize the MCP server
server = Server("validation-scope-tracker")
tracker = ValidationScopeTracker()


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available validation scope tracking tools"""
    return [
        types.Tool(
            name="start_validation_session",
            description="Start tracking a validation session with baseline command and error count",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The original validation command that failed (e.g., 'python3 -m mypy agents/ utils/')",
                    },
                    "error_count": {
                        "type": "integer",
                        "description": "Number of errors found by the original command",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of what we're fixing (e.g., 'Fix all mypy errors')",
                        "default": "",
                    },
                },
                "required": ["command", "error_count"],
            },
        ),
        types.Tool(
            name="check_scope_before_success",
            description="Verify validation scope before declaring success - prevents false positives",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The validation session ID from start_validation_session",
                    },
                    "current_command": {
                        "type": "string",
                        "description": "The command you want to run for final validation",
                    },
                    "current_errors": {
                        "type": "integer",
                        "description": "Number of errors found by current command (0 = success)",
                    },
                },
                "required": ["session_id", "current_command", "current_errors"],
            },
        ),
        types.Tool(
            name="list_active_sessions",
            description="Show all active validation sessions",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="close_validation_session",
            description="Close a validation session (mark as completed or cancelled)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The validation session ID to close",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["completed", "cancelled"],
                        "description": "Whether the session was completed successfully or cancelled",
                    },
                },
                "required": ["session_id", "status"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool calls for validation scope tracking"""

    if name == "start_validation_session":
        command = arguments["command"]
        error_count = arguments["error_count"]
        description = arguments.get("description", "")

        session_id = f"val_{uuid.uuid4().hex[:8]}"

        tracker.sessions[session_id] = {
            "id": session_id,
            "original_command": command,
            "original_error_count": error_count,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "scope_checks": [],
        }

        return [
            types.TextContent(
                type="text",
                text=f"""✅ Validation session started: `{session_id}`

**Original Scope:** `{command}`
**Baseline Errors:** {error_count}
**Description:** {description or 'N/A'}

🔒 This session will now track scope to prevent false positives.
Use `check_scope_before_success` before declaring any fixes complete.""",
            )
        ]

    elif name == "check_scope_before_success":
        session_id = arguments["session_id"]
        current_command = arguments["current_command"]
        current_errors = arguments["current_errors"]

        if session_id not in tracker.sessions:
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ **SESSION NOT FOUND:** `{session_id}`\n\nUse `list_active_sessions` to see available sessions.",
                )
            ]

        session = tracker.sessions[session_id]
        original_command = session["original_command"]
        original_errors = session["original_error_count"]

        # Check scope equivalence
        scope_analysis = tracker._commands_equivalent_scope(
            original_command, current_command
        )

        # Record this check
        check_record = {
            "timestamp": datetime.now().isoformat(),
            "command": current_command,
            "errors": current_errors,
            "scope_analysis": scope_analysis,
        }
        session["scope_checks"].append(check_record)

        if not scope_analysis["equivalent"]:
            # SCOPE DRIFT DETECTED - BLOCK SUCCESS
            reason = scope_analysis["reason"]

            if reason == "scope_reduction":
                missing = scope_analysis["missing_targets"]
                return [
                    types.TextContent(
                        type="text",
                        text=f"""🚨 **SCOPE DRIFT DETECTED - SUCCESS BLOCKED**

**Session:** `{session_id}`
**Issue:** Validation scope reduced - cannot declare success

**Original:** `{original_command}`
**Current:**  `{current_command}`

**Missing Targets:** {', '.join(missing)}

❌ **Cannot declare success on reduced scope**
✅ **Must run:** `{original_command}` 

**Progress:** {original_errors} → {current_errors} errors (on reduced scope)""",
                    )
                ]

            elif reason == "different_tool":
                return [
                    types.TextContent(
                        type="text",
                        text=f"""🚨 **SCOPE DRIFT DETECTED - DIFFERENT TOOL**

**Session:** `{session_id}`
**Original Tool:** `{scope_analysis['tool1']}`
**Current Tool:**  `{scope_analysis['tool2']}`

❌ **Cannot declare success with different validation tool**
✅ **Must use:** `{original_command}`""",
                    )
                ]

            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"""🚨 **SCOPE DRIFT DETECTED - SUCCESS BLOCKED**

**Session:** `{session_id}`
**Issue:** {reason.replace('_', ' ').title()}

**Original:** `{original_command}`
**Current:**  `{current_command}`

❌ **Cannot declare success on different scope**
✅ **Must run:** `{original_command}`

**Scope Analysis:** {json.dumps(scope_analysis, indent=2)}""",
                    )
                ]

        # SCOPE IS VALID
        if current_errors == 0:
            # SUCCESS!
            session["status"] = "success_ready"
            return [
                types.TextContent(
                    type="text",
                    text=f"""🎉 **SUCCESS VALIDATED - SCOPE CONFIRMED**

**Session:** `{session_id}`
**Progress:** {original_errors} → 0 errors ✅
**Scope:** Original scope maintained ✅

**Original:** `{original_command}`
**Final:**    `{current_command}`

✅ **ALL CLEAR:** Success declaration is valid!
🔒 **Scope Protection:** No false positive detected""",
                )
            ]
        else:
            # Still has errors, but scope is valid
            return [
                types.TextContent(
                    type="text",
                    text=f"""⚠️ **SCOPE VALID - ERRORS REMAINING**

**Session:** `{session_id}`
**Progress:** {original_errors} → {current_errors} errors
**Scope:** ✅ Original scope maintained

**Command:** `{current_command}`

🔄 **Continue fixing** - scope is correct, but {current_errors} errors remain.""",
                )
            ]

    elif name == "list_active_sessions":
        if not tracker.sessions:
            return [
                types.TextContent(
                    type="text",
                    text="📋 **No active validation sessions**\n\nUse `start_validation_session` to begin tracking validation scope.",
                )
            ]

        session_list = []
        for session_id, session in tracker.sessions.items():
            status_emoji = {
                "active": "🔄",
                "success_ready": "✅",
                "completed": "✅",
                "cancelled": "❌",
            }
            emoji = status_emoji.get(session["status"], "❓")

            session_list.append(
                f"""**{emoji} {session_id}**
Command: `{session['original_command']}`
Errors: {session['original_error_count']} → Status: {session['status']}
Created: {session['created_at'][:19]}
Checks: {len(session.get('scope_checks', []))}"""
            )

        return [
            types.TextContent(
                type="text",
                text=f"📋 **Active Validation Sessions**\n\n"
                + "\n\n".join(session_list),
            )
        ]

    elif name == "close_validation_session":
        session_id = arguments["session_id"]
        status = arguments["status"]

        if session_id not in tracker.sessions:
            return [
                types.TextContent(
                    type="text", text=f"❌ **SESSION NOT FOUND:** `{session_id}`"
                )
            ]

        tracker.sessions[session_id]["status"] = status
        tracker.sessions[session_id]["closed_at"] = datetime.now().isoformat()

        status_msg = (
            "✅ Completed successfully" if status == "completed" else "❌ Cancelled"
        )

        return [
            types.TextContent(
                type="text",
                text=f"""📋 **Session Closed:** `{session_id}`
**Status:** {status_msg}
**Command:** `{tracker.sessions[session_id]['original_command']}`""",
            )
        ]

    else:
        return [types.TextContent(type="text", text=f"❌ Unknown tool: {name}")]


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="validation-scope-tracker",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
