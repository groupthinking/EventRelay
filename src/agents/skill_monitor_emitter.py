#!/usr/bin/env python3
"""
Skill Monitor Event Emitter - Send pipeline events to Claude Skill Monitor
Lightweight WebSocket client for real-time observability
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("websockets not installed - skill monitor integration disabled")

logger = logging.getLogger(__name__)

class SkillMonitorEmitter:
    """
    Emits pipeline events to Claude Skill Monitor via WebSocket.
    Falls back gracefully if monitor unavailable.
    """

    def __init__(self, monitor_url: str = "ws://localhost:3000"):
        self.monitor_url = monitor_url
        self.ws = None
        self.enabled = WEBSOCKETS_AVAILABLE
        self.failed_connection = False

    async def connect(self):
        """Establish WebSocket connection"""
        if not self.enabled or self.failed_connection:
            return

        try:
            self.ws = await websockets.connect(self.monitor_url, open_timeout=2)
            logger.info(f"Connected to Skill Monitor at {self.monitor_url}")
        except Exception as e:
            logger.debug(f"Skill Monitor not available: {e}")
            self.failed_connection = True
            self.ws = None

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        """Send event to monitor"""
        if not self.enabled or self.failed_connection:
            return

        if not self.ws:
            await self.connect()

        if not self.ws:
            return

        try:
            event = {
                "type": event_type,
                "payload": {
                    **payload,
                    "timestamp": datetime.now().isoformat(),
                    "source": "mcp-agent-network"
                }
            }
            await self.ws.send(json.dumps(event))
            logger.debug(f"Emitted {event_type} to Skill Monitor")

        except Exception as e:
            logger.debug(f"Failed to emit event: {e}")
            self.ws = None

    async def close(self):
        """Close connection"""
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

# Singleton emitter
_emitter = None

def get_emitter() -> SkillMonitorEmitter:
    """Get or create emitter singleton"""
    global _emitter
    if _emitter is None:
        _emitter = SkillMonitorEmitter()
    return _emitter
