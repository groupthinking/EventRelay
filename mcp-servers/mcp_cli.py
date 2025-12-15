#!/usr/bin/env python3
"""
MCP Local CLI
=============

A command-line interface to interact with MCP servers directly.
This allows "Antigravity" and projects to use MCP tools without a desktop client.

Usage:
  python3 mcp_cli.py list <server_script>
  python3 mcp_cli.py call <server_script> <tool_name> <json_args>

Example:
  python3 mcp_cli.py call servers/video_agent_server.py transcribe_media '{"url": "http://example.com/video.mp4"}'
"""

import sys
import json
import asyncio
import argparse
import subprocess
from typing import Dict, Any, Optional

async def run_mcp_command(server_script: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Run an MCP server script and send a JSON-RPC request."""
    
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        sys.executable, server_script,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Prepare request
    request_str = json.dumps(request) + "\n"
    
    try:
        # Send request and get response
        stdout, stderr = await process.communicate(input=request_str.encode())
        
        if stderr:
             # Log stderr but don't fail immediately, some servers log info to stderr
             sys.stderr.write(f"Server Log: {stderr.decode()}\n")

        # Parse output - might be multiple lines, we want the one matching our ID
        output_lines = stdout.decode().splitlines()
        for line in output_lines:
            try:
                response = json.loads(line)
                if response.get("id") == request.get("id"):
                    return response
            except json.JSONDecodeError:
                continue
                
        return {"error": "No matching response found", "raw_output": stdout.decode()}

    except Exception as e:
        return {"error": str(e)}

async def main():
    parser = argparse.ArgumentParser(description="MCP Local CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List tools provided by a server")
    list_parser.add_argument("server", help="Path to server script")
    
    # Call command
    call_parser = subparsers.add_parser("call", help="Call a tool")
    call_parser.add_argument("server", help="Path to server script")
    call_parser.add_argument("tool", help="Name of tool to call")
    call_parser.add_argument("args", help="JSON arguments for the tool", default="{}")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    server_path = args.server
    
    if args.command == "list":
        req = {
            "jsonrpc": "2.0",
            "id": "cli-list-1",
            "method": "tools/list",
            "params": {}
        }
        result = await run_mcp_command(server_path, req)
        print(json.dumps(result, indent=2))
        
    elif args.command == "call":
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError:
            print("Error: args must be valid JSON")
            return

        req = {
            "jsonrpc": "2.0",
            "id": "cli-call-1",
            "method": "tools/call",
            "params": {
                "name": args.tool,
                "arguments": tool_args
            }
        }
        result = await run_mcp_command(server_path, req)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
