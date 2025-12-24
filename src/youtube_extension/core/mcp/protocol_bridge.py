"""
MCP Protocol Bridge - Cross-Protocol Integration

This module provides the MCP protocol bridge system for integrating with
external AI services and protocols, enabling seamless communication across
different AI platforms and standards.

Key Responsibilities:
- Protocol translation and adaptation
- External service integration
- Request/response transformation
- Error handling and fallbacks
- Protocol capability negotiation
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Union, Callable
from abc import ABC, abstractmethod
from enum import Enum
import aiohttp

from pydantic import BaseModel, Field

from .context_manager import MCPContext, get_context_manager
from .server_registry import MCPServer, ServerCapability, get_server_registry

# Configure logging
logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """Supported Protocol Types"""
    MCP = "mcp"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_AI = "google_ai"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class BridgeStatus(Enum):
    """Protocol Bridge Status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ProtocolAdapter(ABC):
    """
    Abstract Protocol Adapter

    Defines the interface for protocol-specific adapters that handle
    communication with external AI services.
    """

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Protocol type this adapter handles"""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the protocol adapter"""
        pass

    @abstractmethod
    async def send_request(self, request: Dict[str, Any], context: MCPContext) -> Dict[str, Any]:
        """Send a request using this protocol"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the protocol connection is healthy"""
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[ServerCapability]:
        """Get capabilities supported by this protocol"""
        pass


class MCPProtocolBridge:
    """
    MCP Protocol Bridge - Central protocol integration hub

    Manages protocol adapters and provides unified interface for
    communicating with external AI services through different protocols.
    """

    def __init__(self):
        """Initialize the MCP Protocol Bridge"""
        self.adapters: Dict[ProtocolType, ProtocolAdapter] = {}
        self.bridge_status: Dict[ProtocolType, BridgeStatus] = {}
        self.request_handlers: Dict[str, Callable] = {}

        # Register built-in protocol handlers
        self._register_builtin_handlers()

        logger.info("MCP Protocol Bridge initialized")

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        """
        Register a protocol adapter

        Args:
            adapter: Protocol adapter instance
        """
        protocol_type = adapter.protocol_type
        self.adapters[protocol_type] = adapter
        self.bridge_status[protocol_type] = BridgeStatus.DISCONNECTED

        logger.info(f"Registered protocol adapter: {protocol_type.value}")

    async def initialize_adapter(self, protocol_type: ProtocolType, config: Dict[str, Any]) -> bool:
        """
        Initialize a protocol adapter

        Args:
            protocol_type: Protocol to initialize
            config: Configuration for the adapter

        Returns:
            True if initialization successful, False otherwise
        """
        if protocol_type not in self.adapters:
            logger.error(f"No adapter registered for protocol: {protocol_type.value}")
            return False

        try:
            success = await self.adapters[protocol_type].initialize(config)
            if success:
                self.bridge_status[protocol_type] = BridgeStatus.CONNECTED
                logger.info(f"Initialized protocol adapter: {protocol_type.value}")
            else:
                self.bridge_status[protocol_type] = BridgeStatus.ERROR
                logger.error(f"Failed to initialize protocol adapter: {protocol_type.value}")
            return success

        except Exception as e:
            self.bridge_status[protocol_type] = BridgeStatus.ERROR
            logger.error(f"Error initializing protocol adapter {protocol_type.value}: {e}")
            return False

    async def send_protocol_request(
        self,
        protocol_type: ProtocolType,
        request: Dict[str, Any],
        context: Optional[MCPContext] = None
    ) -> Dict[str, Any]:
        """
        Send a request through a specific protocol

        Args:
            protocol_type: Target protocol
            request: Request data
            context: Optional MCP context

        Returns:
            Response from the protocol
        """
        if protocol_type not in self.adapters:
            raise ValueError(f"No adapter registered for protocol: {protocol_type.value}")

        if self.bridge_status.get(protocol_type) != BridgeStatus.CONNECTED:
            raise RuntimeError(f"Protocol {protocol_type.value} is not connected")

        # Create context if not provided
        if context is None:
            context_manager = get_context_manager()
            context = context_manager.create_context(
                user="system",
                task="protocol_bridge_request",
                intent=f"Send {protocol_type.value} protocol request"
            )

        try:
            # Add protocol metadata to context
            context.metadata["protocol"] = protocol_type.value
            context.metadata["request_timestamp"] = datetime.utcnow().isoformat()

            # Send request through adapter
            response = await self.adapters[protocol_type].send_request(request, context)

            # Update context with response
            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request": request,
                "response": response,
                "success": True
            })

            return response

        except Exception as e:
            # Update context with error
            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request": request,
                "error": str(e),
                "success": False
            })

            logger.error(f"Protocol request failed for {protocol_type.value}: {e}")
            raise

    async def route_request(
        self,
        request: Dict[str, Any],
        preferred_protocols: Optional[List[ProtocolType]] = None,
        context: Optional[MCPContext] = None
    ) -> Dict[str, Any]:
        """
        Route a request to the best available protocol

        Args:
            request: Request data
            preferred_protocols: Optional list of preferred protocols
            context: Optional MCP context

        Returns:
            Response from the selected protocol
        """
        # Determine available protocols
        available_protocols = [
            protocol for protocol, status in self.bridge_status.items()
            if status == BridgeStatus.CONNECTED
        ]

        if not available_protocols:
            raise RuntimeError("No connected protocol adapters available")

        # Use preferred protocols if specified, otherwise use all available
        candidate_protocols = preferred_protocols or available_protocols

        # Filter to only available protocols
        candidate_protocols = [p for p in candidate_protocols if p in available_protocols]

        if not candidate_protocols:
            raise RuntimeError("No matching connected protocol adapters available")

        # For now, use the first available protocol
        # TODO: Implement intelligent routing based on capabilities, load, etc.
        selected_protocol = candidate_protocols[0]

        logger.info(f"Routing request to protocol: {selected_protocol.value}")

        return await self.send_protocol_request(selected_protocol, request, context)

    async def health_check_all(self) -> Dict[ProtocolType, bool]:
        """
        Check health of all protocol adapters

        Returns:
            Dictionary mapping protocols to health status
        """
        results = {}

        for protocol_type, adapter in self.adapters.items():
            try:
                is_healthy = await adapter.health_check()
                results[protocol_type] = is_healthy

                # Update bridge status
                if is_healthy:
                    self.bridge_status[protocol_type] = BridgeStatus.CONNECTED
                else:
                    self.bridge_status[protocol_type] = BridgeStatus.ERROR

            except Exception as e:
                logger.error(f"Health check failed for {protocol_type.value}: {e}")
                results[protocol_type] = False
                self.bridge_status[protocol_type] = BridgeStatus.ERROR

        return results

    def get_bridge_status(self) -> Dict[ProtocolType, BridgeStatus]:
        """
        Get the status of all protocol bridges

        Returns:
            Dictionary mapping protocols to bridge status
        """
        return self.bridge_status.copy()

    def get_available_protocols(self) -> List[ProtocolType]:
        """
        Get list of available protocol types

        Returns:
            List of protocol types with connected adapters
        """
        return [
            protocol for protocol, status in self.bridge_status.items()
            if status == BridgeStatus.CONNECTED
        ]

    def register_request_handler(self, request_type: str, handler: Callable) -> None:
        """
        Register a custom request handler

        Args:
            request_type: Type of request this handler processes
            handler: Handler function
        """
        self.request_handlers[request_type] = handler
        logger.info(f"Registered request handler for type: {request_type}")

    def _register_builtin_handlers(self) -> None:
        """Register built-in protocol request handlers"""
        # These will be implemented as needed
        pass


# Built-in Protocol Adapters

class OpenAIAdapter(ProtocolAdapter):
    """OpenAI API Protocol Adapter"""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.OPENAI

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize OpenAI adapter"""
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4")

        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return False

        return True

    async def send_request(self, request: Dict[str, Any], context: MCPContext) -> Dict[str, Any]:
        """Send request to OpenAI API"""
        # Implementation would go here
        # This is a placeholder for the actual OpenAI API integration
        return {
            "protocol": "openai",
            "response": "OpenAI response placeholder",
            "context_id": context.id
        }

    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        # Implementation would check API availability
        return True

    async def get_capabilities(self) -> List[ServerCapability]:
        """Get OpenAI capabilities"""
        return [ServerCapability.AI_INFERENCE]


class AnthropicAdapter(ProtocolAdapter):
    """Anthropic Claude API Protocol Adapter"""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.ANTHROPIC

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Anthropic adapter"""
        self.api_key = config.get("api_key")
        self.model = config.get("model", "claude-3-sonnet-20240229")

        if not self.api_key:
            logger.error("Anthropic API key not provided")
            return False

        return True

    async def send_request(self, request: Dict[str, Any], context: MCPContext) -> Dict[str, Any]:
        """Send request to Anthropic API"""
        # Implementation would go here
        return {
            "protocol": "anthropic",
            "response": "Anthropic response placeholder",
            "context_id": context.id
        }

    async def health_check(self) -> bool:
        """Check Anthropic API health"""
        return True

    async def get_capabilities(self) -> List[ServerCapability]:
        """Get Anthropic capabilities"""
        return [ServerCapability.AI_INFERENCE]


class GoogleAIAdapter(ProtocolAdapter):
    """Google AI (Gemini) Protocol Adapter"""

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.GOOGLE_AI

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Google AI adapter"""
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gemini-pro")

        if not self.api_key:
            logger.error("Google AI API key not provided")
            return False

        return True

    async def send_request(self, request: Dict[str, Any], context: MCPContext) -> Dict[str, Any]:
        """Send request to Google AI API"""
        # Implementation would go here
        return {
            "protocol": "google_ai",
            "response": "Google AI response placeholder",
            "context_id": context.id
        }

    async def health_check(self) -> bool:
        """Check Google AI API health"""
        return True

    async def get_capabilities(self) -> List[ServerCapability]:
        """Get Google AI capabilities"""
        return [ServerCapability.AI_INFERENCE]


# Global protocol bridge instance
_protocol_bridge = None


def get_protocol_bridge() -> MCPProtocolBridge:
    """Get the global MCP protocol bridge instance"""
    global _protocol_bridge
    if _protocol_bridge is None:
        _protocol_bridge = MCPProtocolBridge()

        # Register built-in adapters
        _protocol_bridge.register_adapter(OpenAIAdapter())
        _protocol_bridge.register_adapter(AnthropicAdapter())
        _protocol_bridge.register_adapter(GoogleAIAdapter())

    return _protocol_bridge


async def send_ai_request(
    request: Dict[str, Any],
    protocol: Optional[ProtocolType] = None,
    context: Optional[MCPContext] = None
) -> Dict[str, Any]:
    """Convenience function to send AI request through protocol bridge"""
    bridge = get_protocol_bridge()

    if protocol:
        return await bridge.send_protocol_request(protocol, request, context)
    else:
        return await bridge.route_request(request, None, context)
