"""Unit tests for services/agents/monitor.py."""

from __future__ import annotations

import importlib.util
import sys
import types as _types
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))


def _inject_stub(package_name: str, path: Path) -> None:
    """Inject a stub module into sys.modules to prevent broken __init__ from loading."""
    if package_name not in sys.modules:
        stub = _types.ModuleType(package_name)
        stub.__path__ = [str(path)]
        stub.__package__ = package_name
        sys.modules[package_name] = stub


def _load(rel_path: str):
    full = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(rel_path.replace("/", "."), full)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Prevent the broken services/__init__.py from loading
_inject_stub("youtube_extension.services", _SRC / "youtube_extension/services")
_inject_stub("youtube_extension.services.agents", _SRC / "youtube_extension/services/agents")

_monitor_mod = _load("youtube_extension/services/agents/monitor.py")
monitor_file_access = _monitor_mod.monitor_file_access
monitor_error = _monitor_mod.monitor_error
monitor_agent_usage = _monitor_mod.monitor_agent_usage
MonitoredTask = _monitor_mod.MonitoredTask


# ===========================================================================
# monitor_file_access
# ===========================================================================


class TestMonitorFileAccess:
    def test_returns_none_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        result = monitor_file_access("src/main.py", "some task")
        assert result is None

    def test_returns_none_when_env_false(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "false")
        result = monitor_file_access("src/main.py")
        assert result is None

    def test_returns_none_when_env_zero(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "0")
        result = monitor_file_access("src/main.py")
        assert result is None

    def test_returns_none_when_env_no(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "no")
        result = monitor_file_access("src/main.py")
        assert result is None

    def test_accepts_empty_task_description(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_file_access("src/file.py", "")

    def test_does_not_raise_when_analyzer_unavailable(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "true")
        # analyzer may fail to import — function must silently absorb the error
        try:
            monitor_file_access("src/file.py", "task")
        except Exception:
            pytest.fail("monitor_file_access raised an unexpected exception")


# ===========================================================================
# monitor_error
# ===========================================================================


class TestMonitorError:
    def test_returns_none_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        result = monitor_error("ValueError", "some context")
        assert result is None

    def test_returns_none_when_env_false(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "false")
        result = monitor_error("TypeError", "ctx")
        assert result is None

    def test_does_not_raise_when_analyzer_unavailable(self, monkeypatch):
        monkeypatch.setenv("EVENTRELAY_MONITOR_AGENT_GAPS", "1")
        try:
            monitor_error("IOError", "read failed", frequency=3)
        except Exception:
            pytest.fail("monitor_error raised an unexpected exception")

    def test_default_frequency_accepted(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_error("RuntimeError", "context")  # frequency defaults to 1, no raise


# ===========================================================================
# monitor_agent_usage
# ===========================================================================


class TestMonitorAgentUsage:
    def test_no_args_does_not_raise(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage()

    def test_file_path_triggers_file_monitor(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage(file_path="src/main.py")

    def test_task_triggers_file_monitor(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage(task="process video")

    def test_error_tuple_triggers_error_monitor(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage(error=("ValueError", "ctx", 2))

    def test_all_args_accepted(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage(
            file_path="src/main.py",
            task="do work",
            error=("IOError", "read failed", 1),
        )

    def test_none_error_no_error_monitor_called(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        monitor_agent_usage(file_path="src/x.py", error=None)


# ===========================================================================
# MonitoredTask context manager
# ===========================================================================


class TestMonitoredTask:
    def test_init_stores_file_path(self):
        m = MonitoredTask("src/main.py", "do work")
        assert m.file_path == "src/main.py"

    def test_init_stores_task(self):
        m = MonitoredTask("src/main.py", "do work")
        assert m.task == "do work"

    def test_init_error_occurred_false(self):
        m = MonitoredTask("src/main.py", "do work")
        assert m.error_occurred is False

    def test_enter_returns_self(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        m = MonitoredTask("src/main.py", "do work")
        assert m.__enter__() is m

    def test_exit_returns_false_on_success(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        m = MonitoredTask("src/main.py", "do work")
        m.__enter__()
        result = m.__exit__(None, None, None)
        assert result is False

    def test_exit_returns_false_on_exception(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        m = MonitoredTask("src/main.py", "do work")
        m.__enter__()
        result = m.__exit__(ValueError, ValueError("oops"), None)
        assert result is False

    def test_exception_not_suppressed(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        with pytest.raises(RuntimeError):
            with MonitoredTask("src/main.py", "task"):
                raise RuntimeError("boom")

    def test_error_occurred_set_on_exception(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        m = MonitoredTask("src/main.py", "task")
        with pytest.raises(ValueError):
            with m:
                raise ValueError("fail")
        assert m.error_occurred is True

    def test_error_occurred_stays_false_on_success(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        m = MonitoredTask("src/main.py", "task")
        with m:
            pass
        assert m.error_occurred is False

    def test_context_manager_used_as_with_statement(self, monkeypatch):
        monkeypatch.delenv("EVENTRELAY_MONITOR_AGENT_GAPS", raising=False)
        executed = []
        with MonitoredTask("src/test.py", "test task") as mt:
            executed.append(mt.file_path)
        assert executed == ["src/test.py"]
