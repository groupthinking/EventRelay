"""No live deployment: prove failures cannot become successful handoffs."""
import asyncio
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

spec = importlib.util.spec_from_file_location('deployment_handoff', Path(__file__).parents[2] / 'src/agents/mcp_tools/deployment_tool.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def tool():
    instance = object.__new__(module.DeploymentMCPTool)
    instance.github_token = None
    instance.vercel_token = None
    return instance

@pytest.mark.parametrize('failure_stage', [1, 2])
def test_git_failure_stops_handoff(tmp_path, failure_stage):
    results = [SimpleNamespace(returncode=0, stderr='') for _ in range(3)]
    results[failure_stage] = SimpleNamespace(returncode=1, stderr='private provider output')
    with patch.object(module.subprocess, 'run', side_effect=results) as run:
        result = asyncio.run(tool()._initialize_git(tmp_path))
    assert result['success'] is False
    assert run.call_count == failure_stage + 1
    assert 'private provider output' not in str(result)

@pytest.mark.parametrize('failure', [subprocess.TimeoutExpired('gh', 10), FileNotFoundError('gh')])
def test_identity_failure_never_fabricates_unknown_owner(failure):
    with patch.object(module.subprocess, 'run', side_effect=failure), pytest.raises(RuntimeError, match='identity lookup failed'):
        tool()._get_github_username()

def test_missing_deployment_url_is_not_success(tmp_path):
    with patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='completed', stderr='')):
        result = asyncio.run(tool()._deploy_to_vercel(tmp_path, 'example', None))
    assert result['success'] is False
    assert 'deployment_url' not in result


@pytest.mark.parametrize("vercel_result", [
    {"success": False, "error": "Vercel deployment timed out"},
    {"success": False, "error": "Vercel returned no verified deployment URL"},
])
def test_github_success_does_not_hide_vercel_failure(tmp_path, caplog, vercel_result):
    instance = tool()
    instance.github_token = "configured"
    instance.vercel_token = "configured"
    with patch.object(instance, "_initialize_git", new=AsyncMock(return_value={"success": True})), \
         patch.object(instance, "_create_github_repo", new=AsyncMock(return_value={
             "success": True, "repo_url": "https://github.com/example/project"
         })), \
         patch.object(instance, "_deploy_to_vercel", new=AsyncMock(return_value=vercel_result)):
        result = asyncio.run(instance.deploy_to_github_and_vercel(str(tmp_path)))

    assert result["status"] == "failed"
    assert result["github_deployed"] is True
    assert result["vercel_deployed"] is False
    assert result["errors"] == [{"stage": "vercel", "message": vercel_result["error"]}]
    assert any(
        getattr(record, "stage", None) == "vercel"
        and getattr(record, "reason", None) == "deployment_failed"
        for record in caplog.records
    )


@pytest.mark.parametrize("configured,vercel_result,expected", [
    (True, {"success": True, "deployment_url": "https://example.vercel.app"}, "success"),
    (False, None, "failed"),
])
def test_combined_handoff_requires_both_deployments(tmp_path, configured, vercel_result, expected):
    instance = tool()
    instance.github_token = "configured"
    instance.vercel_token = "configured" if configured else None
    with patch.object(instance, "_initialize_git", new=AsyncMock(return_value={"success": True})), \
         patch.object(instance, "_create_github_repo", new=AsyncMock(return_value={
             "success": True, "repo_url": "https://github.com/example/project"
         })), \
         patch.object(instance, "_deploy_to_vercel", new=AsyncMock(return_value=vercel_result)) as deploy:
        result = asyncio.run(instance.deploy_to_github_and_vercel(str(tmp_path)))

    assert result["status"] == expected
    assert result["vercel_deployed"] is configured
    assert deploy.await_count == int(configured)
