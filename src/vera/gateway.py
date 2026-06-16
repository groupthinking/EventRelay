"""
VERA Pillar 4: Segmentation — Capability-Based Tool Permissions

Controls what each agent CAN and CANNOT do. Like security clearances:
a video ingest agent can read transcripts but not deploy code. Permissions
are explicit — if it's not granted, it's denied.

Capability manifests are YAML files in VERA_CAPABILITIES_DIR. Each agent
declares its tools, allowed operations, and constraints. The gateway
validates every tool call against the manifest before execution.

Dependencies: pyyaml (for YAML capability files)
Env vars: VERA_CAPABILITIES_DIR
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_vera_config

logger = logging.getLogger("vera.gateway")


@dataclass
class PermissionDecision:
    """Result of a gateway permission check."""
    request_id: str
    agent_id: str
    tool: str
    operation: str
    allowed: bool
    reason: str
    constraints: dict = field(default_factory=dict)
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "tool": self.tool,
            "operation": self.operation,
            "allowed": self.allowed,
            "reason": self.reason,
            "constraints": self.constraints,
            "checked_at": self.checked_at,
        }


class CapabilityManifest:
    """Parsed agent capability manifest."""

    def __init__(self, agent_id: str, raw: dict):
        self.agent_id = agent_id
        self.agent_name = raw.get("agent_name", agent_id)
        self.version = raw.get("version", "1")
        self.denied_by_default = raw.get("denied_by_default", True)

        # Parse capabilities into a lookup structure:
        # {tool_name: {operation_name: {allowed: bool, constraints: dict}}}
        self._permissions: dict[str, dict[str, dict]] = {}
        for cap in raw.get("capabilities", []):
            tool = cap.get("tool", "")
            ops = {}
            for op in cap.get("operations", []):
                ops[op["name"]] = {
                    "allowed": op.get("allowed", False),
                    "constraints": op.get("constraints", {}),
                }
            self._permissions[tool] = ops

    def check(self, tool: str, operation: str, maturity_level: int = 0) -> PermissionDecision:
        """Check if an operation is permitted under this manifest."""
        request_id = str(uuid.uuid4())

        # Find tool
        tool_ops = self._permissions.get(tool)
        if tool_ops is None:
            if self.denied_by_default:
                return PermissionDecision(
                    request_id=request_id,
                    agent_id=self.agent_id,
                    tool=tool,
                    operation=operation,
                    allowed=False,
                    reason=f"Tool '{tool}' not in capability manifest (deny-by-default)",
                )
            # If not deny-by-default (unusual), allow unlisted tools
            return PermissionDecision(
                request_id=request_id,
                agent_id=self.agent_id,
                tool=tool,
                operation=operation,
                allowed=True,
                reason="Tool not listed, deny-by-default is OFF",
            )

        # Find operation
        op_config = tool_ops.get(operation)
        if op_config is None:
            if self.denied_by_default:
                return PermissionDecision(
                    request_id=request_id,
                    agent_id=self.agent_id,
                    tool=tool,
                    operation=operation,
                    allowed=False,
                    reason=f"Operation '{operation}' not in manifest for tool '{tool}'",
                )
            return PermissionDecision(
                request_id=request_id,
                agent_id=self.agent_id,
                tool=tool,
                operation=operation,
                allowed=True,
                reason="Operation not listed, deny-by-default is OFF",
            )

        # Check allowed flag
        if not op_config["allowed"]:
            return PermissionDecision(
                request_id=request_id,
                agent_id=self.agent_id,
                tool=tool,
                operation=operation,
                allowed=False,
                reason=f"Operation '{operation}' explicitly denied",
            )

        # Check maturity constraint
        constraints = op_config.get("constraints", {})
        required_maturity = constraints.get("requires_maturity", 0)
        if maturity_level < required_maturity:
            return PermissionDecision(
                request_id=request_id,
                agent_id=self.agent_id,
                tool=tool,
                operation=operation,
                allowed=False,
                reason=f"Requires maturity level {required_maturity}, agent is at {maturity_level}",
                constraints=constraints,
            )

        return PermissionDecision(
            request_id=request_id,
            agent_id=self.agent_id,
            tool=tool,
            operation=operation,
            allowed=True,
            reason="Permission granted",
            constraints=constraints,
        )


class CapabilityGateway:
    """Enforces capability-based permissions for all agent tool calls.

    Loads capability manifests from YAML files on disk. Each agent has a
    manifest declaring what tools and operations it can use. Every tool
    call passes through the gateway — unlisted operations are denied.
    """

    def __init__(self):
        self.config = get_vera_config()
        self._manifests: dict[str, CapabilityManifest] = {}
        self._auth_failure_counts: dict[str, int] = {}
        self._load_manifests()

    def _load_manifests(self) -> None:
        """Load all capability manifests from the configured directory."""
        caps_dir = Path(self.config.capabilities_dir)
        if not caps_dir.exists():
            logger.warning(
                "capabilities_dir_missing",
                extra={"path": str(caps_dir)},
            )
            return

        try:
            import yaml
        except ImportError:
            logger.warning(
                "pyyaml_not_installed — capability manifests cannot be loaded. "
                "Install with: pip install pyyaml"
            )
            return

        for yaml_file in caps_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    raw = yaml.safe_load(f)
                if raw and isinstance(raw, dict):
                    agent_id = raw.get("agent_id", yaml_file.stem)
                    manifest = CapabilityManifest(agent_id, raw)
                    self._manifests[agent_id] = manifest
                    logger.info(
                        "capability_manifest_loaded",
                        extra={"agent_id": agent_id, "file": yaml_file.name},
                    )
            except Exception as e:
                logger.error(
                    "capability_manifest_load_failed",
                    extra={"file": yaml_file.name, "error": str(e)},
                )

        logger.info(
            "gateway_initialized",
            extra={"manifests_loaded": len(self._manifests)},
        )

    def check_permission(
        self,
        agent_id: str,
        tool: str,
        operation: str,
        maturity_level: int = 0,
    ) -> PermissionDecision:
        """Check if an agent has permission to perform a tool operation.

        Args:
            agent_id: The agent requesting permission.
            tool: The tool being accessed (e.g., "mcp-agent-network").
            operation: The operation being performed (e.g., "generate_blueprint").
            maturity_level: The agent's current maturity level.

        Returns:
            PermissionDecision with allowed=True/False and reason.
        """
        manifest = self._manifests.get(agent_id)

        if manifest is None:
            # No manifest = use default policy
            decision = self._default_policy(agent_id, tool, operation)
        else:
            decision = manifest.check(tool, operation, maturity_level)

        # Track authorization failures for enforcement escalation
        if not decision.allowed:
            self._auth_failure_counts[agent_id] = (
                self._auth_failure_counts.get(agent_id, 0) + 1
            )

        logger.info(
            "gateway_decision",
            extra={
                "agent_id": agent_id,
                "tool": tool,
                "operation": operation,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "maturity_level": maturity_level,
            },
        )

        return decision

    def get_auth_failure_count(self, agent_id: str) -> int:
        """Get the number of authorization failures for an agent."""
        return self._auth_failure_counts.get(agent_id, 0)

    def reset_auth_failures(self, agent_id: str) -> None:
        """Reset authorization failure count (called after circuit breaker reset)."""
        self._auth_failure_counts.pop(agent_id, None)

    def register_manifest(self, agent_id: str, raw: dict) -> None:
        """Register a capability manifest programmatically (for testing or dynamic agents)."""
        manifest = CapabilityManifest(agent_id, raw)
        self._manifests[agent_id] = manifest
        logger.info(
            "manifest_registered_programmatically",
            extra={"agent_id": agent_id},
        )

    def get_agent_capabilities(self, agent_id: str) -> Optional[dict]:
        """Get an agent's capability summary (for the /types endpoint)."""
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return None
        return {
            "agent_id": agent_id,
            "agent_name": manifest.agent_name,
            "version": manifest.version,
            "denied_by_default": manifest.denied_by_default,
            "tools": list(manifest._permissions.keys()),
        }

    def _default_policy(self, agent_id: str, tool: str, operation: str) -> PermissionDecision:
        """Default policy when no manifest exists for an agent.

        In development: ALLOW with warning (so existing agents work).
        In production: DENY (enforce manifests).
        """
        if self.config.is_production:
            return PermissionDecision(
                request_id=str(uuid.uuid4()),
                agent_id=agent_id,
                tool=tool,
                operation=operation,
                allowed=False,
                reason="No capability manifest found (production requires manifests)",
            )

        logger.warning(
            "default_policy_allow",
            extra={
                "agent_id": agent_id,
                "tool": tool,
                "operation": operation,
                "note": "No manifest — allowing in development mode",
            },
        )
        return PermissionDecision(
            request_id=str(uuid.uuid4()),
            agent_id=agent_id,
            tool=tool,
            operation=operation,
            allowed=True,
            reason="No manifest (development mode — allow by default)",
        )


# --- Module-level singleton ---

_gateway: Optional[CapabilityGateway] = None


def get_gateway() -> CapabilityGateway:
    """Get the singleton capability gateway."""
    global _gateway
    if _gateway is None:
        _gateway = CapabilityGateway()
    return _gateway
