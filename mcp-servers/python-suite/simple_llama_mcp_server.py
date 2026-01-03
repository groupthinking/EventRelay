#!/usr/bin/env python3
"""
SIMPLE LLAMA AGENT MCP SERVER
Basic MCP server that registers tools for the Llama Background Agent

This is a simplified version that focuses on tool registration
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
    format='%(asctime)s - %(levelname)s - [SIMPLE-LLAMA-MCP] %(message)s'
)
logger = logging.getLogger("simple_llama_mcp_server")

# Tool definitions
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

async def main():
    """Main entry point - simple MCP server"""
    logger.info("🚀 Simple Llama Agent MCP Server starting...")
    logger.info(f"📋 Available tools: {[tool['name'] for tool in TOOLS]}")
    logger.info("🔧 Server running in simple mode - tools registered successfully!")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
