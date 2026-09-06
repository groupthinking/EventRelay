"""Optional Google Antigravity execution backend for Agent Factory.

The backend is feature-flagged and transport-injected.  That keeps unit tests
deterministic and prevents importing a provider SDK or making a billable call
unless a caller explicitly supplies a live transport and acknowledges the
provider's fail-open hook behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse


ANTIGRAVITY_AGENT = "antigravity-preview-05-2026"
_MCP_NAME = re.compile(r"^[a-z0-9]+$")


class AntigravityConfigurationError(ValueError):
    """Raised when an adapter configuration violates the provider contract."""


class AntigravityExecutionBlocked(RuntimeError):
    """Raised when a disabled or unapproved backend would execute."""


class AntigravityTransport(Protocol):
    """Minimal transport boundary around ``POST /v1beta/interactions``."""

    is_live: bool

    async def create_interaction(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        """Create one interaction and return the decoded provider response."""


@dataclass(frozen=True)
class AntigravityMCPServer:
    """A Streamable HTTP MCP server exposed to the managed agent."""

    name: str
    url: str
    allowed_tools: tuple[str, ...]

    def validate(self, read_only_tools: frozenset[str]) -> None:
        if not _MCP_NAME.fullmatch(self.name):
            raise AntigravityConfigurationError(
                "MCP server name must contain lowercase ASCII letters and digits only"
            )
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise AntigravityConfigurationError(
                "MCP server URL must use HTTPS Streamable HTTP"
            )
        if not self.allowed_tools:
            raise AntigravityConfigurationError(
                "MCP server must declare an explicit allowed_tools list"
            )
        undeclared = set(self.allowed_tools) - read_only_tools
        if undeclared:
            raise AntigravityConfigurationError(
                "MCP tools are not in the read-only allowlist: "
                + ", ".join(sorted(undeclared))
            )


@dataclass(frozen=True)
class AntigravityBackendConfig:
    """Safety and compatibility configuration for the optional backend."""

    enabled: bool = False
    agent: str = ANTIGRAVITY_AGENT
    max_total_tokens: int = 50_000
    mcp_servers: tuple[AntigravityMCPServer, ...] = ()
    read_only_tools: frozenset[str] = frozenset()
    allow_live_execution: bool = False
    acknowledge_fail_open_hooks: bool = False

    def validate(self) -> None:
        if self.agent != ANTIGRAVITY_AGENT:
            raise AntigravityConfigurationError(
                f"unsupported Antigravity agent: {self.agent}"
            )
        if not 1 <= self.max_total_tokens <= 1_000_000:
            raise AntigravityConfigurationError(
                "max_total_tokens must be between 1 and 1,000,000"
            )
        if not self.mcp_servers:
            raise AntigravityConfigurationError(
                "at least one read-only MCP server is required"
            )
        names: set[str] = set()
        for server in self.mcp_servers:
            server.validate(self.read_only_tools)
            if server.name in names:
                raise AntigravityConfigurationError(
                    f"duplicate MCP server name: {server.name}"
                )
            names.add(server.name)


@dataclass(frozen=True)
class AntigravityExecutionReceipt:
    """Durable, secret-free result from one managed-agent attempt."""

    receipt_id: str
    provider: str
    agent: str
    status: str
    request_sha256: str
    interaction_id: str | None
    environment_id: str | None
    output_text: str | None
    steps: tuple[dict[str, Any], ...]
    usage: dict[str, Any]
    max_total_tokens: int
    budget_exceeded: bool
    mcp_servers: tuple[str, ...]
    policy: dict[str, Any]
    started_at: str
    completed_at: str
    elapsed_seconds: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AntigravityBackend:
    """Execute normalized Agent Factory work on Google's managed runtime."""

    config: AntigravityBackendConfig
    transport: AntigravityTransport
    _last_payload: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def _validate_execution(self) -> None:
        if not self.config.enabled:
            raise AntigravityExecutionBlocked("Antigravity backend is disabled")
        self.config.validate()
        if self.transport.is_live and not self.config.allow_live_execution:
            raise AntigravityExecutionBlocked(
                "live Antigravity execution requires explicit approval"
            )
        if self.transport.is_live and not self.config.acknowledge_fail_open_hooks:
            raise AntigravityExecutionBlocked(
                "live execution requires acknowledgement that provider hooks fail open"
            )

    def build_payload(
        self,
        task: str,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a text-only Interactions API request with read-only MCP tools."""
        self.config.validate()
        if not task.strip():
            raise AntigravityConfigurationError("task must not be empty")

        context = dict(context or {})
        forbidden = {
            "video",
            "video_bytes",
            "video_file",
            "video_uri",
            "audio",
            "audio_file",
            "image",
            "images",
            "image_bytes",
            "image_file",
            "image_uri",
            "document",
        }
        present = sorted(forbidden.intersection(context))
        if present:
            raise AntigravityConfigurationError(
                "This adapter accepts normalized text context, not direct media: "
                + ", ".join(present)
            )

        input_text = task
        if context:
            input_text += "\n\nAgent Factory context:\n" + json.dumps(
                context, sort_keys=True, separators=(",", ":"), default=str
            )

        tools = [
            {
                "type": "mcp_server",
                "name": server.name,
                "url": server.url,
                "allowed_tools": list(server.allowed_tools),
            }
            for server in self.config.mcp_servers
        ]
        return {
            "agent": self.config.agent,
            "input": input_text,
            "environment": "remote",
            "tools": tools,
            "agent_config": {
                "type": "antigravity",
                "max_total_tokens": self.config.max_total_tokens,
            },
            "background": False,
            "store": True,
        }

    async def execute(
        self,
        task: str,
        context: Mapping[str, Any] | None = None,
    ) -> AntigravityExecutionReceipt:
        """Run one bounded interaction and return a durable execution receipt."""
        self._validate_execution()
        payload = self.build_payload(task, context)
        self._last_payload = payload
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        request_sha256 = hashlib.sha256(canonical.encode()).hexdigest()
        started_wall = datetime.now(timezone.utc)
        started = time.monotonic()

        response: Mapping[str, Any]
        failure: str | None = None
        try:
            response = await self.transport.create_interaction(payload)
        except Exception as exc:  # receipt failures instead of losing audit state
            response = {"status": "failed"}
            failure = f"{type(exc).__name__}: {exc}"

        elapsed = time.monotonic() - started
        usage = dict(response.get("usage") or {})
        total_tokens = usage.get("total_tokens")
        budget_exceeded = (
            isinstance(total_tokens, (int, float))
            and total_tokens > self.config.max_total_tokens
        )
        raw_steps = response.get("steps") or []
        steps = tuple(dict(step) for step in raw_steps if isinstance(step, Mapping))
        status = str(response.get("status") or "failed")
        error_value = response.get("error")
        if failure is None and error_value is not None:
            failure = str(error_value)

        return AntigravityExecutionReceipt(
            receipt_id=str(uuid.uuid4()),
            provider="google",
            agent=self.config.agent,
            status=status,
            request_sha256=request_sha256,
            interaction_id=_optional_string(response.get("id")),
            environment_id=_optional_string(response.get("environment_id")),
            output_text=_optional_string(response.get("output_text")),
            steps=steps,
            usage=usage,
            max_total_tokens=self.config.max_total_tokens,
            budget_exceeded=budget_exceeded,
            mcp_servers=tuple(server.name for server in self.config.mcp_servers),
            policy={
                "mcp_access": "explicit_read_only_allowlist",
                "provider_hooks": "fail_open",
                "direct_media": "denied",
                "automatic_continuation": "denied",
                "live_execution": self.transport.is_live,
            },
            started_at=started_wall.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=elapsed,
            error=failure,
        )


def compare_agent_factory_runs(
    native: Mapping[str, Any], managed: AntigravityExecutionReceipt
) -> dict[str, Any]:
    """Return a small provider-neutral comparison artifact for evaluation."""
    native_success = bool(native.get("success", native.get("status") == "ok"))
    return {
        "native": {
            "success": native_success,
            "elapsed_seconds": native.get("total_processing_time"),
            "output_present": bool(native.get("output") or native.get("results")),
        },
        "antigravity": {
            "success": managed.status == "completed" and managed.error is None,
            "elapsed_seconds": managed.elapsed_seconds,
            "total_tokens": managed.usage.get("total_tokens"),
            "budget_exceeded": managed.budget_exceeded,
            "output_present": bool(managed.output_text),
            "receipt_id": managed.receipt_id,
        },
    }


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
