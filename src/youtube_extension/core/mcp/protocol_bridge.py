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
import ipaddress
import logging
import os
import socket
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from .context_manager import MCPContext, get_context_manager
from .server_registry import ServerCapability

# Optional SDK imports — each is silently skipped when not installed
try:
    import openai

    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

try:
    import anthropic

    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    from google import genai
    from google.genai import types as genai_types

    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False

# Configure logging
logger = logging.getLogger(__name__)


def _summarize_payload(payload: Any) -> dict[str, Any]:
    """Build a non-sensitive structural summary for history/logging."""
    if isinstance(payload, Mapping):
        keys = sorted(str(k) for k in payload.keys())
        return {"type": type(payload).__name__, "keys": keys, "key_count": len(keys)}
    return {"type": type(payload).__name__}


def _sanitize_exception(exc: Exception) -> dict[str, str]:
    """Return non-sensitive exception metadata safe to persist."""
    return {"type": type(exc).__name__}


def _is_public_https_base_url(base_url: str) -> bool:
    """Return True when the URL targets a publicly routable HTTPS endpoint."""
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False

    host = parsed.hostname
    if not host:
        return False

    try:
        ip = ipaddress.ip_address(host)
        return ip.is_global
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    if not resolved:
        return False

    for family, _, _, _, sockaddr in resolved:
        address = sockaddr[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if family not in (socket.AF_INET, socket.AF_INET6) or not ip.is_global:
            return False

    return True


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
    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize the protocol adapter"""
        pass

    @abstractmethod
    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        """Send a request using this protocol"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the protocol connection is healthy"""
        pass

    @abstractmethod
    async def get_capabilities(self) -> list[ServerCapability]:
        """Get capabilities supported by this protocol"""
        pass


class MCPProtocolBridge:
    """
    MCP Protocol Bridge - Central protocol integration hub

    Manages protocol adapters and provides unified interface for
    communicating with external AI services through different protocols.
    """

    def __init__(self) -> None:
        """Initialize the MCP Protocol Bridge"""
        self.adapters: dict[ProtocolType, ProtocolAdapter] = {}
        self.bridge_status: dict[ProtocolType, BridgeStatus] = {}
        self.request_handlers: dict[str, Callable] = {}
        self.protocol_stats: dict[ProtocolType, dict[str, int]] = {}

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

    async def initialize_adapter(self, protocol_type: ProtocolType, config: dict[str, Any]) -> bool:
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
        request: dict[str, Any],
        context: Optional[MCPContext] = None
    ) -> dict[str, Any]:
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

        if context is None:
            context_manager = get_context_manager()
            context = context_manager.create_context(
                user="system",
                task="protocol_bridge_request",
                intent=f"Send {protocol_type.value} protocol request"
            )

        stats = self.protocol_stats.setdefault(
            protocol_type, {"in_flight": 0, "success": 0, "failure": 0}
        )
        for counter in ("in_flight", "success", "failure"):
            stats.setdefault(counter, 0)
        stats["in_flight"] += 1

        try:
            context.metadata["protocol"] = protocol_type.value
            context.metadata["request_timestamp"] = datetime.now(timezone.utc).isoformat()

            response = await self.adapters[protocol_type].send_request(request, context)

            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request_summary": _summarize_payload(request),
                "response_summary": _summarize_payload(response),
                "success": True,
            })

            stats["success"] += 1
            return response

        except Exception as e:
            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request_summary": _summarize_payload(request),
                "error": _sanitize_exception(e),
                "success": False,
            })

            stats["failure"] += 1
            logger.error(
                "Protocol request failed for %s with %s",
                protocol_type.value,
                type(e).__name__,
            )
            raise

        finally:
            stats["in_flight"] -= 1

    async def route_request(
        self,
        request: dict[str, Any],
        preferred_protocols: Optional[list[ProtocolType]] = None,
        context: Optional[MCPContext] = None
    ) -> dict[str, Any]:
        """
        Route a request to the best available protocol

        Candidates are filtered by the capabilities listed in
        request["required_capabilities"] (if present), then the least-loaded
        protocol is selected, with error rate and preference order as
        tiebreakers.
        """
        available_protocols = [
            protocol for protocol, status in self.bridge_status.items()
            if status == BridgeStatus.CONNECTED
        ]

        if not available_protocols:
            raise RuntimeError("No connected protocol adapters available")

        candidate_protocols = preferred_protocols or available_protocols
        candidate_protocols = [p for p in candidate_protocols if p in available_protocols]

        if not candidate_protocols:
            raise RuntimeError("No matching connected protocol adapters available")

        selected_protocol = await self._select_protocol(candidate_protocols, request)
        logger.info(f"Routing request to protocol: {selected_protocol.value}")
        return await self.send_protocol_request(selected_protocol, request, context)

    async def _select_protocol(
        self,
        candidates: list[ProtocolType],
        request: dict[str, Any]
    ) -> ProtocolType:
        raw_capabilities = request.get("required_capabilities", [])
        if isinstance(raw_capabilities, (str, bytes)) or not isinstance(
            raw_capabilities, (list, tuple, set, frozenset)
        ):
            raise TypeError(
                "'required_capabilities' must be a list/tuple/set of "
                f"ServerCapability or str, got {type(raw_capabilities).__name__}"
            )

        required_capabilities: set[ServerCapability] = set()
        for capability in raw_capabilities:
            if isinstance(capability, ServerCapability):
                required_capabilities.add(capability)
                continue
            try:
                required_capabilities.add(ServerCapability(capability))
            except ValueError as exc:
                valid = [c.value for c in ServerCapability]
                raise ValueError(
                    f"Unknown capability {capability!r}. Valid values: {valid}"
                ) from exc

        if required_capabilities:
            capable_protocols = []
            for protocol in candidates:
                try:
                    capabilities = set(await self.adapters[protocol].get_capabilities())
                except Exception as e:
                    logger.warning(f"Could not get capabilities for {protocol.value}: {e}")
                    continue
                if required_capabilities <= capabilities:
                    capable_protocols.append(protocol)

            if not capable_protocols:
                required_names = sorted(c.value for c in required_capabilities)
                logger.error(
                    "No connected protocol adapter supports required "
                    f"capabilities: {required_names}"
                )
                raise RuntimeError(
                    "No connected protocol adapter supports the required capabilities"
                )

            candidates = capable_protocols

        def routing_score(item: tuple[int, ProtocolType]) -> tuple[int, float, int]:
            preference_index, protocol = item
            stats = self.protocol_stats.get(protocol, {})
            completed = stats.get("success", 0) + stats.get("failure", 0)
            error_rate = stats.get("failure", 0) / completed if completed else 0.0
            return (stats.get("in_flight", 0), error_rate, preference_index)

        return min(enumerate(candidates), key=routing_score)[1]

    async def health_check_all(self) -> dict[ProtocolType, bool]:
        results = {}

        for protocol_type, adapter in self.adapters.items():
            try:
                is_healthy = await adapter.health_check()
                results[protocol_type] = is_healthy
                if is_healthy:
                    self.bridge_status[protocol_type] = BridgeStatus.CONNECTED
                else:
                    self.bridge_status[protocol_type] = BridgeStatus.ERROR
            except Exception as e:
                logger.error(f"Health check failed for {protocol_type.value}: {e}")
                results[protocol_type] = False
                self.bridge_status[protocol_type] = BridgeStatus.ERROR

        return results

    def get_bridge_status(self) -> dict[ProtocolType, BridgeStatus]:
        return self.bridge_status.copy()

    def get_available_protocols(self) -> list[ProtocolType]:
        return [
            protocol for protocol, status in self.bridge_status.items()
            if status == BridgeStatus.CONNECTED
        ]

    def register_request_handler(self, request_type: str, handler: Callable) -> None:
        self.request_handlers[request_type] = handler
        logger.info(f"Registered request handler for type: {request_type}")

    def _register_builtin_handlers(self) -> None:
        pass


class OpenAIAdapter(ProtocolAdapter):
    """OpenAI API Protocol Adapter"""

    _DEFAULT_TIMEOUT = 60

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.base_url: str = "https://api.openai.com/v1"
        self.model: str = "gpt-4"
        self._client: Any = None

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.OPENAI

    async def initialize(self, config: dict[str, Any]) -> bool:
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4")

        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return False

        if not isinstance(base_url, str):
            logger.error(
                "Unsafe OpenAI base_url rejected (must be a string, got %s)",
                type(base_url).__name__,
            )
            return False
        if not _is_public_https_base_url(base_url):
            logger.error(
                "Unsafe OpenAI base_url rejected (must be HTTPS and publicly routable)"
            )
            return False
        self.base_url = base_url

        if not _HAS_OPENAI:
            logger.error("openai package is not installed")
            return False

        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self._DEFAULT_TIMEOUT,
        )
        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("OpenAI adapter not initialized — call initialize() first")

        messages = request.get("messages") or [
            {"role": "user", "content": request.get("prompt", "")}
        ]
        model = request.get("model", self.model)
        max_tokens = request.get("max_tokens", 4096)
        temperature = request.get("temperature", 1.0)

        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        return {
            "protocol": "openai",
            "model": response.model,
            "content": choice.message.content,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            "context_id": context.id,
        }

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.models.retrieve(self.model)
            return True
        except Exception as e:
            logger.warning("OpenAI health check failed: %s", e)
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
        return [ServerCapability.AI_INFERENCE]


class AnthropicAdapter(ProtocolAdapter):
    """Anthropic Claude API Protocol Adapter"""

    _DEFAULT_TIMEOUT = 120

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.model: str = "claude-opus-4-8"
        self._client: Any = None

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.ANTHROPIC

    async def initialize(self, config: dict[str, Any]) -> bool:
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = config.get("model", "claude-opus-4-8")

        if not self.api_key:
            logger.error("Anthropic API key not provided")
            return False

        if not _HAS_ANTHROPIC:
            logger.error("anthropic package is not installed")
            return False

        self._client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            timeout=self._DEFAULT_TIMEOUT,
        )
        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Anthropic adapter not initialized — call initialize() first")

        messages = request.get("messages") or [
            {"role": "user", "content": request.get("prompt", "")}
        ]
        model = request.get("model", self.model)
        max_tokens = request.get("max_tokens", 8192)

        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            messages=messages,
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        content = "\n".join(text_blocks) if text_blocks else None

        return {
            "protocol": "anthropic",
            "model": response.model,
            "content": content,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "context_id": context.id,
        }

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.warning("Anthropic health check failed: %s", e)
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
        return [ServerCapability.AI_INFERENCE]


class GoogleAIAdapter(ProtocolAdapter):
    """Google AI (Gemini) Protocol Adapter"""

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.model: str = "gemini-pro"
        self._client: Any = None

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.GOOGLE_AI

    async def initialize(self, config: dict[str, Any]) -> bool:
        self.api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
        self.model = config.get("model", "gemini-pro")

        if not self.api_key:
            logger.error("Google AI API key not provided")
            return False

        if not _HAS_GENAI:
            logger.error("google-genai package is not installed")
            return False

        self._client = genai.Client(api_key=self.api_key)
        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Google AI adapter not initialized — call initialize() first")

        prompt = request.get("prompt", "")
        if request.get("messages"):
            parts = []
            for msg in request["messages"]:
                content = msg.get("content", "")
                parts.append(content)
            prompt = "\n".join(parts)

        model = request.get("model", self.model)
        max_tokens = request.get("max_tokens")
        temperature = request.get("temperature")

        config_kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            config_kwargs["max_output_tokens"] = max_tokens
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        config = genai_types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        generate_kwargs: dict[str, Any] = {
            "model": model,
            "contents": prompt,
        }
        if config is not None:
            generate_kwargs["config"] = config

        response = await asyncio.to_thread(
            self._client.models.generate_content, **generate_kwargs
        )

        text = response.text
        if text is None and response.candidates:
            parts = response.candidates[0].content.parts
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
            text = "\n".join(text_parts) if text_parts else None

        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", None),
            }

        return {
            "protocol": "google_ai",
            "model": model,
            "content": text,
            "usage": usage,
            "context_id": context.id,
        }

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            await asyncio.to_thread(self._client.models.list)
            return True
        except Exception as e:
            logger.warning("Google AI health check failed: %s", e)
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
        return [ServerCapability.AI_INFERENCE]


_protocol_bridge = None


def get_protocol_bridge() -> MCPProtocolBridge:
    global _protocol_bridge
    if _protocol_bridge is None:
        _protocol_bridge = MCPProtocolBridge()
        _protocol_bridge.register_adapter(OpenAIAdapter())
        _protocol_bridge.register_adapter(AnthropicAdapter())
        _protocol_bridge.register_adapter(GoogleAIAdapter())
    return _protocol_bridge


async def send_ai_request(
    request: dict[str, Any],
    protocol: Optional[ProtocolType] = None,
    context: Optional[MCPContext] = None
) -> dict[str, Any]:
    bridge = get_protocol_bridge()

    if protocol:
        return await bridge.send_protocol_request(protocol, request, context)
    return await bridge.route_request(request, None, context)
