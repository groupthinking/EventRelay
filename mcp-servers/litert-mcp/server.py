#!/usr/bin/env python3
"""
LiteRT-LM MCP Server
====================

Exposes Google's LiteRT-LM (Edge LLM Runtime) capabilities as an MCP Server.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
LOGGER = logging.getLogger("litert-mcp-server")

# Constants
MCP_VERSION = "2024-11-05"

class MCPServer:
    def __init__(self):
        self.default_model_path = os.environ.get("LIT_MODEL_PATH")
        self.lit_binary = os.environ.get("LIT_BINARY_PATH", "lit")

    async def handle_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
                return None  # No response needed
            else:
                # For unknown methods, proper JSON-RPC error code -32601
                if request_id is not None:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                return None

        except Exception as e:
            LOGGER.error(f"Error handling request: {e}", exc_info=True)
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": str(e)},
                }
            return None

    def _handle_initialize(self, request_id, params):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "serverInfo": {
                    "name": "LiteRT-LM MCP",
                    "version": "1.0.0",
                    "mcpVersion": MCP_VERSION,
                },
                "capabilities": {
                    "tools": {},
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
                        "name": "run_inference",
                        "description": "Run inference using a LiteRT-LM model. Supports text generation and optionally multimodal inputs if supported by the runtime.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The input text prompt."
                                },
                                "model_path": {
                                    "type": "string",
                                    "description": "Path to the .litertlm model file. Overrides LIT_MODEL_PATH."
                                },
                                "image_path": {
                                    "type": "string",
                                    "description": "Path to an image file for multimodal inference."
                                },
                                "audio_path": {
                                    "type": "string",
                                    "description": "Path to an audio file for multimodal inference."
                                },
                                "backend": {
                                    "type": "string",
                                    "enum": ["cpu", "gpu", "npu"],
                                    "default": "cpu",
                                    "description": "Compute backend to use."
                                }
                            },
                            "required": ["prompt"]
                        }
                    }
                ]
            }
        }

    async def _handle_tools_call(self, request_id, params):
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = {}

        if tool_name == "run_inference":
            result = await self._run_inference(arguments)
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

    async def _run_inference(self, args: Dict[str, Any]) -> Dict[str, Any]:
        prompt = args.get("prompt")

        # Validate prompt parameter
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return {
                "status": "error",
                "message": "Invalid or empty prompt. Please provide a non-empty text prompt."
            }

        model_path = args.get("model_path") or self.default_model_path
        image_path = args.get("image_path")
        audio_path = args.get("audio_path")
        backend = args.get("backend", "cpu")

        # Validate backend parameter
        valid_backends = ["cpu", "gpu", "npu"]
        if backend not in valid_backends:
            return {
                "status": "error",
                "message": f"Invalid backend '{backend}'. Must be one of {valid_backends}."
            }

        # Validate Prompt
        if not prompt:
            return {
                "status": "error",
                "message": "Prompt is required and cannot be empty."
            }

        # Validate Backend
        valid_backends = {"cpu", "gpu", "npu"}
        if backend not in valid_backends:
            return {
                "status": "error",
                "message": f"Invalid backend '{backend}'. Must be one of {sorted(list(valid_backends))}."
            }

        if not model_path:
            return {
                "status": "error",
                "message": "No model path provided. Set LIT_MODEL_PATH env var or pass model_path argument."
            }

        # Check if binary exists
        binary_path = shutil.which(self.lit_binary)
        # If it's a direct path (e.g. ./lit), shutil.which might return None if not in PATH, so check explicitly
        if not binary_path and os.path.exists(self.lit_binary):
            binary_path = self.lit_binary

        if not binary_path:
             return {
                 "status": "error",
                 "message": f"LiteRT binary '{self.lit_binary}' not found. Please set LIT_BINARY_PATH or install LiteRT-LM."
             }

        # Construct command
        cmd = [binary_path]
        cmd.extend(["--backend", backend])
        cmd.extend(["--model_path", model_path])

        # Multimodal Handling
        # The current 'lit' CLI wrapper does not support verified multimodal input flags.
        # We restrict to text-only to avoid speculative errors.
        if image_path or audio_path:
            return {
                "status": "error",
                "message": "Multimodal input (image/audio) is not yet supported via the 'lit' CLI wrapper. Please use the LiteRT-LM C++ or Python API directly, or update this server implementation once CLI flags are verified."
            }

        cmd.extend(["--input_prompt", prompt])

        LOGGER.info(f"Executing command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if process.returncode != 0:
                return {
                    "status": "error",
                    "code": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "message": "LiteRT-LM execution failed."
                }

            return {
                "status": "success",
                "output": stdout_str,
                "debug_stderr": stderr_str
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

async def main():
    server = MCPServer()
    LOGGER.info("LiteRT-LM MCP Server running on stdio...")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer = None
    if sys.platform != "win32":
        try:
            w_transport, w_protocol = await asyncio.get_event_loop().connect_write_pipe(
                asyncio.Protocol, sys.stdout
            )
            writer = asyncio.StreamWriter(w_transport, w_protocol, None, asyncio.get_event_loop())
        except Exception as e:
            LOGGER.warning(f"Could not connect write pipe to stdout: {e}. Falling back to sys.stdout.write().")
            writer = None
    else:
        # Windows fallback:
        # On Windows, connecting a pipe to stdout using asyncio can be problematic with the default loop.
        # We fall back to standard print() which works for basic JSON-RPC over stdio.
        LOGGER.info("Windows detected: Using print() fallback for stdout.")
        writer = None

    while True:
        try:
            line = await reader.readline()
            if not line:
                break

            try:
                request = json.loads(line)
                response = await server.handle_request(request)

                if response:
                    response_str = json.dumps(response) + "\n"
                    if writer:
                        writer.write(response_str.encode())
                        try:
                            await writer.drain()
                        except (AttributeError, BrokenPipeError) as e:
                            LOGGER.warning(f"Error draining writer: {e}. Switching to print fallback.")
                            writer = None
                            print(response_str, flush=True)
                    else:
                        sys.stdout.write(response_str)
                        sys.stdout.flush()

            except json.JSONDecodeError:
                LOGGER.error(f"Invalid JSON received: {line}")
        except Exception as e:
            LOGGER.error(f"Loop error: {e}")
            break

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
