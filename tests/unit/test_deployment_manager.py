"""Unit tests for backend/deployment_manager.py."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Stub optional heavy dependencies BEFORE importing deployment_manager so we
# can import the module in an environment where they may be absent, and also
# so we control their behaviour in tests.
# ---------------------------------------------------------------------------

# Stub skill_builder if not installed
if "skill_builder" not in sys.modules:
    _sb = types.ModuleType("skill_builder")
    _sb.SkillBuilder = None  # type: ignore[attr-defined]
    sys.modules["skill_builder"] = _sb

# Stub src.agents.github_deployment_agent
_agents_pkg = types.ModuleType("src")
_agents_sub = types.ModuleType("src.agents")
_agents_mod = types.ModuleType("src.agents.github_deployment_agent")
_agents_mod.GitHubDeploymentAgent = None  # type: ignore[attr-defined]
sys.modules.setdefault("src", _agents_pkg)
sys.modules.setdefault("src.agents", _agents_sub)
sys.modules.setdefault("src.agents.github_deployment_agent", _agents_mod)

# Now import the module under test
from youtube_extension.backend.deployment_manager import (  # noqa: E402
    DeploymentManager,
    get_deployment_manager,
    validate_deployment_environment,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_manager(**kwargs) -> DeploymentManager:
    """Create a DeploymentManager with all optional sub-systems disabled."""
    with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
         patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
         patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
        return DeploymentManager(**kwargs)


def _make_manager_without_github_token() -> DeploymentManager:
    """Create a manager with GITHUB_TOKEN stripped from the environment."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
        with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = DeploymentManager()
            mgr.github_token = None
            return mgr


# ===========================================================================
# DeploymentManager.__init__
# ===========================================================================


class TestDeploymentManagerInit:
    def test_no_token_env_fallback(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mgr = _make_manager()
        assert mgr.github_token is None

    def test_explicit_token_stored(self) -> None:
        mgr = _make_manager(github_token="mytoken")
        assert mgr.github_token == "mytoken"

    def test_env_token_used_when_no_explicit(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "envtoken")
        mgr = _make_manager()
        assert mgr.github_token == "envtoken"

    def test_explicit_token_overrides_env(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "envtoken")
        mgr = _make_manager(github_token="explicit")
        assert mgr.github_token == "explicit"

    def test_github_agent_none_without_agent_class(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mgr = _make_manager()
        assert mgr.github_agent is None

    def test_github_agent_initialized_when_token_and_class_available(self) -> None:
        mock_agent_cls = MagicMock(return_value=MagicMock())
        with patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", mock_agent_cls), \
             patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False):
            mgr = DeploymentManager(github_token="tok")
        mock_agent_cls.assert_called_once_with("tok")
        assert mgr.github_agent is not None

    def test_github_agent_gracefully_handles_init_error(self) -> None:
        mock_agent_cls = MagicMock(side_effect=RuntimeError("bad"))
        with patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", mock_agent_cls), \
             patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False):
            mgr = DeploymentManager(github_token="tok")
        assert mgr.github_agent is None

    def test_skill_builder_initialized_when_enabled(self) -> None:
        mock_sb_cls = MagicMock()
        mock_sb_instance = MagicMock()
        mock_sb_instance.get_stats.return_value = {"total_errors_handled": 5}
        mock_sb_cls.return_value = mock_sb_instance
        with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", True), \
             patch("youtube_extension.backend.deployment_manager.SkillBuilder", mock_sb_cls), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = DeploymentManager()
        assert mgr.skill_builder is mock_sb_instance

    def test_skill_builder_handles_init_error(self) -> None:
        mock_sb_cls = MagicMock(side_effect=RuntimeError("fail"))
        with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", True), \
             patch("youtube_extension.backend.deployment_manager.SkillBuilder", mock_sb_cls), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = DeploymentManager()
        assert mgr.skill_builder is None

    def test_ai_code_generator_initialized_when_available(self) -> None:
        mock_ai_cls = MagicMock(return_value=MagicMock())
        with patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", True), \
             patch("youtube_extension.backend.deployment_manager.AICodeGenerator", mock_ai_cls), \
             patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = DeploymentManager()
        assert mgr.ai_code_generator is not None

    def test_ai_code_generator_handles_init_error(self) -> None:
        mock_ai_cls = MagicMock(side_effect=RuntimeError("err"))
        with patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", True), \
             patch("youtube_extension.backend.deployment_manager.AICodeGenerator", mock_ai_cls), \
             patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = DeploymentManager()
        assert mgr.ai_code_generator is None


# ===========================================================================
# _generate_random_id
# ===========================================================================


class TestGenerateRandomId:
    def test_returns_string(self) -> None:
        mgr = _make_manager()
        rid = mgr._generate_random_id()
        assert isinstance(rid, str)

    def test_length_is_8(self) -> None:
        mgr = _make_manager()
        assert len(mgr._generate_random_id()) == 8

    def test_only_lowercase_alphanumeric(self) -> None:
        mgr = _make_manager()
        rid = mgr._generate_random_id()
        assert rid.isalnum()
        assert rid == rid.lower()

    def test_different_each_call(self) -> None:
        mgr = _make_manager()
        ids = {mgr._generate_random_id() for _ in range(20)}
        # With 36^8 combinations, we expect near-zero collision in 20 draws.
        assert len(ids) > 1


# ===========================================================================
# _generate_repo_name
# ===========================================================================


class TestGenerateRepoName:
    def _call(self, config):
        mgr = _make_manager()
        mock_loop = MagicMock()
        mock_loop.time.return_value = 12345.0
        with patch("asyncio.get_event_loop", return_value=mock_loop):
            return mgr._generate_repo_name(config)

    def test_sanitizes_special_chars(self) -> None:
        name = self._call({"title": "Hello! World#2"})
        # Only alphanumeric and hyphens (plus trailing timestamp)
        base = name.rsplit("-", 1)[0]
        assert re.match(r'^[a-z0-9\-]+$', base)

    def test_spaces_become_hyphens(self) -> None:
        name = self._call({"title": "My Cool App"})
        base = name.rsplit("-", 1)[0]
        assert " " not in base
        assert "my-cool-app" == base

    def test_max_30_chars_base(self) -> None:
        long_title = "a" * 100
        name = self._call({"title": long_title})
        base = name.rsplit("-", 1)[0]
        assert len(base) <= 30

    def test_missing_title_uses_fallback(self) -> None:
        name = self._call({})
        assert name.startswith("uvai-project-")

    def test_ends_with_numeric_timestamp(self) -> None:
        name = self._call({"title": "test"})
        suffix = name.rsplit("-", 1)[-1]
        assert suffix.isdigit()

    def test_empty_title_uses_fallback(self) -> None:
        name = self._call({"title": "!!!"})
        assert name.startswith("uvai-project-")


# ===========================================================================
# _generate_deployment_summary
# ===========================================================================


class TestGenerateDeploymentSummary:
    def setup_method(self):
        self.mgr = _make_manager()

    def test_empty_deployments(self) -> None:
        result = self.mgr._generate_deployment_summary({})
        assert result["total_deployments"] == 0
        assert result["successful_deployments"] == 0
        assert result["failed_deployments"] == 0
        assert result["skipped_deployments"] == 0
        assert result["primary_url"] is None

    def test_counts_success_correctly(self) -> None:
        deployments = {
            "vercel": {"status": "success", "url": "https://vercel.app"},
            "github": {"status": "success", "url": "https://github.com/u/r"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["total_deployments"] == 2
        assert result["successful_deployments"] == 2
        assert result["failed_deployments"] == 0

    def test_counts_failed_correctly(self) -> None:
        deployments = {
            "vercel": {"status": "failed"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["failed_deployments"] == 1

    def test_counts_skipped_correctly(self) -> None:
        deployments = {
            "netlify": {"status": "skipped"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["skipped_deployments"] == 1

    def test_primary_url_is_first_success(self) -> None:
        deployments = {
            "vercel": {"status": "success", "url": "https://first.vercel.app"},
            "netlify": {"status": "success", "url": "https://second.netlify.app"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["primary_url"] in ("https://first.vercel.app", "https://second.netlify.app")

    def test_no_url_in_success_not_added(self) -> None:
        deployments = {
            "github": {"status": "success"},  # No URL
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["deployment_urls"] == {}
        assert result["primary_url"] is None

    def test_deployment_urls_collected(self) -> None:
        deployments = {
            "vercel": {"status": "success", "url": "https://v.app"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["deployment_urls"]["vercel"] == "https://v.app"

    def test_mixed_statuses(self) -> None:
        deployments = {
            "vercel": {"status": "success", "url": "https://v.app"},
            "netlify": {"status": "failed"},
            "fly": {"status": "skipped"},
        }
        result = self.mgr._generate_deployment_summary(deployments)
        assert result["total_deployments"] == 3
        assert result["successful_deployments"] == 1
        assert result["failed_deployments"] == 1
        assert result["skipped_deployments"] == 1


# ===========================================================================
# _generate_deployment_urls
# ===========================================================================


class TestGenerateDeploymentUrls:
    def setup_method(self):
        self.mgr = _make_manager()

    def test_collects_urls_from_deployments(self) -> None:
        deployments = {
            "vercel": {"status": "success", "url": "https://v.app"},
            "github": {"status": "success", "url": "https://github.com/u/r"},
        }
        urls = self.mgr._generate_deployment_urls(deployments, {})
        assert urls["vercel"] == "https://v.app"
        assert urls["github"] == "https://github.com/u/r"

    def test_skips_entries_without_url(self) -> None:
        deployments = {
            "vercel": {"status": "failed"},
            "netlify": {"status": "success", "url": "https://n.app"},
        }
        urls = self.mgr._generate_deployment_urls(deployments, {})
        assert "vercel" not in urls
        assert urls["netlify"] == "https://n.app"

    def test_empty_deployments_returns_empty_dict(self) -> None:
        urls = self.mgr._generate_deployment_urls({}, {})
        assert urls == {}

    def test_project_config_not_required(self) -> None:
        urls = self.mgr._generate_deployment_urls({"p": {"url": "https://x.com"}}, {})
        assert urls["p"] == "https://x.com"


# ===========================================================================
# get_deployment_status
# ===========================================================================


class TestGetDeploymentStatus:
    async def test_returns_dict_with_deployment_id(self) -> None:
        mgr = _make_manager()
        result = await mgr.get_deployment_status("deploy-123")
        assert result["deployment_id"] == "deploy-123"

    async def test_status_is_completed(self) -> None:
        mgr = _make_manager()
        result = await mgr.get_deployment_status("any-id")
        assert result["status"] == "completed"

    async def test_has_message(self) -> None:
        mgr = _make_manager()
        result = await mgr.get_deployment_status("x")
        assert "message" in result


# ===========================================================================
# verify_project
# ===========================================================================


class TestVerifyProject:
    async def test_invalid_path_not_directory(self, tmp_path) -> None:
        mgr = _make_manager()
        not_a_dir = str(tmp_path / "no_such_dir")
        result = await mgr.verify_project(not_a_dir)
        assert result["passed"] is False
        assert "Invalid project path" in result["summary"]

    async def test_no_package_json_passes(self, tmp_path) -> None:
        """Projects without package.json are allowed through."""
        mgr = _make_manager()
        result = await mgr.verify_project(str(tmp_path))
        assert result["passed"] is True
        assert "skipping" in result["summary"].lower()

    async def test_npm_install_failure(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        mock_run = MagicMock()
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "npm ERR! peer dep not found\nerror: missing package"

        with patch("youtube_extension.backend.deployment_manager.subprocess.run", mock_run):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert "npm install failed" in result["summary"]
        assert result["npm_install"]["success"] is False

    async def test_npm_build_failure(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        install_result = MagicMock()
        install_result.returncode = 0
        install_result.stdout = "installed"
        install_result.stderr = ""

        build_result = MagicMock()
        build_result.returncode = 1
        build_result.stdout = "Build failed\nerror: type mismatch"
        build_result.stderr = "Error: cannot compile"

        mock_run = MagicMock(side_effect=[install_result, build_result])
        with patch("youtube_extension.backend.deployment_manager.subprocess.run", mock_run):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert "Build failed" in result["summary"]
        assert result["npm_build"]["success"] is False

    async def test_full_success_no_tsconfig(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        ok = MagicMock()
        ok.returncode = 0
        ok.stdout = "ok"
        ok.stderr = ""

        with patch("youtube_extension.backend.deployment_manager.subprocess.run", MagicMock(return_value=ok)):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is True
        assert result["summary"] == "All verification checks passed"

    async def test_full_success_with_tsconfig(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text("{}")
        mgr = _make_manager()

        ok = MagicMock()
        ok.returncode = 0
        ok.stdout = "ok"
        ok.stderr = ""

        with patch("youtube_extension.backend.deployment_manager.subprocess.run", MagicMock(return_value=ok)):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is True
        assert result["typescript"]["success"] is True

    async def test_ts_check_failure_does_not_fail_build(self, tmp_path) -> None:
        """TypeScript errors after a successful build should not fail the overall check."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text("{}")
        mgr = _make_manager()

        ok = MagicMock(returncode=0, stdout="ok", stderr="")
        ts_fail = MagicMock(returncode=1, stdout="error TS1234: bad type", stderr="")

        run_calls = [ok, ok, ts_fail]
        with patch("youtube_extension.backend.deployment_manager.subprocess.run", MagicMock(side_effect=run_calls)):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is True
        assert result["typescript"]["success"] is False

    async def test_timeout_returns_failure(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        with patch("youtube_extension.backend.deployment_manager.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["npm"], 180)):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert "timeout" in result["summary"].lower()

    async def test_npm_not_found_returns_failure(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        with patch("youtube_extension.backend.deployment_manager.subprocess.run",
                   side_effect=FileNotFoundError("npm not found")):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert "npm not found" in result["summary"]

    async def test_generic_exception_returns_failure(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        mgr = _make_manager()

        with patch("youtube_extension.backend.deployment_manager.subprocess.run",
                   side_effect=OSError("disk error")):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert "disk error" in result["summary"]

    async def test_skill_builder_used_on_build_errors(self, tmp_path) -> None:
        """When skill_builder is present and build fails, it queries for known patterns."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        mock_sb = MagicMock()
        mock_sb.find_matching_skill.return_value = {"resolution": "Try X", "id": "skill-1"}
        mgr = _make_manager()
        mgr.skill_builder = mock_sb

        install_ok = MagicMock(returncode=0, stdout="", stderr="")
        build_fail = MagicMock(
            returncode=1,
            stdout="Error: type mismatch in component",
            stderr="error: bad import",
        )
        with patch("youtube_extension.backend.deployment_manager.subprocess.run",
                   MagicMock(side_effect=[install_ok, build_fail])):
            result = await mgr.verify_project(str(tmp_path))

        assert result["passed"] is False
        assert mock_sb.find_matching_skill.called


# ===========================================================================
# verify_and_fix_project
# ===========================================================================


class TestVerifyAndFixProject:
    async def test_passes_on_first_attempt(self, tmp_path) -> None:
        mgr = _make_manager()

        passing_verification = {
            "passed": True,
            "npm_build": {"errors": []},
            "summary": "All verification checks passed",
        }
        mgr.verify_project = AsyncMock(return_value=passing_verification)

        result = await mgr.verify_and_fix_project(str(tmp_path))
        assert result["passed"] is True
        assert len(result["attempts"]) == 1

    async def test_retries_on_failure_then_passes(self, tmp_path) -> None:
        mgr = _make_manager()

        fail_v = {"passed": False, "npm_build": {"errors": ["err1"]}}
        pass_v = {"passed": True, "npm_build": {"errors": []}}

        mock_ai = AsyncMock()
        mock_ai.fix_build_errors = AsyncMock(return_value={"success": True, "fixed_files": ["a.ts"]})
        mgr.ai_code_generator = mock_ai

        mgr.verify_project = AsyncMock(side_effect=[fail_v, pass_v])

        result = await mgr.verify_and_fix_project(str(tmp_path), max_retries=1)
        assert result["passed"] is True
        assert len(result["attempts"]) == 2

    async def test_exhausts_retries_and_fails(self, tmp_path) -> None:
        mgr = _make_manager()

        fail_v = {"passed": False, "npm_build": {"errors": ["err1"]}, "summary": "failed"}
        mgr.verify_project = AsyncMock(return_value=fail_v)

        result = await mgr.verify_and_fix_project(str(tmp_path), max_retries=1)
        assert result["passed"] is False
        assert len(result["attempts"]) == 2  # initial + 1 retry

    async def test_no_ai_generator_stops_after_first_fail(self, tmp_path) -> None:
        mgr = _make_manager()
        mgr.ai_code_generator = None

        fail_v = {"passed": False, "npm_build": {"errors": ["err"]}, "summary": "failed"}
        mgr.verify_project = AsyncMock(return_value=fail_v)

        result = await mgr.verify_and_fix_project(str(tmp_path), max_retries=2)
        assert result["passed"] is False

    async def test_ai_fix_exception_handled(self, tmp_path) -> None:
        mgr = _make_manager()

        mock_ai = AsyncMock()
        mock_ai.fix_build_errors = AsyncMock(side_effect=RuntimeError("ai exploded"))
        mgr.ai_code_generator = mock_ai

        fail_v = {"passed": False, "npm_build": {"errors": ["err"]}, "summary": "failed"}
        mgr.verify_project = AsyncMock(return_value=fail_v)

        result = await mgr.verify_and_fix_project(str(tmp_path), max_retries=1)
        assert result["passed"] is False
        assert len(result["fixes_applied"]) == 1
        assert result["fixes_applied"][0]["success"] is False

    async def test_skill_success_tracked_after_fix(self, tmp_path) -> None:
        mock_sb = MagicMock()
        mock_sb.find_matching_skill.return_value = {"resolution": "fix X", "id": "skill-42"}

        mgr = _make_manager()
        mgr.skill_builder = mock_sb

        mock_ai = AsyncMock()
        mock_ai.fix_build_errors = AsyncMock(return_value={"success": True, "fixed_files": ["b.ts"]})
        mgr.ai_code_generator = mock_ai

        fail_v = {"passed": False, "npm_build": {"errors": ["err1"]}}
        pass_v = {"passed": True, "npm_build": {"errors": []}}
        mgr.verify_project = AsyncMock(side_effect=[fail_v, pass_v])

        result = await mgr.verify_and_fix_project(str(tmp_path), max_retries=1)
        assert result["passed"] is True
        mock_sb.apply_skill.assert_called()


# ===========================================================================
# deploy_project
# ===========================================================================


class TestDeployProject:
    def _patched_manager(self, github_token=None):
        if github_token is None:
            return _make_manager_without_github_token()
        return _make_manager(github_token=github_token)

    async def test_verification_failure_returns_failed_status(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": False,
            "attempts": [{"attempt": 1, "passed": False, "errors": []}],
            "fixes_applied": [],
            "final_verification": {"npm_build": {"errors": ["type error"]}},
        })

        result = await mgr.deploy_project(
            str(tmp_path),
            {"title": "Test"},
            {"target": "vercel"},
        )
        assert result["status"] == "failed"
        assert "Build verification failed" in result["errors"][0]

    async def test_no_github_token_adds_error(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })

        mock_adapter_result = {"status": "success", "url": "https://vercel.app"}
        with patch("youtube_extension.backend.deployment_manager._adapter_deploy",
                   new=AsyncMock(return_value=mock_adapter_result)):
            result = await mgr.deploy_project(
                str(tmp_path),
                {"title": "Test"},
                {"target": "vercel"},
            )

        assert "GitHub token not configured" in result["errors"]

    async def test_github_deployment_called_when_token_set(self, tmp_path) -> None:
        mgr = self._patched_manager(github_token="tok")
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_github = AsyncMock(return_value={"status": "success", "url": "https://github.com/u/r", "repository": {}})
        mock_adapter_result = {"status": "success", "url": "https://vercel.app"}
        mgr._deploy_to_github = mock_github

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy",
                   new=AsyncMock(return_value=mock_adapter_result)):
            result = await mgr.deploy_project(
                str(tmp_path),
                {"title": "Test"},
                {"target": "vercel"},
            )

        mock_github.assert_awaited_once()

    async def test_vercel_target_uses_adapter(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(return_value={"status": "success", "url": "https://v.app"})

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})

        mock_adapter.assert_awaited_once()
        assert "vercel" in result["deployments"]

    async def test_netlify_target_uses_adapter(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(return_value={"status": "success", "url": "https://n.app"})

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "netlify"})

        assert "netlify" in result["deployments"]

    async def test_fly_target_uses_adapter(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(return_value={"status": "success", "url": "https://fly.app"})

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "fly"})

        assert "fly" in result["deployments"]

    async def test_github_target_no_extra_hosting(self, tmp_path) -> None:
        mgr = self._patched_manager(github_token="tok")
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mgr._deploy_to_github = AsyncMock(return_value={
            "status": "success",
            "url": "https://github.com/u/r",
            "repository": {"owner": "u", "repo_name": "r"},
        })

        result = await mgr.deploy_project(str(tmp_path), {}, {"target": "github"})
        assert "github" in result["deployments"]
        # No extra hosting key beyond 'github'
        assert "vercel" not in result["deployments"]
        assert "netlify" not in result["deployments"]

    async def test_github_pages_target(self, tmp_path) -> None:
        mgr = self._patched_manager(github_token="tok")
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mgr._deploy_to_github = AsyncMock(return_value={
            "status": "success",
            "url": "https://github.com/u/r",
            "repository": {"owner": "u", "repo_name": "r", "html_url": "https://github.com/u/r"},
        })
        mgr._deploy_to_github_pages = AsyncMock(return_value={
            "status": "simulated",
            "url": "https://u.github.io/r",
        })

        result = await mgr.deploy_project(str(tmp_path), {}, {"target": "github_pages"})
        assert "github_pages" in result["deployments"]

    async def test_unknown_target_adds_error(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })

        result = await mgr.deploy_project(str(tmp_path), {}, {"target": "unknown_platform"})
        assert any("Unknown deployment target" in e for e in result["errors"])

    async def test_success_status_when_no_errors(self, tmp_path) -> None:
        # Use a token so the "GitHub token not configured" error is NOT added.
        mgr = self._patched_manager(github_token="tok")
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(return_value={"status": "success", "url": "https://v.app"})
        mock_github = AsyncMock(return_value={"status": "success", "url": "https://github.com/u/r", "repository": {}})
        mgr._deploy_to_github = mock_github

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})

        assert result["status"] == "success"

    async def test_partial_success_when_deployments_fail(self, tmp_path) -> None:
        # Use a token so the only "error" source is the failed deployment, not missing token.
        mgr = self._patched_manager(github_token="tok")
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_github = AsyncMock(return_value={"status": "success", "url": "https://github.com/u/r", "repository": {}})
        mgr._deploy_to_github = mock_github
        mock_adapter = AsyncMock(return_value={"status": "failed", "error": "some error"})

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})

        # has_errors=False (no errors list entries), has_failed_deployments=True → partial_success
        assert result["status"] == "partial_success"

    async def test_adapter_exception_results_in_failed_status(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(side_effect=RuntimeError("network down"))

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})

        assert result["deployments"]["vercel"]["status"] == "failed"

    async def test_result_has_deployment_id(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={"passed": False, "attempts": [], "fixes_applied": [], "final_verification": {"npm_build": {"errors": []}}})

        result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})
        assert result["deployment_id"].startswith("uvai_")

    async def test_exception_in_deploy_returns_failed(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(side_effect=RuntimeError("unexpected"))

        result = await mgr.deploy_project(str(tmp_path), {}, {"target": "vercel"})
        assert result["status"] == "failed"
        assert "unexpected" in result["errors"][0]

    async def test_environment_from_deployment_config_passed_to_adapter(self, tmp_path) -> None:
        mgr = self._patched_manager()
        mgr.verify_and_fix_project = AsyncMock(return_value={
            "passed": True,
            "attempts": [],
            "fixes_applied": [],
            "final_verification": {},
        })
        mock_adapter = AsyncMock(return_value={"status": "success", "url": "https://v.app"})

        with patch("youtube_extension.backend.deployment_manager._adapter_deploy", new=mock_adapter):
            await mgr.deploy_project(
                str(tmp_path),
                {},
                {"target": "vercel", "environment": {"MY_VAR": "hello"}},
            )

        # Third positional arg is the env dict
        call_kwargs = mock_adapter.await_args
        env_arg = call_kwargs[0][3]  # positional args: target, path, config, env
        assert env_arg.get("MY_VAR") == "hello"


# ===========================================================================
# _deploy_to_github
# ===========================================================================


class TestDeployToGithub:
    async def test_no_token_returns_failed(self) -> None:
        mgr = _make_manager_without_github_token()
        result = await mgr._deploy_to_github("/some/path", {})
        assert result["status"] == "failed"
        assert "token" in result["error"].lower()

    async def test_success_structure(self) -> None:
        mgr = _make_manager(github_token="tok")
        repo_result = {
            "repo_name": "my-repo",
            "owner": "user",
            "full_name": "user/my-repo",
            "clone_url": "https://github.com/user/my-repo.git",
            "html_url": "https://github.com/user/my-repo",
        }
        upload_result = {"files_uploaded": 3, "file_list": ["a.ts", "b.ts", "c.ts"]}

        mgr._create_github_repository = AsyncMock(return_value=repo_result)
        mgr._upload_to_github = AsyncMock(return_value=upload_result)

        result = await mgr._deploy_to_github("/path", {"title": "My App"})
        assert result["status"] == "success"
        assert result["url"] == "https://github.com/user/my-repo"
        assert result["repository"] == repo_result

    async def test_exception_returns_failed(self) -> None:
        mgr = _make_manager(github_token="tok")
        mgr._create_github_repository = AsyncMock(side_effect=RuntimeError("API error"))

        result = await mgr._deploy_to_github("/path", {})
        assert result["status"] == "failed"
        assert "API error" in result["error"]


# ===========================================================================
# _deploy_to_github_pages
# ===========================================================================


class TestDeployToGithubPages:
    async def test_no_github_result_fails(self) -> None:
        mgr = _make_manager()
        result = await mgr._deploy_to_github_pages("/path", {}, {"status": "failed"})
        assert result["status"] == "failed"

    async def test_missing_owner_fails(self) -> None:
        mgr = _make_manager()
        result = await mgr._deploy_to_github_pages(
            "/path", {},
            {"status": "success", "repository": {"repo_name": "r"}}
        )
        assert result["status"] == "failed"

    async def test_missing_repo_name_fails(self) -> None:
        mgr = _make_manager()
        result = await mgr._deploy_to_github_pages(
            "/path", {},
            {"status": "success", "repository": {"owner": "u"}}
        )
        assert result["status"] == "failed"

    async def test_success_returns_simulated(self) -> None:
        mgr = _make_manager()
        result = await mgr._deploy_to_github_pages(
            "/path", {},
            {
                "status": "success",
                "repository": {"owner": "myuser", "repo_name": "myrepo", "html_url": "https://github.com/myuser/myrepo"},
            }
        )
        assert result["status"] == "simulated"
        assert "myuser.github.io/myrepo" in result["url"]

    async def test_returns_instructions(self) -> None:
        mgr = _make_manager()
        result = await mgr._deploy_to_github_pages(
            "/path", {},
            {
                "status": "success",
                "repository": {"owner": "u", "repo_name": "r", "html_url": "https://github.com/u/r"},
            }
        )
        assert isinstance(result["instructions"], list)
        assert len(result["instructions"]) > 0


# ===========================================================================
# _deploy_to_vercel / _deploy_to_netlify (deprecated stubs)
# ===========================================================================


class TestDeprecatedStubs:
    async def test_deploy_to_vercel_raises_not_implemented(self) -> None:
        mgr = _make_manager()
        with pytest.raises(NotImplementedError):
            await mgr._deploy_to_vercel()

    async def test_deploy_to_netlify_raises_not_implemented(self) -> None:
        mgr = _make_manager()
        with pytest.raises(NotImplementedError):
            await mgr._deploy_to_netlify()


# ===========================================================================
# Module-level helpers
# ===========================================================================


class TestGetDeploymentManager:
    def test_returns_deployment_manager_instance(self) -> None:
        mgr = get_deployment_manager()
        assert isinstance(mgr, DeploymentManager)

    def test_passes_token(self) -> None:
        with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = get_deployment_manager(github_token="mytoken")
        assert mgr.github_token == "mytoken"

    def test_no_token_gives_none(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with patch("youtube_extension.backend.deployment_manager.SKILL_LEARNING_ENABLED", False), \
             patch("youtube_extension.backend.deployment_manager.AI_CODE_GENERATOR_AVAILABLE", False), \
             patch("youtube_extension.backend.deployment_manager.GitHubDeploymentAgent", None):
            mgr = get_deployment_manager()
        assert mgr.github_token is None


class TestValidateDeploymentEnvironment:
    def test_returns_dict_with_expected_keys(self, monkeypatch) -> None:
        for var in ["VERCEL_TOKEN", "NETLIFY_AUTH_TOKEN", "FLY_API_TOKEN", "GITHUB_TOKEN"]:
            monkeypatch.delenv(var, raising=False)
        result = validate_deployment_environment()
        assert "overall_valid" in result
        assert "platform_validations" in result
        assert "missing_tokens" in result

    def test_all_platforms_present(self, monkeypatch) -> None:
        for var in ["VERCEL_TOKEN", "NETLIFY_AUTH_TOKEN", "FLY_API_TOKEN", "GITHUB_TOKEN"]:
            monkeypatch.delenv(var, raising=False)
        result = validate_deployment_environment()
        validations = result["platform_validations"]
        for platform in DeploymentManager.SUPPORTED_PLATFORMS:
            assert platform in validations
        assert "github" in validations

    def test_missing_tokens_listed(self, monkeypatch) -> None:
        for var in ["VERCEL_TOKEN", "NETLIFY_AUTH_TOKEN", "FLY_API_TOKEN", "GITHUB_TOKEN"]:
            monkeypatch.delenv(var, raising=False)
        result = validate_deployment_environment()
        assert len(result["missing_tokens"]) > 0

    def test_overall_valid_true_when_all_tokens_present(self, monkeypatch) -> None:
        monkeypatch.setenv("VERCEL_TOKEN", "vt")
        monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "nt")
        monkeypatch.setenv("FLY_API_TOKEN", "ft")
        monkeypatch.setenv("GITHUB_TOKEN", "gt")
        result = validate_deployment_environment()
        assert result["overall_valid"] is True

    def test_overall_valid_false_when_tokens_missing(self, monkeypatch) -> None:
        for var in ["VERCEL_TOKEN", "NETLIFY_AUTH_TOKEN", "FLY_API_TOKEN", "GITHUB_TOKEN"]:
            monkeypatch.delenv(var, raising=False)
        result = validate_deployment_environment()
        assert result["overall_valid"] is False


# ===========================================================================
# _create_github_repository
# ===========================================================================


def _make_aiohttp_ctx(response_mock: MagicMock) -> MagicMock:
    """Wrap a response mock in an async context manager."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_aiohttp_session(
    get_responses: list | None = None,
    post_responses: list | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Build a mock aiohttp.ClientSession context manager.

    get_responses / post_responses are lists of response mocks returned in
    order for each call.
    """
    get_iter = iter(get_responses or [])
    post_iter = iter(post_responses or [])

    session_mock = MagicMock()
    session_mock.get = MagicMock(side_effect=lambda *a, **kw: _make_aiohttp_ctx(next(get_iter)))
    session_mock.post = MagicMock(side_effect=lambda *a, **kw: _make_aiohttp_ctx(next(post_iter)))

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_mock)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm, session_mock


class TestCreateGithubRepository:
    async def test_no_token_raises(self) -> None:
        mgr = _make_manager_without_github_token()
        with pytest.raises(Exception, match="token"):
            await mgr._create_github_repository("repo", {})

    async def test_user_info_failure_raises(self) -> None:
        mgr = _make_manager(github_token="tok")

        user_resp = MagicMock()
        user_resp.status = 401
        user_resp.text = AsyncMock(return_value="Unauthorized")

        session_cm, _ = _make_aiohttp_session(get_responses=[user_resp])
        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            with pytest.raises(Exception, match="Failed to get GitHub user info"):
                await mgr._create_github_repository("repo", {})

    async def test_successful_creation(self) -> None:
        mgr = _make_manager(github_token="tok")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "testuser"})

        repo_resp = MagicMock()
        repo_resp.status = 201
        repo_resp.json = AsyncMock(return_value={
            "full_name": "testuser/my-repo",
            "clone_url": "https://github.com/testuser/my-repo.git",
            "html_url": "https://github.com/testuser/my-repo",
        })

        session_cm, _ = _make_aiohttp_session(
            get_responses=[user_resp],
            post_responses=[repo_resp],
        )
        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._create_github_repository("my-repo", {"title": "Test"})

        assert result["repo_name"] == "my-repo"
        assert result["owner"] == "testuser"
        assert result["clone_url"] == "https://github.com/testuser/my-repo.git"

    async def test_repo_already_exists_422_fetches_existing(self) -> None:
        mgr = _make_manager(github_token="tok")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "testuser"})

        repo_422 = MagicMock()
        repo_422.status = 422

        existing_resp = MagicMock()
        existing_resp.status = 200
        existing_resp.json = AsyncMock(return_value={
            "full_name": "testuser/my-repo",
            "clone_url": "https://github.com/testuser/my-repo.git",
            "html_url": "https://github.com/testuser/my-repo",
        })

        # GET is called twice: user info, then existing repo fetch
        session_cm, _ = _make_aiohttp_session(
            get_responses=[user_resp, existing_resp],
            post_responses=[repo_422],
        )
        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._create_github_repository("my-repo", {})

        assert result["owner"] == "testuser"

    async def test_creation_error_status_raises(self) -> None:
        mgr = _make_manager(github_token="tok")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "testuser"})

        error_resp = MagicMock()
        error_resp.status = 500
        error_resp.text = AsyncMock(return_value="Internal Server Error")

        session_cm, _ = _make_aiohttp_session(
            get_responses=[user_resp],
            post_responses=[error_resp],
        )
        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            with pytest.raises(Exception, match="Failed to create GitHub repository"):
                await mgr._create_github_repository("my-repo", {})


# ===========================================================================
# _upload_to_github
# ===========================================================================


class TestUploadToGithub:
    async def test_no_token_raises(self) -> None:
        mgr = _make_manager_without_github_token()
        with pytest.raises(Exception, match="token"):
            await mgr._upload_to_github("/path", "repo")

    async def test_uploads_files(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        (tmp_path / "index.ts").write_text("const x = 1;")
        (tmp_path / "style.css").write_text("body {}")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "u"})

        put_resp = MagicMock()
        put_resp.status = 201
        put_resp.text = AsyncMock(return_value="")

        session_mock = MagicMock()
        get_cm = _make_aiohttp_ctx(user_resp)
        session_mock.get = MagicMock(return_value=get_cm)
        put_cm = MagicMock()
        put_cm.__aenter__ = AsyncMock(return_value=put_resp)
        put_cm.__aexit__ = AsyncMock(return_value=False)
        session_mock.put = MagicMock(return_value=put_cm)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "my-repo")

        assert result["files_uploaded"] == 2
        assert len(result["file_list"]) == 2

    async def test_skips_excluded_dirs(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "dep.js").write_text("module.exports = {}")
        (tmp_path / "app.ts").write_text("export const x = 1;")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "u"})

        put_resp = MagicMock()
        put_resp.status = 201
        put_resp.text = AsyncMock(return_value="")

        session_mock = MagicMock()
        session_mock.get = MagicMock(return_value=_make_aiohttp_ctx(user_resp))
        put_cm = MagicMock()
        put_cm.__aenter__ = AsyncMock(return_value=put_resp)
        put_cm.__aexit__ = AsyncMock(return_value=False)
        session_mock.put = MagicMock(return_value=put_cm)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "repo")

        # Only app.ts should be uploaded, not node_modules/dep.js
        assert result["files_uploaded"] == 1
        assert "app.ts" in result["file_list"][0]

    async def test_skips_dotfiles(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        (tmp_path / ".env").write_text("SECRET=abc")
        (tmp_path / "main.ts").write_text("export const y = 2;")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "u"})

        put_resp = MagicMock()
        put_resp.status = 201
        put_resp.text = AsyncMock(return_value="")

        session_mock = MagicMock()
        session_mock.get = MagicMock(return_value=_make_aiohttp_ctx(user_resp))
        put_cm = MagicMock()
        put_cm.__aenter__ = AsyncMock(return_value=put_resp)
        put_cm.__aexit__ = AsyncMock(return_value=False)
        session_mock.put = MagicMock(return_value=put_cm)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "repo")

        assert result["files_uploaded"] == 1
        assert all(not Path(f).name.startswith(".") for f in result["file_list"])

    async def test_upload_failure_warned_but_not_raised(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")
        (tmp_path / "app.ts").write_text("export const z = 3;")

        user_resp = MagicMock()
        user_resp.status = 200
        user_resp.json = AsyncMock(return_value={"login": "u"})

        put_fail = MagicMock()
        put_fail.status = 500
        put_fail.text = AsyncMock(return_value="server error")

        session_mock = MagicMock()
        session_mock.get = MagicMock(return_value=_make_aiohttp_ctx(user_resp))
        put_cm = MagicMock()
        put_cm.__aenter__ = AsyncMock(return_value=put_fail)
        put_cm.__aexit__ = AsyncMock(return_value=False)
        session_mock.put = MagicMock(return_value=put_cm)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "repo")

        # Upload failed but no exception raised; count stays 0
        assert result["files_uploaded"] == 0


# ===========================================================================
# SUPPORTED_PLATFORMS class attribute
# ===========================================================================


class TestSupportedPlatforms:
    def test_includes_vercel(self) -> None:
        assert "vercel" in DeploymentManager.SUPPORTED_PLATFORMS

    def test_includes_netlify(self) -> None:
        assert "netlify" in DeploymentManager.SUPPORTED_PLATFORMS

    def test_includes_fly(self) -> None:
        assert "fly" in DeploymentManager.SUPPORTED_PLATFORMS
