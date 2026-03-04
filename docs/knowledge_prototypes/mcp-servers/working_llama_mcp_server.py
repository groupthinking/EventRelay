#!/usr/bin/env python3
"""
WORKING LLAMA AGENT MCP SERVER
Proper MCP server that follows the MCP protocol for Cursor integration

This server implements the actual MCP protocol messages
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
# REMOVED: sys.path.insert with Path manipulation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [WORKING-LLAMA-MCP] %(message)s'
)
logger = logging.getLogger("working_llama_mcp_server")

# Tool definitions (static schema)
TOOLS = [
    {
        "name": "analyze_video_content",
        "description": "Analyze YouTube video content using Llama 3.1 8B",
        "inputSchema": {
            "type": "object",
            "properties": {
                "transcript": {"type": "string", "description": "Video transcript text"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "title": {"type": "string"},
                        "duration": {"type": "string"},
                        "upload_date": {"type": "string"}
                    },
                    "required": ["video_id"]
                }
            },
            "required": ["transcript", "metadata"]
        }
    },
    {
        "name": "assess_video_quality",
        "description": "Assess video quality and actionability",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of action items to assess"
                },
                "transcript": {"type": "string", "description": "Video transcript for context"}
            },
            "required": ["actions", "transcript"]
        }
    },
    {
        "name": "generate_implementation_plan",
        "description": "Generate detailed implementation plan from actions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_items": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of action items"
                },
                "video_id": {"type": "string", "description": "Video ID for context"}
            },
            "required": ["action_items", "video_id"]
        }
    },
    {
        "name": "extract_learning_insights",
        "description": "Extract learning insights from processed video",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_result": {"type": "object", "description": "Video analysis result"},
                "transcript": {"type": "string", "description": "Video transcript"}
            },
            "required": ["analysis_result", "transcript"]
        }
    },
    {
        "name": "get_agent_stats",
        "description": "Get Llama agent performance statistics",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    }
]

async def handle_mcp_message(message, agent):
    """Handle incoming MCP messages"""
    try:
        if message.get("method") == "tools/list":
            # Respond to tools/list request
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": TOOLS
                }
            }
            return response
            
        elif message.get("method") == "tools/call":
            # Handle tool calls
            tool_name = message.get("params", {}).get("name")
            arguments = message.get("params", {}).get("arguments", {})
            
            logger.info(f"Tool call: {tool_name}")

            # Route to real agent
            result = None
            if agent is None:
                raise RuntimeError("Agent not initialized")

            if tool_name == "analyze_video_content":
                transcript = arguments.get("transcript", "")
                metadata = arguments.get("metadata", {})
                analysis = await agent.analyze_video_content(transcript, metadata)
                result = {
                    "video_id": analysis.video_id,
                    "content_category": analysis.content_category,
                    "confidence_score": analysis.confidence_score,
                    "key_topics": analysis.key_topics,
                    "action_items": analysis.action_items,
                    "quality_score": analysis.quality_score,
                    "processing_time": analysis.processing_time,
                    "model_used": analysis.model_used,
                    "timestamp": analysis.timestamp,
                }
            elif tool_name == "assess_video_quality":
                actions = arguments.get("actions", [])
                transcript = arguments.get("transcript", "")
                # Build minimal analysis result wrapper
                from agents.llama_background_agent import VideoAnalysisResult
                analysis = VideoAnalysisResult(
                    video_id="mcp",
                    content_category="unknown",
                    confidence_score=0.0,
                    key_topics=[],
                    action_items=actions,
                    quality_score=0.0,
                    processing_time=0.0,
                    model_used="llama",
                    timestamp=""
                )
                score = await agent.assess_video_quality(analysis, transcript)
                result = {"quality_score": float(score)}
            elif tool_name == "generate_implementation_plan":
                action_items = arguments.get("action_items", [])
                video_id = arguments.get("video_id", "unknown")
                plan = await agent.generate_implementation_plan(action_items, video_id)
                result = plan
            elif tool_name == "extract_learning_insights":
                from agents.llama_background_agent import VideoAnalysisResult
                analysis_result = arguments.get("analysis_result", {})
                transcript = arguments.get("transcript", "")
                # Map dict -> dataclass (best-effort)
                analysis = VideoAnalysisResult(
                    video_id=analysis_result.get("video_id", "mcp"),
                    content_category=analysis_result.get("content_category", "unknown"),
                    confidence_score=analysis_result.get("confidence_score", 0.0),
                    key_topics=analysis_result.get("key_topics", []),
                    action_items=analysis_result.get("action_items", []),
                    quality_score=analysis_result.get("quality_score", 0.0),
                    processing_time=analysis_result.get("processing_time", 0.0),
                    model_used=analysis_result.get("model_used", "llama"),
                    timestamp=analysis_result.get("timestamp", "")
                )
                insights = await agent.learn_from_video(analysis, transcript)
                result = {"insights": [i.__dict__ for i in insights]}
            elif tool_name == "get_agent_stats":
                stats = await agent.get_performance_stats()
                result = stats
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            }
            return response
            
        elif message.get("method") == "initialize":
            # Handle initialization
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "llama-background-agent",
                        "version": "1.0.0"
                    }
                }
            }
            return response
            
        else:
            logger.warning(f"Unknown method: {message.get('method')}")
            return None
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -1,
                "message": str(e)
            }
        }
        return error_response

async def main():
    """Main MCP server loop"""
    logger.info("🚀 Working Llama Agent MCP Server starting...")
    logger.info(f"📋 Available tools: {[tool['name'] for tool in TOOLS]}")
    logger.info("🔧 Server implementing MCP protocol for Cursor integration")
    
    # Initialize agent once
    agent = None
    try:
        from agents.llama_background_agent import LlamaBackgroundAgent
        agent = LlamaBackgroundAgent()
        await agent.initialize()
        logger.info("✅ Llama Background Agent ready in MCP server")
    except Exception as e:
        logger.error(f"Failed to initialize Llama agent in MCP server: {e}")
    
    # Read from stdin, write to stdout (MCP stdio protocol)
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    # Set up stdin/stdout
    stdin_transport, _ = await asyncio.get_event_loop().connect_read_pipe(
        lambda: protocol, sys.stdin
    )
    
    try:
        while True:
            # Read line from stdin
            line = await reader.readline()
            if not line:
                break
                
            try:
                # Parse JSON message
                message = json.loads(line.decode().strip())
                logger.debug(f"Received: {message}")
                
                # Handle message and send response
                response = await handle_mcp_message(message, agent)
                if response:
                    response_json = json.dumps(response) + "\n"
                    sys.stdout.write(response_json)
                    sys.stdout.flush()
                    logger.debug(f"Sent: {response}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        stdin_transport.close()

if __name__ == "__main__":
    asyncio.run(main())
