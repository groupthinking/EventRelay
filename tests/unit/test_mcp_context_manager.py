"""Unit tests for core/mcp/context_manager.py."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


def _inject_stub(name: str, path: str) -> None:
    if name not in sys.modules:
        stub = _types.ModuleType(name)
        stub.__path__ = [path]
        stub.__package__ = name
        sys.modules[name] = stub


def _load(rel_path: str, canonical: str):
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(canonical, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[canonical] = mod
    spec.loader.exec_module(mod)
    return mod


_inject_stub("youtube_extension.core", str(_SRC / "youtube_extension/core"))
_inject_stub("youtube_extension.core.mcp", str(_SRC / "youtube_extension/core/mcp"))

_ctx_mod = _load(
    "youtube_extension/core/mcp/context_manager.py",
    "youtube_extension.core.mcp.context_manager",
)
ContextPriority = _ctx_mod.ContextPriority
ContextStatus = _ctx_mod.ContextStatus
MCPContext = _ctx_mod.MCPContext
MCPContextManager = _ctx_mod.MCPContextManager


# ===========================================================================
# ContextStatus enum
# ===========================================================================


class TestContextStatus:
    def test_active_value(self):
        assert ContextStatus.ACTIVE.value == "active"

    def test_pending_value(self):
        assert ContextStatus.PENDING.value == "pending"

    def test_completed_value(self):
        assert ContextStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert ContextStatus.FAILED.value == "failed"

    def test_expired_value(self):
        assert ContextStatus.EXPIRED.value == "expired"

    def test_has_five_members(self):
        assert len(ContextStatus) == 5


# ===========================================================================
# ContextPriority enum
# ===========================================================================


class TestContextPriority:
    def test_low_value(self):
        assert ContextPriority.LOW.value == "low"

    def test_normal_value(self):
        assert ContextPriority.NORMAL.value == "normal"

    def test_high_value(self):
        assert ContextPriority.HIGH.value == "high"

    def test_critical_value(self):
        assert ContextPriority.CRITICAL.value == "critical"

    def test_has_four_members(self):
        assert len(ContextPriority) == 4


# ===========================================================================
# MCPContext model
# ===========================================================================


def _make_ctx(**kwargs):
    defaults = dict(user="user1", task="task1", intent="do something")
    defaults.update(kwargs)
    return MCPContext(**defaults)


class TestMCPContextDefaults:
    def test_id_auto_generated(self):
        ctx = _make_ctx()
        assert len(ctx.id) == 36  # UUID

    def test_user_stored(self):
        assert _make_ctx().user == "user1"

    def test_task_stored(self):
        assert _make_ctx().task == "task1"

    def test_intent_stored(self):
        assert _make_ctx().intent == "do something"

    def test_env_defaults_development(self):
        assert _make_ctx().env == "development"

    def test_code_state_defaults_empty(self):
        assert _make_ctx().code_state == {}

    def test_subtask_defaults_none(self):
        assert _make_ctx().subtask is None

    def test_history_defaults_empty(self):
        assert _make_ctx().history == []

    def test_metadata_defaults_empty(self):
        assert _make_ctx().metadata == {}

    def test_status_defaults_active(self):
        assert _make_ctx().status == ContextStatus.ACTIVE

    def test_priority_defaults_normal(self):
        assert _make_ctx().priority == ContextPriority.NORMAL

    def test_created_at_set(self):
        before = datetime.utcnow()
        ctx = _make_ctx()
        assert ctx.created_at >= before

    def test_expires_at_set_24h_from_creation(self):
        before = datetime.utcnow()
        ctx = _make_ctx()
        expected = before + timedelta(hours=24)
        diff = abs((ctx.expires_at - expected).total_seconds())
        assert diff < 5  # within 5 seconds

    def test_checksum_default_none(self):
        assert _make_ctx().checksum is None


# ===========================================================================
# MCPContext.update_checksum / validate_integrity
# ===========================================================================


class TestMCPContextChecksum:
    def test_update_checksum_sets_value(self):
        ctx = _make_ctx()
        ctx.update_checksum()
        assert ctx.checksum is not None
        assert len(ctx.checksum) == 64

    def test_validate_integrity_true_after_update(self):
        ctx = _make_ctx()
        ctx.update_checksum()
        assert ctx.validate_integrity() is True

    def test_validate_integrity_false_without_checksum(self):
        ctx = _make_ctx()
        assert ctx.validate_integrity() is False

    def test_validate_integrity_false_after_modification(self):
        ctx = _make_ctx()
        ctx.update_checksum()
        ctx.user = "tampered"
        assert ctx.validate_integrity() is False


# ===========================================================================
# MCPContext.add_history_entry
# ===========================================================================


class TestMCPContextHistory:
    def test_history_entry_added(self):
        ctx = _make_ctx()
        ctx.add_history_entry("test_action", {"key": "val"})
        assert len(ctx.history) == 1

    def test_history_entry_has_action(self):
        ctx = _make_ctx()
        ctx.add_history_entry("my_action", {})
        assert ctx.history[0]["action"] == "my_action"

    def test_history_entry_has_details(self):
        ctx = _make_ctx()
        ctx.add_history_entry("act", {"x": 1})
        assert ctx.history[0]["details"]["x"] == 1

    def test_history_entry_has_timestamp(self):
        ctx = _make_ctx()
        ctx.add_history_entry("act", {})
        assert "timestamp" in ctx.history[0]

    def test_multiple_entries(self):
        ctx = _make_ctx()
        ctx.add_history_entry("a1", {})
        ctx.add_history_entry("a2", {})
        assert len(ctx.history) == 2


# ===========================================================================
# MCPContext.update_status
# ===========================================================================


class TestMCPContextUpdateStatus:
    def test_status_updated(self):
        ctx = _make_ctx()
        ctx.update_status(ContextStatus.COMPLETED)
        assert ctx.status == ContextStatus.COMPLETED

    def test_history_entry_added_on_status_change(self):
        ctx = _make_ctx()
        ctx.update_status(ContextStatus.FAILED, reason="error occurred")
        status_entries = [e for e in ctx.history if e["action"] == "status_change"]
        assert len(status_entries) == 1

    def test_reason_in_history_details(self):
        ctx = _make_ctx()
        ctx.update_status(ContextStatus.COMPLETED, reason="done")
        details = ctx.history[-1]["details"]
        assert details.get("reason") == "done"

    def test_status_change_without_reason(self):
        ctx = _make_ctx()
        ctx.update_status(ContextStatus.PENDING)
        assert len(ctx.history) >= 1


# ===========================================================================
# MCPContext.is_expired / extend_expiry
# ===========================================================================


class TestMCPContextExpiry:
    def test_not_expired_by_default(self):
        ctx = _make_ctx()
        assert ctx.is_expired() is False

    def test_expired_when_expires_at_in_past(self):
        ctx = _make_ctx()
        ctx.expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert ctx.is_expired() is True

    def test_extend_expiry_sets_future_time(self):
        ctx = _make_ctx()
        ctx.extend_expiry(hours=48)
        expected = datetime.utcnow() + timedelta(hours=48)
        diff = abs((ctx.expires_at - expected).total_seconds())
        assert diff < 5

    def test_extend_expiry_adds_history_entry(self):
        ctx = _make_ctx()
        ctx.extend_expiry(hours=12)
        history = [e for e in ctx.history if e["action"] == "expiry_extended"]
        assert len(history) == 1


# ===========================================================================
# MCPContextManager
# ===========================================================================


class TestMCPContextManager:
    def test_active_contexts_starts_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        assert mgr.active_contexts == {}

    def test_context_cache_starts_empty(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        assert mgr.context_cache == {}

    def test_create_context_returns_mcp_context(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        assert isinstance(ctx, MCPContext)

    def test_create_context_stored_in_active(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        assert ctx.id in mgr.active_contexts

    def test_get_context_returns_active(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        retrieved = mgr.get_context(ctx.id)
        assert retrieved is not None
        assert retrieved.id == ctx.id

    def test_get_context_returns_none_for_unknown(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        assert mgr.get_context("nonexistent-id") is None

    def test_update_context_changes_field(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        updated = mgr.update_context(ctx.id, {"subtask": "sub1"})
        assert updated.subtask == "sub1"

    def test_update_context_returns_none_for_unknown(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        result = mgr.update_context("unknown", {"subtask": "x"})
        assert result is None

    def test_delete_context_returns_true(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        assert mgr.delete_context(ctx.id) is True

    def test_delete_context_removes_from_active(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("user1", "task1", "intent1")
        mgr.delete_context(ctx.id)
        assert ctx.id not in mgr.active_contexts

    def test_delete_unknown_context_returns_false(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        assert mgr.delete_context("nonexistent") is False

    # ----- cache-hit path (line 222) ----------------------------------------

    def test_get_context_returns_cache_hit(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        del mgr.active_contexts[ctx.id]
        mgr.context_cache[ctx.id] = ctx
        result = mgr.get_context(ctx.id)
        assert result is ctx

    # ----- load-from-storage path (lines 227-228, 374-378) ------------------

    def test_get_context_loads_from_storage(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        ctx_id = ctx.id
        mgr.active_contexts.clear()
        mgr.context_cache.clear()
        result = mgr.get_context(ctx_id)
        assert result is not None
        assert result.id == ctx_id

    def test_load_context_direct_success(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        loaded = mgr._load_context(ctx.id)
        assert loaded is not None
        assert loaded.user == "u"

    def test_load_context_missing_file_returns_none(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        assert mgr._load_context("no-such-id") is None

    def test_load_context_bad_json_returns_none(self, tmp_path):
        storage = tmp_path / "ctx"
        storage.mkdir()
        (storage / "bad-id.json").write_text("not json {{{")
        mgr = MCPContextManager(storage_path=str(storage))
        result = mgr._load_context("bad-id")
        assert result is None

    # ----- delete cache path (line 289) -------------------------------------

    def test_delete_context_removes_from_cache(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        mgr.context_cache[ctx.id] = ctx
        mgr.delete_context(ctx.id)
        assert ctx.id not in mgr.context_cache

    # ----- list_contexts (lines 315-326) ------------------------------------

    def test_list_contexts_returns_all(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        mgr.create_context("a", "t", "i")
        mgr.create_context("b", "t", "i")
        assert len(mgr.list_contexts()) == 2

    def test_list_contexts_user_filter(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        mgr.create_context("alice", "t", "i")
        mgr.create_context("bob", "t", "i")
        result = mgr.list_contexts(user="alice")
        assert len(result) == 1
        assert result[0].user == "alice"

    def test_list_contexts_status_filter(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        ctx.status = ContextStatus.COMPLETED
        result = mgr.list_contexts(status=ContextStatus.COMPLETED)
        assert len(result) == 1

    def test_list_contexts_limit(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        for _ in range(5):
            mgr.create_context("u", "t", "i")
        assert len(mgr.list_contexts(limit=2)) == 2

    # ----- cleanup_expired_contexts (lines 335-347) -------------------------

    def test_cleanup_expired_removes_expired(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        ctx.expires_at = datetime.utcnow() - timedelta(seconds=1)
        count = mgr.cleanup_expired_contexts()
        assert count == 1
        assert ctx.id not in mgr.active_contexts

    def test_cleanup_expired_ignores_active(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        mgr.create_context("u", "t", "i")
        count = mgr.cleanup_expired_contexts()
        assert count == 0

    # ----- _persist_context exception path (lines 361-362) ------------------

    def test_persist_context_exception_does_not_raise(self, tmp_path, monkeypatch):
        import builtins
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        real_open = builtins.open

        def fail_open(path, *args, **kwargs):
            if str(tmp_path) in str(path) and "ctx" in str(path):
                raise OSError("disk full")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", fail_open)
        mgr._persist_context(ctx)  # must not raise

    # ----- _delete_persisted_context exception path (lines 394-395) ---------

    def test_delete_persisted_context_exception_does_not_raise(self, tmp_path, monkeypatch):
        import os as _os
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context("u", "t", "i")
        monkeypatch.setattr(_os, "remove", lambda p: (_ for _ in ()).throw(OSError("perm")))
        mgr._delete_persisted_context(ctx.id)  # must not raise

    # ----- module-level convenience functions (lines 412, 417) --------------

    def test_get_context_manager_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_ctx_mod, "_context_manager", None)
        monkeypatch.chdir(tmp_path)
        mgr1 = _ctx_mod.get_context_manager()
        mgr2 = _ctx_mod.get_context_manager()
        assert mgr1 is mgr2

    def test_create_context_convenience(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_ctx_mod, "_context_manager", None)
        monkeypatch.chdir(tmp_path)
        ctx = _ctx_mod.create_context("u2", "t2", "i2")
        assert isinstance(ctx, MCPContext)
        assert ctx.user == "u2"

    def test_get_context_convenience(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_ctx_mod, "_context_manager", None)
        monkeypatch.chdir(tmp_path)
        ctx = _ctx_mod.create_context("u3", "t3", "i3")
        retrieved = _ctx_mod.get_context(ctx.id)
        assert retrieved is not None
        assert retrieved.id == ctx.id


class TestContinuityLayerFoundations:
    def test_apply_state_delta_tracks_diff_and_vector_clock(self, tmp_path):
        mgr = MCPContextManager(storage_path=str(tmp_path / "ctx"))
        ctx = mgr.create_context(
            "agent-user",
            "task1",
            "intent1",
            code_state={"a": 1, "b": 2},
            metadata={"agent_id": "agent-1"},
        )

        diff = mgr.apply_state_delta(
            ctx.id,
            {"a": 1, "b": 3, "c": 4},
            device_id="device-a",
        )

        assert diff["updated"] == {"b": {"from": 2, "to": 3}}
        assert diff["added"] == {"c": 4}
        assert diff["removed"] == []

        refreshed = mgr.get_context(ctx.id)
        assert refreshed.vector_clock["device-a"] == 1

    def test_get_latest_context_for_agent_restores_from_persistence(self, tmp_path):
        storage = tmp_path / "ctx"
        mgr1 = MCPContextManager(storage_path=str(storage))
        ctx = mgr1.create_context(
            "agent-user",
            "task1",
            "intent1",
            code_state={"state": "initial"},
            metadata={"agent_id": "agent-restore"},
        )
        mgr1.apply_state_delta(ctx.id, {"state": "updated"}, device_id="device-a")
        mgr1.active_contexts.clear()
        mgr1.context_cache.clear()

        mgr2 = MCPContextManager(storage_path=str(storage))
        restored = mgr2.get_latest_context_for_agent("agent-restore")

        assert restored is not None
        assert restored.code_state["state"] == "updated"
        assert restored.vector_clock["device-a"] == 1
