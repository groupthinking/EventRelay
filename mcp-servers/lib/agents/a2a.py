# Unified A2A (Agent-to-Agent) Framework
# Enables autonomous agents to negotiate, collaborate, and share context with MCP integration

import asyncio
import json
import logging
import sys
import os
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

# Ensure the lib directory is in sys.path FIRST before any relative imports
_lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _lib_dir)

# Clear any cached connectors module to avoid conflicts
if "connectors" in sys.modules:
    del sys.modules["connectors"]
if "connectors.real_mcp_client" in sys.modules:
    del sys.modules["connectors.real_mcp_client"]
if "connectors.mcp_base" in sys.modules:
    del sys.modules["connectors.mcp_base"]

# Internal imports (relative within the connectors folder)
from connectors.mcp_base import MCPContext
from connectors.real_mcp_client import MCPClient, execute_mcp_tool

logger = logging.getLogger(__name__)

# --- Protocols & Enums ---


class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TransportStrategy(Enum):
    ZERO_COPY = "zero_copy"
    SHARED_MEMORY = "shared_memory"
    MCP_PIPE = "mcp_pipe"
    STANDARD = "standard"


# --- Message Models ---


class A2AMessage:
    """Standard message format for agent communication"""

    def __init__(
        self,
        sender: str,
        recipient: str,
        message_type: str,
        content: Dict,
        conversation_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.recipient = recipient
        self.message_type = message_type
        self.content = content
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "content": self.content,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "A2AMessage":
        msg = cls(
            sender=data["sender"],
            recipient=data["recipient"],
            message_type=data["message_type"],
            content=data["content"],
            conversation_id=data.get("conversation_id"),
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        return msg


@dataclass
class A2AMCPMessage:
    """Enhanced message that combines A2A protocol with MCP context"""

    a2a_message: A2AMessage
    mcp_context: MCPContext
    priority: MessagePriority = MessagePriority.NORMAL
    transport_strategy: TransportStrategy = TransportStrategy.STANDARD
    deadline_ms: Optional[float] = None
    performance_requirements: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "a2a": self.a2a_message.to_dict(),
            "mcp": self.mcp_context.to_dict(),
            "transport": {
                "priority": self.priority.value,
                "strategy": self.transport_strategy.value,
                "deadline_ms": self.deadline_ms,
                "requirements": self.performance_requirements,
            },
        }


# --- Base Agent ---


class BaseAgent(ABC):
    """Base class for all agents with A2A capabilities"""

    def __init__(self, agent_id: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.conversations: dict[str, list] = {}
        self.message_handlers: dict[str, Callable] = {}
        self.state: dict[str, Any] = {}

    @abstractmethod
    async def process_intent(self, intent: Dict) -> Dict:
        """Process an intent and return result"""

    async def send_message(
        self, recipient: str, message_type: str, content: Dict
    ) -> A2AMessage:
        msg = A2AMessage(
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            content=content,
        )
        await message_bus.send(msg)
        return msg

    async def receive_message(self, message: A2AMessage):
        if message.conversation_id not in self.conversations:
            self.conversations[message.conversation_id] = []
        self.conversations[message.conversation_id].append(message)
        handler = self.message_handlers.get(message.message_type)
        if handler:
            response = await handler(message)
            if response:
                await self.send_message(
                    recipient=message.sender,
                    message_type=f"{message.message_type}_response",
                    content=response,
                )

    def register_handler(self, message_type: str, handler: Callable):
        self.message_handlers[message_type] = handler


# --- MCP Enabled Agent ---


class MCPEnabledA2AAgent(BaseAgent):
    """Enhanced agent with MCP context support"""

    def __init__(self, agent_id: str, capabilities: List[str]):
        super().__init__(agent_id, capabilities)
        self.mcp_context = MCPContext()
        self.message_bus: Optional["A2AMessageBus"] = None
        self.performance_stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "avg_response_time_ms": 0.0,
            "sla_violations": 0,
        }
        self.sla_requirements = {"max_latency_ms": 100}

        self.register_handler("context_share", self.handle_context_share)
        self.register_handler("tool_request", self.handle_tool_request)

    async def _execute_mcp_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await execute_mcp_tool(tool_name, params)

    async def handle_context_share(self, message: A2AMessage) -> Dict[str, Any]:
        incoming = message.content.get("context", {})
        if isinstance(incoming.get("task"), dict):
            self.mcp_context.task.update(incoming["task"])
        if isinstance(incoming.get("history"), list):
            self.mcp_context.history.extend(incoming["history"])
        return {"status": "context_merged"}

    async def handle_tool_request(self, message: A2AMessage) -> Dict[str, Any]:
        tool_name = message.content.get("tool")
        params = message.content.get("params", {})
        return await self._execute_mcp_tool(tool_name, params)


# --- Bus & Orchestration ---


class A2AMessageBus:
    def __init__(self):
        self.agents = {}
        self.message_queue = asyncio.Queue()
        self.running = False

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.agent_id] = agent

    async def send(self, message: A2AMessage):
        await self.message_queue.put(message)

    async def start(self):
        self.running = True
        while self.running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                recipient = self.agents.get(message.recipient)
                if recipient:
                    await recipient.receive_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Bus error: {e}")

    def stop(self):
        self.running = False


message_bus = A2AMessageBus()
