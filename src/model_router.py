"""Centralized routing logic for selecting AI providers.

This module inspects task metadata, Claude's planning hints, and
system-level routing preferences to decide which provider should
own a given request. It keeps the heuristic logic in a single place
so that MCP Bridge, RAG pipelines, or future services can all rely on
the same decision surface.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

ModelProvider = None
try:  # pragma: no cover - prefer the official SDK module name
    ModelProvider = importlib.import_module("unified_ai_sdk.rate_limiter").ModelProvider
except ModuleNotFoundError:  # pragma: no cover - try legacy naming
    try:
        ModelProvider = importlib.import_module("unified-ai-sdk.rate_limiter").ModelProvider
    except ModuleNotFoundError:
        ModelProvider = None

if ModelProvider is None:  # pragma: no cover - fallback for local testing
    class ModelProvider:  # type: ignore
        """Fallback stub for ModelProvider when SDK is unavailable."""

        def __init__(self, value: str):
            self.value = value

        def __repr__(self) -> str:  # pragma: no cover - debugging helper
            return f"ModelProvider({self.value})"

    # Provide a minimal set of common providers so code keeps working
    ModelProvider.CLAUDE = ModelProvider("claude")  # type: ignore[attr-defined]
    ModelProvider.GROK = ModelProvider("grok")  # type: ignore[attr-defined]
    ModelProvider.OPENAI = ModelProvider("openai")  # type: ignore[attr-defined]
    ModelProvider.GEMINI = ModelProvider("gemini")  # type: ignore[attr-defined]


logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents the outcome of a routing decision."""

    provider: ModelProvider
    reason: str
    signals: Dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """Centralized heuristic routing for multi-model orchestration."""

    REALTIME_KEYWORDS = {
        "breaking",
        "real-time",
        "trend",
        "twitter",
        "x.com",
        "live",
        "market",
        "news",
    }
    CODE_KEYWORDS = {
        "code",
        "stack trace",
        "error",
        "bug",
        "function",
        "class",
        "compile",
    }
    VIDEO_KEYWORDS = {"video", "transcript", "frame", "segment", "youtube"}
    SAFETY_KEYWORDS = {"policy", "compliance", "safety", "ethics", "governance"}

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        routing_cfg = self._extract_routing_config(self.config)
        self.strategy = routing_cfg.get("strategy", "balanced")
        self.fallback_order = self._build_fallback_order(routing_cfg.get("fallback_order"))
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            "ModelRouter initialized | strategy=%s | fallback=%s",
            self.strategy,
            [provider.name for provider in self.fallback_order],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def select_provider(
        self,
        *,
        task_type: Optional[Any],
        priority: Optional[Any],
        content: Optional[Dict[str, Any]] = None,
        preferred_provider: Optional[ModelProvider] = None,
        claude_plan: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """Return the provider that should own this request."""

        if preferred_provider:
            return RoutingDecision(
                provider=preferred_provider,
                reason="preferred_provider",
                signals={"source": "request"},
            )

        recommended = self._provider_from_plan(claude_plan)
        if recommended:
            return RoutingDecision(
                provider=recommended,
                reason="claude_plan",
                signals={"source": "claude-autonomy"},
            )

        signals = self._detect_signals(task_type, priority, content)
        provider = self._route_from_signals(signals)

        return RoutingDecision(provider=provider, reason=signals.get("reason", "heuristic"), signals=signals)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_routing_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        candidates = [
            config.get("model_routing", {}),
            config.get("routing", {}),
            config.get("features", {}).get("model_routing", {}),
        ]
        for entry in candidates:
            if entry:
                return entry
        return {}

    def _build_fallback_order(self, configured_order: Optional[Iterable[str]]) -> list:
        order: list[ModelProvider] = []
        iterable = configured_order or ["claude", "grok", "openai", "gemini"]
        for provider_name in iterable:
            provider = self._to_provider(provider_name)
            if provider and provider not in order:
                order.append(provider)

        if not order:
            # last-resort fallback is the enum order
            try:
                order = list(ModelProvider)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - fallback for stub enum
                order = [ModelProvider.CLAUDE, ModelProvider.GROK, ModelProvider.OPENAI]  # type: ignore[attr-defined]
        return order

    def _provider_from_plan(self, plan: Optional[Dict[str, Any]]) -> Optional[ModelProvider]:
        if not plan:
            return None
        provider_hint = plan.get("recommended_provider") or plan.get("provider")
        return self._to_provider(provider_hint)

    def _detect_signals(
        self,
        task_type: Optional[Any],
        priority: Optional[Any],
        content: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        task_value = self._normalize_value(task_type)
        priority_value = self._normalize_value(priority)

        text_blob = self._flatten_text(content)
        requires_real_time = any(keyword in text_blob for keyword in self.REALTIME_KEYWORDS) or (
            task_value and "trend" in task_value
        )
        is_code_heavy = any(keyword in text_blob for keyword in self.CODE_KEYWORDS) or (
            task_value and "code" in task_value
        )
        is_video_task = any(keyword in text_blob for keyword in self.VIDEO_KEYWORDS) or (
            task_value and "video" in task_value
        )
        is_safety_sensitive = any(keyword in text_blob for keyword in self.SAFETY_KEYWORDS)

        if priority_value in {"critical", "high"} and not requires_real_time:
            # Claude handles high-stakes reasoning better by default
            default_reason = "high_priority"
            default_provider = self._to_provider("claude") or self.fallback_order[0]
        else:
            default_reason = "fallback"
            default_provider = self.fallback_order[0]

        signals = {
            "task_type": task_value,
            "priority": priority_value,
            "requires_real_time": requires_real_time,
            "code_heavy": is_code_heavy,
            "video_analysis": is_video_task,
            "safety_sensitive": is_safety_sensitive,
            "default_provider": default_provider,
            "reason": default_reason,
        }
        return signals

    def _route_from_signals(self, signals: Dict[str, Any]) -> ModelProvider:
        if signals.get("requires_real_time"):
            provider = self._to_provider("grok")
            if provider:
                signals["reason"] = "real_time_signal"
                return provider

        if signals.get("code_heavy"):
            provider = self._to_provider("grok")
            if provider:
                signals["reason"] = "code_generation"
                return provider

        if signals.get("video_analysis"):
            provider = self._to_provider("claude")
            if provider:
                signals["reason"] = "video_analysis"
                return provider

        if signals.get("safety_sensitive"):
            provider = self._to_provider("claude")
            if provider:
                signals["reason"] = "safety_sensitive"
                return provider

        if self.strategy == "cost_effective":
            provider = self._cost_effective_provider(signals)
            if provider:
                signals["reason"] = "cost_effective"
                return provider

        return signals.get("default_provider") or self.fallback_order[0]

    def _cost_effective_provider(self, signals: Dict[str, Any]) -> Optional[ModelProvider]:
        priority = signals.get("priority") or "normal"
        if priority in {"low", "background"}:
            preferred = ["openai", "grok", "claude"]
        elif priority in {"critical", "high"}:
            preferred = ["claude", "grok", "openai"]
        else:
            preferred = ["grok", "openai", "claude"]

        for name in preferred:
            provider = self._to_provider(name)
            if provider:
                return provider
        return None

    def _flatten_text(self, content: Optional[Dict[str, Any]]) -> str:
        if not content:
            return ""
        fragments = []
        for value in content.values():
            if isinstance(value, str):
                fragments.append(value.lower())
            elif isinstance(value, (list, tuple)):
                fragments.extend(str(item).lower() for item in value if isinstance(item, (str, int, float)))
            elif isinstance(value, dict):
                fragments.append(self._flatten_text(value))
        return " ".join(fragments)

    def _normalize_value(self, value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower()
        if hasattr(value, "value"):
            return str(value.value).lower()
        if hasattr(value, "name"):
            return str(value.name).lower()
        return str(value).lower()

    def _to_provider(self, name: Optional[str]) -> Optional[ModelProvider]:
        if not name:
            return None
        normalized = str(name).lower()
        for provider in self._iterate_providers():
            if provider.name.lower() == normalized or str(provider.value).lower() == normalized:
                return provider
        return None

    def _iterate_providers(self) -> Iterable[ModelProvider]:
        try:
            providers = list(ModelProvider)  # type: ignore[arg-type]
        except TypeError:
            providers = [
                getattr(ModelProvider, "CLAUDE", None),
                getattr(ModelProvider, "GROK", None),
                getattr(ModelProvider, "OPENAI", None),
                getattr(ModelProvider, "GEMINI", None),
            ]
        return [provider for provider in providers if provider]
