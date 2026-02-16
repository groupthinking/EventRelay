import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class MCPServerConfig:
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None

class MCPClient:
    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self.process = None
        self._request_id = 0
        self._pending_requests = {}
        self._reader_task = None

    async def start(self):
        """Start the MCP server subprocess"""
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)

        # Ensure we don't buffer stdout to ensure real-time communication
        self.process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        self._reader_task = asyncio.create_task(self._read_loop())

    async def stop(self):
        """Stop the MCP server"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
        if self._reader_task:
            self._reader_task.cancel()

    async def _read_loop(self):
        """Read standard out from server"""
        if not self.process:
            return

        while True:
            try:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    message = json.loads(line_str)
                    # Handle JSON-RPC response
                    if "id" in message and message["id"] in self._pending_requests:
                        future = self._pending_requests.pop(message["id"])
                        if "error" in message:
                            future.set_exception(Exception(message["error"].get("message", "Unknown error")))
                        else:
                            future.set_result(message.get("result"))
                except json.JSONDecodeError:
                    # Ignore non-JSON output (logs, etc.)
                   pass
            except Exception as e:
                print(f"Error in MCP read loop: {e}", file=sys.stderr)
                break

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool on the MCP server"""
        if not self.process:
            await self.start()

        self._request_id += 1
        arguments = arguments or {}
        
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[self._request_id] = future
        
        input_data = json.dumps(request) + "\n"
        self.process.stdin.write(input_data.encode())
        await self.process.stdin.drain()
        
        # Wait for response with simple timeout
        return await asyncio.wait_for(future, timeout=60.0)

    async def list_tools(self) -> List[Any]:
        """List available tools"""
        if not self.process:
            await self.start()

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/list",
            "params": {}
        }

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[self._request_id] = future

        input_data = json.dumps(request) + "\n"
        self.process.stdin.write(input_data.encode())
        await self.process.stdin.drain()

        result = await asyncio.wait_for(future, timeout=30.0)
        return result.get("tools", [])
