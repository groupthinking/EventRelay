#!/usr/bin/env python3
"""
Code Analysis Agent MCP Server
==============================

Exposes Code Analysis capabilities (Security, Performance, Style) 
as an MCP Server.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add lib directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, '..', 'lib')
# Add agents directory to path specifically for direct imports if needed
AGENTS_DIR = os.path.join(LIB_DIR, 'agents')
sys.path.append(LIB_DIR)
sys.path.append(AGENTS_DIR)

try:
    from agents.code_analysis_subagents import SecurityAnalyzerAgent, PerformanceOptimizerAgent, StyleCheckerAgent
except ImportError:
    # Fallback if agents package structure is different
    from code_analysis_subagents import SecurityAnalyzerAgent, PerformanceOptimizerAgent, StyleCheckerAgent

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger("code-analysis-server")

# Constants
MCP_VERSION = "2024-11-05"

class MCPServer:
    def __init__(self):
        self.security_agent = SecurityAnalyzerAgent()
        self.performance_agent = PerformanceOptimizerAgent()
        self.style_agent = StyleCheckerAgent()
        
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC requests."""
        request_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        LOGGER.info(f"Handling request: {method} (ID: {request_id})")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(request_id, params)
            elif method == "notifications/initialized":
                return None # No response needed
            else:
                raise Exception(f"Unknown method: {method}")

        except Exception as e:
            LOGGER.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)},
            }

    def _handle_initialize(self, request_id, params):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "serverInfo": {
                    "name": "Code Analysis Agent MCP",
                    "version": "1.0.0",
                    "mcpVersion": MCP_VERSION,
                },
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
            }
        }

    def _handle_tools_list(self, request_id):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "scan_security",
                        "description": "Perform security scan on code",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string", "description": "Source code to scan"},
                                "language": {"type": "string", "description": "Programming language (default: python)"}
                            },
                            "required": ["code"]
                        }
                    },
                    {
                        "name": "analyze_performance",
                        "description": "Analyze code performance and identify bottlenecks",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "language": {"type": "string"}
                            },
                            "required": ["code"]
                        }
                    },
                    {
                        "name": "check_style",
                        "description": "Check code style and conventions",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "language": {"type": "string"}
                            },
                            "required": ["code"]
                        }
                    }
                ]
            }
        }

    async def _handle_tools_call(self, request_id, params):
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = {}
        
        # Map MCP tools to Agent internal methods
        # Note: The agents expect a 'data' dictionary in their internal intents
        # so we wrap arguments in the expected structure if calling _perform_* methods DIRECTLY
        # OR we call process_intent if we want the full agent flow.
        # Direct method calls are safer/simpler here since we know the mapping.
        
        if tool_name == "scan_security":
            result = await self.security_agent._perform_security_scan(arguments)
            
        elif tool_name == "analyze_performance":
            result = await self.performance_agent._analyze_performance(arguments)

        elif tool_name == "check_style":
            result = await self.style_agent._check_style(arguments)
            
        else:
            raise Exception(f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "mimeType": "application/json",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        }

async def main():
    server = MCPServer()
    LOGGER.info("Code Analysis Server running on stdio...")
    
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    writer = None
    if sys.platform != "win32":
        w_transport, w_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.Protocol, sys.stdout
        )
        writer = asyncio.StreamWriter(w_transport, w_protocol, None, asyncio.get_event_loop())

    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            
            request = json.loads(line)
            response = await server.handle_request(request)
            
            if response: 
                response_str = json.dumps(response) + "\n"
                if writer:
                    writer.write(response_str.encode())
                    await writer.drain()
                else:
                    print(response_str, flush=True)
                    
        except json.JSONDecodeError:
            pass 
        except Exception as e:
            LOGGER.error(f"Loop error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
