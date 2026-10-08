"""No live deployment: prove failures cannot become successful handoffs."""
import asyncio
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
