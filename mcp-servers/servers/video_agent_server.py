#!/usr/bin/env python3
"""
Video Agent MCP Server
======================

Exposes Video Processing capabilities (Transcription, Action Generation) 
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
    from agents.video_subagents import TranscriptionAgent, ActionGeneratorAgent
except ImportError:
    # Fallback if agents package structure is different
    from video_subagents import TranscriptionAgent, ActionGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger("video-agent-server")

# Constants
MCP_VERSION = "2024-11-05"

class MCPServer:
    def __init__(self):
        self.transcription_agent = TranscriptionAgent()
        self.action_agent = ActionGeneratorAgent()
        
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
                    "name": "Video Agent MCP",
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
                        "name": "transcribe_media",
                        "description": "Transcribe audio/video content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "URL of the media"},
                                "file_path": {"type": "string", "description": "Local path to media file"},
                                "format": {"type": "string", "description": "Media format (mp4, mp3, etc)"}
                            },
                        }
                    },
                    {
                        "name": "generate_actions",
                        "description": "Generate actionable items from video transcript",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "transcript": {
                                    "type": "object",
                                    "description": "Transcript object with text and segments"
                                },
                                "content_type": {
                                    "type": "string", 
                                    "enum": ["tutorial", "educational", "meeting", "general"],
                                    "description": "Type of video content"
                                }
                            },
                            "required": ["transcript"]
                        }
                    },
                    {
                        "name": "process_video_pipeline",
                        "description": "Full pipeline: Transcribe -> Generate Actions",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "content_type": {"type": "string"}
                            },
                            "required": ["url"]
                        }
                    }
                ]
            }
        }

    async def _handle_tools_call(self, request_id, params):
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = {}
        
        if tool_name == "transcribe_media":
            # Delegate to TranscriptionAgent using 'data' wrapper expected by process_intent logic
            # OR direct method call if we know the class structure.
            # The agent has _transcribe_media(data) method.
            result = await self.transcription_agent._transcribe_media(arguments)
            
        elif tool_name == "generate_actions":
            result = await self.action_agent._generate_actions(arguments)
            
        elif tool_name == "process_video_pipeline":
            # Chain transcription and action generation
            transcription = await self.transcription_agent._transcribe_media(arguments)
            if transcription.get("status") == "error":
                result = transcription
            else:
                # Prepare data for action generator
                action_args = {
                    "transcript": transcription,
                    "content_type": arguments.get("content_type", "general"),
                    "metadata": {"title": arguments.get("url", "unknown")}
                }
                actions = await self.action_agent._generate_actions(action_args)
                result = {
                    "transcription": transcription,
                    "actions": actions
                }
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
    LOGGER.info("Video Agent Server running on stdio...")
    
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
            
            if response: # Notifications might return None
                response_str = json.dumps(response) + "\n"
                if writer:
                    writer.write(response_str.encode())
                    await writer.drain()
                else:
                    print(response_str, flush=True)
                    
        except json.JSONDecodeError:
            pass # Ignore malformed lines or use proper error handling
        except Exception as e:
            LOGGER.error(f"Loop error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
