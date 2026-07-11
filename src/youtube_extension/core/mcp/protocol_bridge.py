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
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import httpx

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


def _summarize_request(request: dict[str, Any]) -> dict[str, Any]:
    """Build a non-sensitive summary of a request for history/logging.

    The raw request may carry API keys, tokens, prompts, or PII. Persisting it
    verbatim would leak those into context history (which is serialized and
    logged), so we record only structural metadata, never values.
    """
    try:
        keys = sorted(str(k) for k in request.keys())
    except AttributeError:
        keys = []
    return {"keys": keys, "key_count": len(keys)}


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

        # Create context if not provided
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
        # Ensure every counter exists before incrementing so a pre-existing
        # partial stats dict (from a caller or future refactor) can't raise
        # KeyError and leave the counters in an inconsistent state.
        for _counter in ("in_flight", "success", "failure"):
            stats.setdefault(_counter, 0)
        stats["in_flight"] += 1

        try:
            # Add protocol metadata to context
            context.metadata["protocol"] = protocol_type.value
            context.metadata["request_timestamp"] = datetime.now(timezone.utc).isoformat()

            # Send request through adapter
            response = await self.adapters[protocol_type].send_request(request, context)

            # Update context with response. Store only a non-sensitive summary of
            # the request — the raw dict may contain API keys/tokens/PII.
            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request_summary": _summarize_request(request),
                "response": response,
                "success": True
            })

            stats["success"] += 1
            return response

        except Exception as e:
            # Update context with error
            context.add_history_entry("protocol_request", {
                "protocol": protocol_type.value,
                "request_summary": _summarize_request(request),
                "error": str(e),
                "success": False
            })

            stats["failure"] += 1
            logger.error(f"Protocol request failed for {protocol_type.value}: {e}")
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

        selected_protocol = await self._select_protocol(candidate_protocols, request)

        logger.info(f"Routing request to protocol: {selected_protocol.value}")

        return await self.send_protocol_request(selected_protocol, request, context)

    async def _select_protocol(
        self,
        candidates: list[ProtocolType],
        request: dict[str, Any]
    ) -> ProtocolType:
        """
        Select the best protocol from connected candidates

        Filters candidates to those whose adapters support every capability in
        request["required_capabilities"], then picks the candidate with the
        fewest in-flight requests, breaking ties by lowest historical error
        rate and finally by candidate order (preference order).

        Args:
            candidates: Connected protocols to choose from, in preference order
            request: Request data, optionally containing "required_capabilities"

        Returns:
            The selected protocol

        Raises:
            TypeError: If "required_capabilities" is not a list/tuple/set
            ValueError: If a capability string is not a known ServerCapability
            RuntimeError: If no candidate supports the required capabilities
        """
        raw_capabilities = request.get("required_capabilities", [])
        # A bare string is iterable: without this guard the loop below would
        # iterate over its characters, raising a confusing cascade of
        # ValueErrors. Reject non-collection inputs up front.
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
                # Log specifics internally for debugging, but keep the raised
                # message generic so it doesn't disclose which capabilities the
                # system knows about if it propagates to an API response.
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

    def get_bridge_status(self) -> dict[ProtocolType, BridgeStatus]:
        """
        Get the status of all protocol bridges

        Returns:
            Dictionary mapping protocols to bridge status
        """
        return self.bridge_status.copy()

    def get_available_protocols(self) -> list[ProtocolType]:
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
        """Initialize OpenAI adapter"""
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4")

        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return False

        # base_url may arrive as a non-string (e.g. an explicit None in config);
        # urlparse would raise TypeError on such input, so reject it up front.
        if not isinstance(base_url, str):
            logger.error(
                "Unsafe OpenAI base_url rejected (must be a string, got %s)",
                type(base_url).__name__,
            )
            return False

        # Reject non-HTTPS or hostless base URLs. An attacker-influenced config
        # could otherwise point requests at internal targets such as the cloud
        # metadata endpoint (http://169.254.169.254) or file:// URIs (SSRF).
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            logger.error("Unsafe OpenAI base_url rejected (must be HTTPS with a host)")
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
<<<<<<< HEAD
        """Send request to OpenAI API."""
        if not getattr(self, "api_key", None):
            return {
                "protocol": "openai",
                "success": False,
                "error": "OpenAI adapter not initialized (no API key)",
                "context_id": context.id,
            }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": getattr(self, "model", "gpt-4"),
                    "messages": request.get("messages", [{"role": "user", "content": request.get("prompt", "")}]),
                    "temperature": request.get("temperature", 0.7),
                    "max_tokens": request.get("max_tokens", 4000),
                }
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "protocol": "openai",
                    "success": True,
                    "response": data["choices"][0]["message"]["content"],
                    "context_id": context.id,
                    "usage": data.get("usage"),
                }
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return {
                "protocol": "openai",
                "success": False,
                "error": str(e),
                "context_id": context.id,
            }

    async def health_check(self) -> bool:
        """Check OpenAI API reachability."""
        if not getattr(self, "api_key", None):
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception:
=======
        """Send request to OpenAI API"""
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
        """Check OpenAI API health"""
        if self._client is None:
            return False
        try:
            await self._client.models.retrieve(self.model)
            return True
        except Exception as e:
            logger.warning("OpenAI health check failed: %s", e)
>>>>>>> origin/main
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
        """Get OpenAI capabilities"""
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
        """Initialize Anthropic adapter"""
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = config.get("model", "claude-opus-4-8")
        self.base_url = "https://api.anthropic.com"

        if not self.api_key:
            logger.error("Anthropic API key not provided")
            return False

<<<<<<< HEAD
        # Validate base_url if overridden
        base_url = config.get("base_url", self.base_url)
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            logger.error("Unsafe Anthropic base_url rejected (must be HTTPS with a host)")
            return False
        self.base_url = base_url

        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        """Send request to Anthropic API."""
        if not getattr(self, "api_key", None):
            return {
                "protocol": "anthropic",
                "success": False,
                "error": "Anthropic adapter not initialized (no API key)",
                "context_id": context.id,
            }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                messages = request.get("messages", [{"role": "user", "content": request.get("prompt", "")}])
                payload = {
                    "model": getattr(self, "model", "claude-opus-4-8"),
                    "max_tokens": request.get("max_tokens", 4000),
                    "messages": messages,
                }
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content = "".join(
                    block["text"] for block in data.get("content", []) if block.get("type") == "text"
                )
                return {
                    "protocol": "anthropic",
                    "success": True,
                    "response": content,
                    "context_id": context.id,
                    "usage": data.get("usage"),
                }
        except Exception as e:
            logger.error(f"Anthropic request failed: {e}")
            return {
                "protocol": "anthropic",
                "success": False,
                "error": str(e),
                "context_id": context.id,
            }

    async def health_check(self) -> bool:
        """Check Anthropic API reachability without consuming tokens."""
        if not getattr(self, "api_key", None):
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Send intentionally invalid payload (empty messages) to test
                # reachability without generating tokens. A 400 confirms the
                # API is reachable; only network errors indicate unavailability.
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={"model": self.model, "max_tokens": 1, "messages": []},
                )
                # 400 = reachable (invalid request rejected), 401 = bad key but reachable
                return resp.status_code in (200, 400, 401)
        except Exception:
=======
        if not _HAS_ANTHROPIC:
            logger.error("anthropic package is not installed")
            return False

        self._client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            timeout=self._DEFAULT_TIMEOUT,
        )
        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        """Send request to Anthropic API"""
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

        # Extract text content from response blocks
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
        """Check Anthropic API health"""
        if self._client is None:
            return False
        try:
            # Use a minimal count_tokens call as a lightweight health probe
            await self._client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.warning("Anthropic health check failed: %s", e)
>>>>>>> origin/main
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
        """Get Anthropic capabilities"""
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
        """Initialize Google AI adapter"""
        self.api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")
        self.model = config.get("model", "gemini-pro")
        self.base_url = "https://generativelanguage.googleapis.com"

        if not self.api_key:
            logger.error("Google AI API key not provided")
            return False

<<<<<<< HEAD
        # Validate base_url if overridden
        base_url = config.get("base_url", self.base_url)
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            logger.error("Unsafe Google AI base_url rejected (must be HTTPS with a host)")
            return False
        self.base_url = base_url

        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        """Send request to Google AI (Gemini) API."""
        if not getattr(self, "api_key", None):
            return {
                "protocol": "google_ai",
                "success": False,
                "error": "Google AI adapter not initialized (no API key)",
                "context_id": context.id,
            }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                model = request.get("model", getattr(self, "model", "gemini-pro"))
                prompt = request.get("prompt", "")
                url = f"{self.base_url}/v1beta/models/{model}:generateContent"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": request.get("temperature", 0.7),
                        "maxOutputTokens": request.get("max_tokens", 4000),
                    },
                }
                resp = await client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                content = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = "".join(p.get("text", "") for p in parts)
                return {
                    "protocol": "google_ai",
                    "success": True,
                    "response": content,
                    "context_id": context.id,
                    "usage": data.get("usageMetadata"),
                }
        except Exception as e:
            logger.error(f"Google AI request failed: {e}")
            return {
                "protocol": "google_ai",
                "success": False,
                "error": str(e),
                "context_id": context.id,
            }

    async def health_check(self) -> bool:
        """Check Google AI API reachability."""
        if not getattr(self, "api_key", None):
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/v1beta/models",
                    headers={"x-goog-api-key": self.api_key},
                )
                return resp.status_code == 200
        except Exception:
=======
        if not _HAS_GENAI:
            logger.error("google-genai package is not installed")
            return False

        self._client = genai.Client(api_key=self.api_key)
        return True

    async def send_request(self, request: dict[str, Any], context: MCPContext) -> dict[str, Any]:
        """Send request to Google AI API"""
        if self._client is None:
            raise RuntimeError("Google AI adapter not initialized — call initialize() first")

        prompt = request.get("prompt", "")
        if request.get("messages"):
            # Flatten messages to a single prompt for Gemini content API
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

        # google-genai Client is synchronous — run in thread pool
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
        """Check Google AI API health"""
        if self._client is None:
            return False
        try:
            await asyncio.to_thread(self._client.models.list)
            return True
        except Exception as e:
            logger.warning("Google AI health check failed: %s", e)
>>>>>>> origin/main
            return False

    async def get_capabilities(self) -> list[ServerCapability]:
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
    request: dict[str, Any],
    protocol: Optional[ProtocolType] = None,
    context: Optional[MCPContext] = None
) -> dict[str, Any]:
    """Convenience function to send AI request through protocol bridge"""
    bridge = get_protocol_bridge()

    if protocol:
        return await bridge.send_protocol_request(protocol, request, context)
    else:
        return await bridge.route_request(request, None, context)
