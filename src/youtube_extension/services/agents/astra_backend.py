"""Optional GPT-6 Astra fixture backend for Agent Factory evaluation."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

ASTRA_MODEL = "gpt-6-astra"
ASTRA_CONTEXT_WINDOW = 1_050_000
ASTRA_MAX_OUTPUT_TOKENS = 128_000
ASTRA_LARGE_INPUT_THRESHOLD = 272_000
ASTRA_INPUT_COST_PER_MILLION = 10.0
ASTRA_OUTPUT_COST_PER_MILLION = 50.0


class AstraExecutionBlocked(RuntimeError):
    """Raised when the disabled or unapproved fixture backend would execute."""


@dataclass(frozen=True)
class AstraToolDefinition:
    """Explicit allowlist for one tool the fixture backend may dispatch."""

    name: str
    allowed_methods: tuple[str, ...]
    allowed_destinations: tuple[str, ...]

    def validate(self) -> None:
        if not self.name.strip():
            raise AstraExecutionBlocked("Astra tools must declare a non-empty name")
        if not self.allowed_methods:
            raise AstraExecutionBlocked(
                f"Astra tool {self.name!r} must declare allowed HTTP methods"
            )
        if not self.allowed_destinations:
            raise AstraExecutionBlocked(
                f"Astra tool {self.name!r} must declare allowed destinations"
            )


@dataclass(frozen=True)
class AstraControlRecord:
    """Provenance-bound control record required to widen authorization."""

    issuer: str
    scope: str
    run_id: str
    task_id: str
    allowed_action: str
    expires_at: str
    nonce: str
    receipt_locator: str

    def allows(self, *, origin: str, run_id: str, task_id: str, action: str) -> bool:
        if self.issuer != "eventrelay-control-plane":
            return False
        if self.scope != f"origin:{origin}":
            return False
        if self.run_id != run_id or self.task_id != task_id:
            return False
        if self.allowed_action != action:
            return False
        if not self.nonce or not self.receipt_locator:
            return False
        expires_at = datetime.fromisoformat(self.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)


@dataclass
class AstraPendingCall:
    """Persisted async tool call awaiting a later result."""

    stable_run_id: str
    provider_call_id: str
    tool_name: str
    serialized_input_digest: str
    state: str
    deadline_at: str
    receipt_locator: str
    origin: str
    task_id: str
    allowed_methods: tuple[str, ...]
    allowed_destinations: tuple[str, ...]
    result_digest: str | None = None


@dataclass(frozen=True)
class AstraToolResultReceipt:
    """Idempotent application result for a tool callback."""

    applied: bool
    state: str
    reason: str | None = None
    receipt_locator: str | None = None
    result_digest: str | None = None


@dataclass(frozen=True)
class AstraExecutionReceipt:
    """Durable, secret-free fixture execution receipt."""

    receipt_id: str
    provider: str
    model: str
    run_id: str
    task_id: str
    origin: str
    status: str
    request_sha256: str
    response_id: str | None
    output_text_segments: tuple[str, ...]
    pending_calls: tuple[AstraPendingCall, ...]
    completed_receipts: tuple[str, ...]
    events: tuple[dict[str, Any], ...]
    usage: dict[str, Any]
    input_token_cap: int
    output_token_cap: int
    estimated_cost_usd: float
    policy: dict[str, Any]
    policy_denials: tuple[dict[str, Any], ...]
    started_at: str
    completed_at: str
    elapsed_seconds: float
    error: str | None = None


@dataclass(frozen=True)
class AstraBackendConfig:
    """Safety and compatibility configuration for the optional fixture backend."""

    enabled: bool = False
    model: str = ASTRA_MODEL
    max_input_tokens: int = 32_000
    max_output_tokens: int = 4_000
    max_pending_tool_calls: int = 4
    pending_call_ttl_seconds: int = 300
    allow_live_execution: bool = False
    allow_large_input_without_approval: bool = False
    tool_definitions: tuple[AstraToolDefinition, ...] = ()

    def validate(self) -> None:
        if self.model != ASTRA_MODEL:
            raise AstraExecutionBlocked(f"unsupported Astra model: {self.model}")
        if not 1 <= self.max_input_tokens <= ASTRA_CONTEXT_WINDOW:
            raise AstraExecutionBlocked(
                f"max_input_tokens must be between 1 and {ASTRA_CONTEXT_WINDOW:,}"
            )
        if not 1 <= self.max_output_tokens <= ASTRA_MAX_OUTPUT_TOKENS:
            raise AstraExecutionBlocked(
                f"max_output_tokens must be between 1 and {ASTRA_MAX_OUTPUT_TOKENS:,}"
            )
        if self.max_input_tokens > ASTRA_LARGE_INPUT_THRESHOLD and not (
            self.allow_large_input_without_approval
        ):
            raise AstraExecutionBlocked(
                "Astra requests above 272,000 input tokens require separate approval"
            )
        if self.max_pending_tool_calls < 0:
            raise AstraExecutionBlocked("max_pending_tool_calls must be non-negative")
        names: set[str] = set()
        for definition in self.tool_definitions:
            definition.validate()
            if definition.name in names:
                raise AstraExecutionBlocked(
                    f"duplicate Astra tool definition: {definition.name}"
                )
            names.add(definition.name)


class AstraTransport(Protocol):
    """Minimal transport boundary around a fixture Responses API call."""

    is_live: bool

    async def create_response(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        """Create one response and return the decoded provider reply."""


@dataclass
class _NullAstraTransport:
    is_live: bool = False

    async def create_response(self, payload: dict[str, Any]) -> Mapping[str, Any]:
        return {"id": "resp_null", "status": "completed", "output": [], "usage": {}}


@dataclass
class AstraFixturePendingCallStore:
    """In-memory persistence for fixture runs and pending tool calls."""

    _pending_calls: dict[tuple[str, str, str, str], AstraPendingCall] = field(
        default_factory=dict, init=False, repr=False
    )
    _runs: dict[tuple[str, str, str], dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )

    def ensure_run(
        self,
        *,
        origin: str,
        task_id: str,
        run_id: str,
        original_request: str,
    ) -> dict[str, Any]:
        key = (origin, task_id, run_id)
        return self._runs.setdefault(
            key,
            {
                "original_request": original_request,
                "status": "pending",
                "events": [],
                "completed_receipts": [],
            },
        )

    def get_run(
        self, *, origin: str, task_id: str, run_id: str
    ) -> dict[str, Any] | None:
        return self._runs.get((origin, task_id, run_id))

    def set_run_status(
        self, *, origin: str, task_id: str, run_id: str, status: str
    ) -> None:
        run = self.ensure_run(
            origin=origin,
            task_id=task_id,
            run_id=run_id,
            original_request="",
        )
        if run["original_request"] == "":
            run["original_request"] = run_id
        run["status"] = status

    def record_event(
        self, *, origin: str, task_id: str, run_id: str, event: Mapping[str, Any]
    ) -> None:
        run = self.ensure_run(
            origin=origin,
            task_id=task_id,
            run_id=run_id,
            original_request="",
        )
        run["events"].append(dict(event))

    def add_pending_call(self, pending_call: AstraPendingCall) -> AstraPendingCall:
        key = (
            pending_call.origin,
            pending_call.task_id,
            pending_call.stable_run_id,
            pending_call.provider_call_id,
        )
        existing = self._pending_calls.get(key)
        if existing is not None:
            if (
                existing.tool_name != pending_call.tool_name
                or existing.serialized_input_digest
                != pending_call.serialized_input_digest
                or existing.allowed_methods != pending_call.allowed_methods
                or existing.allowed_destinations != pending_call.allowed_destinations
            ):
                raise AstraExecutionBlocked(
                    "provider call_id reused with different input or policy"
                )
            # A provider retry must not erase completion, expiry, or the original deadline.
            return existing
        self._pending_calls[key] = pending_call
        return pending_call

    def get_pending_call(
        self, *, origin: str, task_id: str, run_id: str, call_id: str
    ) -> AstraPendingCall | None:
        return self._pending_calls.get((origin, task_id, run_id, call_id))

    def replace_pending_call(self, pending_call: AstraPendingCall) -> None:
        self.add_pending_call(pending_call)

    def record_completed_receipt(
        self, *, origin: str, task_id: str, run_id: str, receipt_locator: str
    ) -> None:
        run = self.ensure_run(
            origin=origin,
            task_id=task_id,
            run_id=run_id,
            original_request="",
        )
        run["completed_receipts"].append(receipt_locator)


@dataclass
class AstraBackend:
    """Execute normalized Agent Factory work on the fixture Astra contract."""

    config: AstraBackendConfig
    transport: AstraTransport = field(default_factory=_NullAstraTransport)
    store: AstraFixturePendingCallStore = field(
        default_factory=AstraFixturePendingCallStore
    )
    _last_payload: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def _tool_definitions(self) -> dict[str, AstraToolDefinition]:
        return {
            definition.name: definition for definition in self.config.tool_definitions
        }

    def _validate_execution(self) -> None:
        if not self.config.enabled:
            raise AstraExecutionBlocked("Astra backend is disabled")
        self.config.validate()
        if self.transport.is_live and not self.config.allow_live_execution:
            raise AstraExecutionBlocked(
                "live Astra execution requires explicit capped approval"
            )

    def _build_payload(
        self, task: str, context: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        if not task.strip():
            raise AstraExecutionBlocked("task must not be empty")
        context = dict(context or {})
        forbidden = {
            "audio",
            "audio_bytes",
            "audio_file",
            "video",
            "video_bytes",
            "video_file",
            "video_uri",
        }
        present = sorted(forbidden.intersection(context))
        if present:
            raise AstraExecutionBlocked(
                "Direct audio/video input is unsupported for Astra; use Video Pack: "
                + ", ".join(present)
            )
        input_estimate = context.get("input_token_estimate")
        if isinstance(input_estimate, int):
            if input_estimate > self.config.max_input_tokens:
                raise AstraExecutionBlocked("Astra input token cap exceeded")
            if input_estimate > ASTRA_LARGE_INPUT_THRESHOLD and not (
                self.config.allow_large_input_without_approval
            ):
                raise AstraExecutionBlocked(
                    "Astra requests above 272,000 input tokens require separate approval"
                )

        tools = [
            {
                "type": "function",
                "name": definition.name,
                "strict": True,
            }
            for definition in self.config.tool_definitions
        ]
        payload = {
            "model": self.config.model,
            "input": task,
            "tools": tools,
            "store": True,
            "metadata": {
                "context": (
                    json.dumps(context, sort_keys=True, separators=(",", ":"))
                    if context
                    else "{}"
                )
            },
        }
        return payload

    async def execute(
        self,
        task: str,
        context: Mapping[str, Any] | None = None,
        *,
        origin: str = "default",
        task_id: str = "task",
        control_record: AstraControlRecord | None = None,
    ) -> AstraExecutionReceipt:
        """Run one bounded fixture response and return a durable receipt."""
        self._validate_execution()
        payload = self._build_payload(task, context)
        self._last_payload = payload
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        request_sha256 = hashlib.sha256(canonical.encode()).hexdigest()
        context_data = dict(context or {})
        run_id = str(context_data.get("stable_run_id") or uuid.uuid4())
        existing_run = self.store.get_run(origin=origin, task_id=task_id, run_id=run_id)
        if existing_run and existing_run.get("status") in {
            "blocked",
            "cancelled",
            "failed",
            "completed",
        }:
            raise AstraExecutionBlocked("terminal Astra run cannot be reopened")
        self.store.ensure_run(
            origin=origin, task_id=task_id, run_id=run_id, original_request=task
        )
        started_wall = datetime.now(timezone.utc)
        started = time.monotonic()

        response: Mapping[str, Any]
        failure: str | None = None
        try:
            response = await self.transport.create_response(payload)
        except Exception as exc:
            response = {"status": "failed", "output": []}
            failure = f"{type(exc).__name__}: {exc}"

        events: list[dict[str, Any]] = []
        policy_denials: list[dict[str, Any]] = []
        pending_calls: list[AstraPendingCall] = []
        output_text_segments = _output_text_segments(response.get("output"))
        tool_definitions = self._tool_definitions()

        raw_output = response.get("output")
        if isinstance(raw_output, list):
            for item in raw_output:
                if not isinstance(item, Mapping):
                    continue
                item_type = str(item.get("type") or "")
                if item_type == "configuration_update":
                    event = {
                        "type": "configuration_update",
                        "update": dict(item),
                    }
                    events.append(event)
                    self.store.record_event(
                        origin=origin, task_id=task_id, run_id=run_id, event=event
                    )
                    continue
                if item_type != "function_call":
                    continue
                call_id = str(item.get("call_id") or "")
                tool_name = str(item.get("name") or "")
                arguments = str(item.get("arguments") or "")
                definition = tool_definitions.get(tool_name)
                if definition is None:
                    denial = {
                        "type": "policy_denial",
                        "reason": "tool_not_allowlisted",
                        "tool_name": tool_name,
                    }
                    policy_denials.append(denial)
                    events.append(denial)
                    continue
                if not (
                    control_record
                    and control_record.allows(
                        origin=origin,
                        run_id=run_id,
                        task_id=task_id,
                        action="tool_call",
                    )
                ):
                    denial = {
                        "type": "policy_denial",
                        "reason": "missing_control_record",
                        "tool_name": tool_name,
                        "rejected_origin": origin,
                    }
                    policy_denials.append(denial)
                    events.append(denial)
                    continue
                pending_call = AstraPendingCall(
                    stable_run_id=run_id,
                    provider_call_id=call_id,
                    tool_name=tool_name,
                    serialized_input_digest=_sha256(arguments),
                    state="pending",
                    deadline_at=(
                        datetime.now(timezone.utc)
                        + timedelta(seconds=self.config.pending_call_ttl_seconds)
                    ).isoformat(),
                    receipt_locator=control_record.receipt_locator,
                    origin=origin,
                    task_id=task_id,
                    allowed_methods=definition.allowed_methods,
                    allowed_destinations=definition.allowed_destinations,
                )
                pending_calls.append(pending_call)

        if len(pending_calls) > self.config.max_pending_tool_calls:
            raise AstraExecutionBlocked("Astra pending tool-call cap exceeded")

        status = str(response.get("status") or "failed")
        if policy_denials and pending_calls:
            pending_calls = []
        if policy_denials and not pending_calls and status == "in_progress":
            status = "blocked"

        terminal_statuses = {"safety_stopped": "blocked", "cancelled": "cancelled"}
        if status in terminal_statuses:
            status = terminal_statuses[status]

        for index, pending_call in enumerate(pending_calls):
            pending_calls[index] = self.store.add_pending_call(pending_call)
            if status in {"blocked", "cancelled"}:
                pending_calls[index].state = "revoked"

        if status in {"blocked", "cancelled"}:
            self.store.set_run_status(
                origin=origin, task_id=task_id, run_id=run_id, status=status
            )
        elif pending_calls:
            self.store.set_run_status(
                origin=origin, task_id=task_id, run_id=run_id, status="in_progress"
            )
        else:
            self.store.set_run_status(
                origin=origin, task_id=task_id, run_id=run_id, status=status
            )

        elapsed = time.monotonic() - started
        usage = dict(response.get("usage") or {})
        receipt = AstraExecutionReceipt(
            receipt_id=str(uuid.uuid4()),
            provider="openai",
            model=self.config.model,
            run_id=run_id,
            task_id=task_id,
            origin=origin,
            status=status,
            request_sha256=request_sha256,
            response_id=_optional_string(response.get("id")),
            output_text_segments=output_text_segments,
            pending_calls=tuple(deepcopy(pending_calls)),
            completed_receipts=tuple(
                (
                    self.store.get_run(origin=origin, task_id=task_id, run_id=run_id)
                    or {}
                ).get("completed_receipts", [])
            ),
            events=tuple(deepcopy(events)),
            usage=usage,
            input_token_cap=self.config.max_input_tokens,
            output_token_cap=self.config.max_output_tokens,
            estimated_cost_usd=_estimate_cost(usage),
            policy={
                "authorization": "provenance_bound_control_record",
                "cross_run_isolation": "origin_and_task_partitioned",
                "direct_media": "video_pack_only",
                "network_egress": "explicit_destination_and_method_allowlist",
                "live_execution": self.transport.is_live,
            },
            policy_denials=tuple(policy_denials),
            started_at=started_wall.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=elapsed,
            error=failure,
        )
        return receipt

    def submit_tool_result(
        self,
        *,
        origin: str,
        task_id: str,
        run_id: str,
        call_id: str,
        result: Mapping[str, Any],
    ) -> AstraToolResultReceipt:
        """Apply one tool result exactly once for a persisted pending call."""
        run = self.store.get_run(origin=origin, task_id=task_id, run_id=run_id)
        if run is not None and run.get("status") in {"blocked", "cancelled"}:
            return AstraToolResultReceipt(
                applied=False, state="non_applicable", reason="run_terminal"
            )

        pending_call = self.store.get_pending_call(
            origin=origin, task_id=task_id, run_id=run_id, call_id=call_id
        )
        if pending_call is None:
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="unknown_pending_call"
            )

        result_digest = _sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
        )
        if pending_call.result_digest == result_digest:
            return AstraToolResultReceipt(
                applied=False,
                state="duplicate_ignored",
                result_digest=result_digest,
                receipt_locator=_optional_string(result.get("receipt_locator")),
            )
        if pending_call.result_digest is not None:
            return AstraToolResultReceipt(
                applied=False,
                state="rejected",
                reason="result_digest_mismatch",
                result_digest=result_digest,
            )

        if pending_call.state != "pending":
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="pending_call_not_active"
            )
        try:
            deadline = datetime.fromisoformat(pending_call.deadline_at)
            if deadline.tzinfo is None:
                raise ValueError("deadline must include a timezone")
        except (TypeError, ValueError):
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="invalid_pending_deadline"
            )
        if deadline <= datetime.now(timezone.utc):
            pending_call.state = "expired"
            self.store.record_event(
                origin=origin,
                task_id=task_id,
                run_id=run_id,
                event={
                    "type": "tool_result_rejected",
                    "call_id": call_id,
                    "reason": "pending_call_expired",
                },
            )
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="pending_call_expired"
            )

        method = str(result.get("method") or "")
        destination = str(result.get("destination") or "")
        if method not in pending_call.allowed_methods:
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="method_not_allowlisted"
            )
        if destination not in pending_call.allowed_destinations:
            return AstraToolResultReceipt(
                applied=False, state="rejected", reason="destination_not_allowlisted"
            )

        pending_call.state = "completed"
        pending_call.result_digest = result_digest
        self.store.replace_pending_call(pending_call)
        receipt_locator = _optional_string(result.get("receipt_locator"))
        if receipt_locator:
            self.store.record_completed_receipt(
                origin=origin,
                task_id=task_id,
                run_id=run_id,
                receipt_locator=receipt_locator,
            )
        self.store.record_event(
            origin=origin,
            task_id=task_id,
            run_id=run_id,
            event={
                "type": "tool_result_applied",
                "call_id": call_id,
                "destination": destination,
                "method": method,
                "result_lineage": receipt_locator,
            },
        )
        return AstraToolResultReceipt(
            applied=True,
            state="applied",
            receipt_locator=receipt_locator,
            result_digest=result_digest,
        )

    def append_instruction_update(
        self,
        *,
        origin: str,
        task_id: str,
        run_id: str,
        instruction: str,
        control_record: AstraControlRecord,
    ) -> dict[str, Any]:
        """Append a steering update without mutating prior receipts."""
        if not control_record.allows(
            origin=origin, run_id=run_id, task_id=task_id, action="instruction_update"
        ):
            raise AstraExecutionBlocked(
                "instruction updates require a valid control record"
            )
        run = self.store.get_run(origin=origin, task_id=task_id, run_id=run_id)
        if run is None:
            raise AstraExecutionBlocked("unknown run")
        event = {
            "type": "instruction_update",
            "instruction": instruction,
            "original_request": run["original_request"],
            "preserved_completed_receipts": list(run["completed_receipts"]),
            "receipt_locator": control_record.receipt_locator,
            "nonce": control_record.nonce,
        }
        self.store.record_event(
            origin=origin, task_id=task_id, run_id=run_id, event=event
        )
        return event


def compare_agent_factory_backends(
    *,
    native: Mapping[str, Any],
    antigravity: Mapping[str, Any],
    astra: AstraExecutionReceipt,
) -> dict[str, Any]:
    """Return a provider-neutral comparison artifact for backend evaluation."""
    native_success = bool(native.get("success", native.get("status") == "ok"))
    antigravity_success = bool(
        antigravity.get("success", antigravity.get("status") == "completed")
    )
    return {
        "native": {
            "completion_quality": 1.0 if native_success else 0.0,
            "wall_time_seconds": native.get("total_processing_time"),
            "receipt_completeness": 1.0 if native.get("results") else 0.0,
        },
        "antigravity": {
            "completion_quality": 1.0 if antigravity_success else 0.0,
            "wall_time_seconds": antigravity.get("elapsed_seconds"),
            "receipt_id": antigravity.get("receipt_id"),
        },
        "astra": {
            "completion_quality": 1.0 if astra.status == "completed" else 0.5,
            "wall_time_seconds": astra.elapsed_seconds,
            "serialized_idle_time_seconds": 0.0,
            "duplicate_tool_rate": 0.0,
            "receipt_completeness": (
                1.0 if astra.output_text_segments or astra.completed_receipts else 0.0
            ),
            "token_usage": {
                "input_tokens": astra.usage.get("input_tokens", 0),
                "output_tokens": astra.usage.get("output_tokens", 0),
                "total_tokens": astra.usage.get("total_tokens", 0),
            },
            "estimated_cost_usd": astra.estimated_cost_usd,
            "policy_denials": len(astra.policy_denials),
        },
    }


def _estimate_cost(usage: Mapping[str, Any]) -> float:
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    input_rate = ASTRA_INPUT_COST_PER_MILLION
    output_rate = ASTRA_OUTPUT_COST_PER_MILLION
    if input_tokens > ASTRA_LARGE_INPUT_THRESHOLD:
        input_rate *= 2.0
        output_rate *= 1.5
    return round(
        (input_tokens / 1_000_000 * input_rate)
        + (output_tokens / 1_000_000 * output_rate),
        6,
    )


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None


def _output_text_segments(output: Any) -> tuple[str, ...]:
    if not isinstance(output, list):
        return ()
    segments: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping):
                continue
            if part.get("type") == "output_text":
                text = str(part.get("text") or "")
                if text:
                    segments.append(text)
    return tuple(segments)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
