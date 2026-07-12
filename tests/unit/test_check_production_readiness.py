"""Tests for scripts/check_production_readiness.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "check_production_readiness.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "scripts.check_production_readiness", _SCRIPT_PATH
)
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["scripts.check_production_readiness"] = _MODULE
_SPEC.loader.exec_module(_MODULE)


def test_main_exits_nonzero_when_a_critical_check_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(_MODULE, "check_env_vars", lambda: False)
    monkeypatch.setattr(_MODULE, "check_cors_config", lambda: True)
    monkeypatch.setattr(_MODULE, "check_log_levels", lambda: True)
    monkeypatch.setattr(_MODULE, "check_security_middleware", lambda: True)
    monkeypatch.setattr(_MODULE, "check_dependencies", lambda: True)

    with pytest.raises(SystemExit, match="1"):
        _MODULE.main()
