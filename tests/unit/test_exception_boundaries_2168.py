"""Issue #2168: narrowed exception handling in deploy handoff and agent orchestrator.

Every failure here is simulated (patched subprocess / store / agents): no
subprocess, network or database is touched.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import ArgumentError, OperationalError

from youtube_extension.services.agents.adapters import agent_orchestrator as orch_mod
from youtube_extension.services.agents.adapters.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationResult,
)
from youtube_extension.services.agents.base_agent import BaseAgent

REPO_ROOT = Path(__file__).parents[2]
DEPLOY_PATH = REPO_ROOT / "src/agents/mcp_tools/deployment_tool.py"
ORCH_PATH = REPO_ROOT / "src/youtube_extension/services/agents/adapters/agent_orchestrator.py"

_spec = importlib.util.spec_from_file_location("deployment_tool_2168", DEPLOY_PATH)
deploy_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy_mod)

DEPLOY_LOGGER = deploy_mod.logger.name
SECRET = "vercel-secret-token-2168"


def _tool(github_token=None, vercel_token=None):
    instance = object.__new__(deploy_mod.DeploymentMCPTool)
    instance.github_token = github_token
    instance.vercel_token = vercel_token
    return instance


def _step_records(caplog, stage):
    return [r for r in caplog.records if getattr(r, "stage", None) == stage and getattr(r, "error_class", None)]


# ---------------------------------------------------------------------------
# deployment_tool.py
# ---------------------------------------------------------------------------


def test_git_init_missing_cli_is_logged_with_stage_class_and_traceback(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    with patch.object(deploy_mod.subprocess, "run", side_effect=FileNotFoundError("git")):
        result = asyncio.run(_tool()._initialize_git(tmp_path))
    assert result["success"] is False
    assert result["error_class"] == "FileNotFoundError"
    (record,) = _step_records(caplog, "git_init")
    assert record.error_class == "FileNotFoundError"
    assert "Traceback (most recent call last)" in record.traceback


def test_git_init_timeout_is_logged(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    with patch.object(deploy_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 30)):
        result = asyncio.run(_tool()._initialize_git(tmp_path))
    assert result == {"success": False, "error": "Git initialization timed out", "error_class": "TimeoutExpired"}
    assert _step_records(caplog, "git_init")[0].error_class == "TimeoutExpired"


def test_unexpected_error_in_git_step_raises(tmp_path):
    with patch.object(deploy_mod.subprocess, "run", side_effect=ValueError("bug")), pytest.raises(ValueError):
        asyncio.run(_tool()._initialize_git(tmp_path))


def test_github_step_subprocess_error_is_logged(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    with patch.object(deploy_mod.subprocess, "run", side_effect=subprocess.SubprocessError("boom")):
        result = asyncio.run(_tool(github_token="gh-token")._create_github_repo(tmp_path, "demo", None))
    assert result["success"] is False
    assert result["error_class"] == "SubprocessError"
    assert _step_records(caplog, "github")[0].error_class == "SubprocessError"


def test_vercel_timeout_is_logged_without_leaking_token(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    timeout = subprocess.TimeoutExpired(["vercel", "--prod", "--yes", "--token", SECRET], 300)
    with patch.object(deploy_mod.subprocess, "run", side_effect=timeout):
        result = asyncio.run(_tool(vercel_token=SECRET)._deploy_to_vercel(tmp_path, "demo", None))
    assert result["success"] is False
    assert result["error_class"] == "TimeoutExpired"
    (record,) = _step_records(caplog, "vercel")
    assert "Traceback" in record.traceback
    assert SECRET not in caplog.text
    assert SECRET not in str(result)


def test_owner_lookup_failure_is_caught_and_reported(tmp_path, caplog):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    created = SimpleNamespace(returncode=0, stdout="created", stderr="")
    tool = _tool(github_token="gh-token")
    with patch.object(deploy_mod.subprocess, "run", return_value=created), patch.object(
        tool, "_get_github_username", side_effect=deploy_mod.GitHubIdentityError("GitHub identity lookup failed")
    ):
        result = asyncio.run(tool._create_github_repo(tmp_path, "demo", None))
    assert result["success"] is False
    assert result["error_class"] == "GitHubIdentityError"
    assert "repo_url" not in result
    assert _step_records(caplog, "github_identity")


def test_owner_lookup_unexpected_error_raises(tmp_path):
    created = SimpleNamespace(returncode=0, stdout="created", stderr="")
    tool = _tool(github_token="gh-token")
    with patch.object(deploy_mod.subprocess, "run", return_value=created), patch.object(
        tool, "_get_github_username", side_effect=KeyError("bug")
    ), pytest.raises(KeyError):
        asyncio.run(tool._create_github_repo(tmp_path, "demo", None))


def test_identity_error_is_runtime_error_subclass():
    assert issubclass(deploy_mod.GitHubIdentityError, RuntimeError)
    with patch.object(deploy_mod.subprocess, "run", side_effect=OSError("gh")), pytest.raises(
        deploy_mod.GitHubIdentityError
    ):
        _tool(github_token="gh-token")._get_github_username()


def test_entrypoint_boundary_returns_error_class_and_logs_not_stderr(tmp_path, caplog, capsys):
    caplog.set_level(logging.ERROR, logger=DEPLOY_LOGGER)
    with patch.object(deploy_mod.subprocess, "run", side_effect=ValueError("unexpected")):
        result = asyncio.run(_tool().deploy_to_github_and_vercel(str(tmp_path)))
    assert result["status"] == "error"
    assert result["error_class"] == "ValueError"
    (record,) = _step_records(caplog, "deploy_entrypoint")
    assert "Traceback" in record.traceback
    assert capsys.readouterr().err == ""


def test_failed_step_error_class_reaches_deploy_result(tmp_path):
    (tmp_path / ".git").mkdir()  # git init already done
    with patch.object(deploy_mod.subprocess, "run", side_effect=FileNotFoundError("gh")):
        result = asyncio.run(_tool(github_token="gh-token").deploy_to_github_and_vercel(str(tmp_path)))
    assert result["status"] == "failed"
    github_errors = [e for e in result["errors"] if e["stage"] == "github"]
    assert github_errors[0]["error_class"] == "FileNotFoundError"


# ---------------------------------------------------------------------------
# agent_orchestrator.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure",
    [
        OperationalError("connect", {}, Exception("refused")),
        ArgumentError("bad url"),
        ModuleNotFoundError("No module named 'psycopg'"),
        PermissionError("read-only path"),
    ],
    ids=["db", "bad-url", "missing-driver", "file"],
)
def test_shared_store_expected_failures_degrade_with_log(failure, caplog):
    caplog.set_level(logging.WARNING, logger="agent_orchestrator")
    with patch.object(orch_mod, "SharedSQLStateStore", side_effect=failure):
        orch = AgentOrchestrator(database_url="sqlite:///unused.db")
    assert orch._shared_state is None
    (record,) = [r for r in caplog.records if getattr(r, "error_class", None)]
    assert record.error_class == type(failure).__name__
    assert record.exc_info is not None


def test_shared_store_unexpected_failure_raises():
    with patch.object(orch_mod, "SharedSQLStateStore", side_effect=ValueError("bug")), pytest.raises(ValueError):
        AgentOrchestrator(database_url="sqlite:///unused.db")


async def test_create_agent_boundary_logs_agent_class_traceback(caplog):
    caplog.set_level(logging.ERROR, logger="agent_orchestrator")

    class Exploding:
        def __init__(self, config=None):
            raise ValueError("ctor failed")

    orch = AgentOrchestrator()
    orch.register_agent_type("exploding", Exploding)
    assert await orch.get_agent("exploding") is None
    (record,) = [r for r in caplog.records if getattr(r, "agent", None) == "exploding"]
    assert record.error_class == "ValueError"
    assert record.exc_info is not None


async def test_execute_task_boundary_returns_failure_and_logs(caplog):
    caplog.set_level(logging.ERROR, logger="agent_orchestrator")
    agent = MagicMock(spec=BaseAgent)
    agent.name = "video_master"
    agent.run = MagicMock(side_effect=ValueError("sync crash"))
    orch = AgentOrchestrator()
    orch._agents["video_master"] = agent
    result = await orch.execute_task("content_generation", {})
    assert isinstance(result, OrchestrationResult)
    assert result.success is False
    assert result.errors == ["Orchestration failed: sync crash"]
    (record,) = [r for r in caplog.records if getattr(r, "task_type", None) == "content_generation"]
    assert record.error_class == "ValueError"
    assert record.exc_info is not None


async def test_execute_single_boundary_returns_error_dict_and_logs(caplog):
    caplog.set_level(logging.ERROR, logger="agent_orchestrator")
    agent = MagicMock(spec=BaseAgent)
    agent.name = "worker"
    agent.run = AsyncMock(side_effect=RuntimeError("run crashed"))
    orch = AgentOrchestrator()
    orch._agents["worker"] = agent
    assert await orch.execute_single("worker", {"event": 1}) == {"error": "run crashed"}
    (record,) = [r for r in caplog.records if getattr(r, "agent", None) == "worker"]
    assert record.error_class == "RuntimeError"
    assert record.exc_info is not None


async def test_message_delivery_boundary_keeps_message_and_logs(caplog):
    caplog.set_level(logging.WARNING, logger="agent_orchestrator")
    recipient = MagicMock()
    recipient.receive_context = AsyncMock(side_effect=KeyError("missing"))
    orch = AgentOrchestrator()
    orch._agents["receiver"] = recipient
    msg = await orch.send_a2a_message("sender", "receiver", {"k": "v"})
    assert msg.recipient == "receiver"
    assert orch.get_a2a_log(conversation_id=msg.conversation_id)
    (record,) = [r for r in caplog.records if getattr(r, "agent", None) == "receiver"]
    assert record.error_class == "KeyError"
    assert record.exc_info is not None


# ---------------------------------------------------------------------------
# Guard: no new unmarked broad handlers in the two narrowed files
# ---------------------------------------------------------------------------

_MARKER = "# exception-boundary:"


@pytest.mark.parametrize("path,expected", [(DEPLOY_PATH, 1), (ORCH_PATH, 4)], ids=["deploy", "orchestrator"])
def test_broad_handlers_are_counted_and_marked(path, expected):
    broad = [
        line
        for line in path.read_text().splitlines()
        if re.match(r"^\s*except\s*(:|\(?\s*(Exception|BaseException)\b)", line)
    ]
    assert len(broad) == expected, broad
    unmarked = [line for line in broad if _MARKER not in line]
    assert unmarked == []
    markers = [line for line in path.read_text().splitlines() if _MARKER in line]
    assert len(markers) == expected
    for line in markers:
        assert len(line.split(_MARKER, 1)[1].strip()) > 10, f"boundary needs a reason: {line}"
