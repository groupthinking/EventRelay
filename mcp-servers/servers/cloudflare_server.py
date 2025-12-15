#!/usr/bin/env python3
"""
Cloudflare MCP Server
=====================

Exposes Cloudflare capabilities as an MCP Server.
"""

import asyncio
import json
import logging
import sys
import os
import requests
from typing import Dict, Any, Optional

# Add lib directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, '..', 'lib')
sys.path.append(LIB_DIR)

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger("cloudflare-server")

# Constants
MCP_VERSION = "2024-11-05"
CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
# Credentials from task context
ACCOUNT_ID = "a8b9cb3a634fca2b1a670019dfa76e15"
# Using the primary token from the top of the file
API_TOKEN = "QowMt_bpgC9kc0hD5WRQ2DdlAw0kvOQVFOBcFZLb"

class CloudflareServer:
    def __init__(self):
        self.account_id = ACCOUNT_ID
        self.api_token = API_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })

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
                    "name": "Cloudflare MCP",
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
                        "name": "get_gateway_url",
                        "description": "Get the URL for a Cloudflare AI Gateway",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "gateway_id": {"type": "string", "description": "The ID/Name of the gateway (e.g. 'netmesh')"},
                                "provider": {"type": "string", "description": "The provider name (e.g. 'openai', 'anthropic')"}
                            },
                            "required": ["gateway_id", "provider"]
                        }
                    }
                ]
            }
        }

    async def _handle_tools_call(self, request_id, params):
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = {}
        
        if tool_name == "get_gateway_url":
            gateway_id = arguments.get("gateway_id")
            provider = arguments.get("provider")
            if not gateway_id or not provider:
                raise ValueError("gateway_id and provider are required")
            
            url = f"{CLOUDFLARE_API_BASE}/accounts/{self.account_id}/ai-gateway/gateways/{gateway_id}/url/{provider}"
            
            try:
                # Run blocking IO in executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self._make_request, url)
                
                if response.ok:
                   data = response.json()
                   if data.get("success"):
                       result_url = data.get("result")
                       result = {
                           "url": result_url,
                           "full_response": data
                       }
                   else:
                       raise Exception(f"Cloudflare API error: {data.get('errors')}")
                else:
                    raise Exception(f"HTTP Error {response.status_code}: {response.text}")

            except Exception as e:
                raise Exception(f"Request failed: {str(e)}")

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

    def _make_request(self, url):
        return self.session.get(url)

async def main():
    server = CloudflareServer()
    LOGGER.info("Cloudflare MCP Server running on stdio...")
    
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
                
            request_data = json.loads(line)
            response = await server.handle_request(request_data)
            
            if response:
                response_str = json.dumps(response)
                if writer:
                    writer.write(response_str.encode() + b"\n")
                    await writer.drain()
                else:
                    sys.stdout.write(response_str + "\n")
                    sys.stdout.flush()
                    
        except json.JSONDecodeError:
            pass 
        except Exception as e:
            LOGGER.error(f"Loop error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
