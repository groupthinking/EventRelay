"""Unit tests for backend/deploy/core.py."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

sys.modules.pop("youtube_extension.backend.deploy.core", None)

from youtube_extension.backend.deploy.core import (
    BaseDeploymentAdapter,
    DeploymentError,
    DeploymentResult,
    EnvironmentValidator,
    RetryConfig,
)

# ===========================================================================
# DeploymentError
# ===========================================================================


class TestDeploymentError:
    def test_platform_stored(self):
        e = DeploymentError(platform="vercel", operation="deploy", message="failed")
        assert e.platform == "vercel"

    def test_operation_stored(self):
        e = DeploymentError(platform="netlify", operation="build", message="err")
        assert e.operation == "build"

    def test_message_stored(self):
        e = DeploymentError(platform="fly", operation="deploy", message="timeout")
        assert e.message == "timeout"

    def test_details_defaults_empty(self):
        e = DeploymentError(platform="p", operation="o", message="m")
        assert e.details == {}

    def test_recoverable_defaults_false(self):
        e = DeploymentError(platform="p", operation="o", message="m")
        assert e.recoverable is False

    def test_recoverable_can_be_set_true(self):
        e = DeploymentError(platform="p", operation="o", message="m", recoverable=True)
        assert e.recoverable is True

    def test_details_can_be_provided(self):
        e = DeploymentError(platform="p", operation="o", message="m", details={"code": 404})
        assert e.details["code"] == 404

    def test_is_exception(self):
        e = DeploymentError(platform="p", operation="o", message="m")
        assert isinstance(e, Exception)


# ===========================================================================
# DeploymentResult
# ===========================================================================


class TestDeploymentResult:
    def test_status_required(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.status == "success"

    def test_platform_required(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.platform == "vercel"

    def test_deployment_id_defaults_none(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.deployment_id is None

    def test_url_defaults_none(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.url is None

    def test_build_log_url_defaults_none(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.build_log_url is None

    def test_error_message_defaults_none(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.error_message is None

    def test_metadata_defaults_empty(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.metadata == {}

    def test_timestamps_defaults_empty(self):
        r = DeploymentResult(status="success", platform="vercel")
        assert r.timestamps == {}

    def test_all_fields_can_be_set(self):
        r = DeploymentResult(
            status="success",
            platform="vercel",
            deployment_id="dep-123",
            url="https://example.vercel.app",
            error_message=None,
            metadata={"branch": "main"},
        )
        assert r.deployment_id == "dep-123"
        assert r.url == "https://example.vercel.app"
        assert r.metadata["branch"] == "main"


# ===========================================================================
# EnvironmentValidator.validate_for_platform
# ===========================================================================


class TestEnvironmentValidatorValidate:
    def test_valid_when_token_present(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert result["valid"] is True

    def test_invalid_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert result["valid"] is False

    def test_missing_required_listed(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert "VERCEL_TOKEN" in result["missing_required"]

    def test_token_masked_when_present(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert result["available_tokens"]["VERCEL_TOKEN"] == "***masked***"

    def test_template_placeholder_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "[VERCEL_TOKEN]")
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert result["valid"] is False

    def test_optional_missing_listed_separately(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        monkeypatch.delenv("VERCEL_PROJECT_NAME", raising=False)
        monkeypatch.delenv("VERCEL_ORG_ID", raising=False)
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert "VERCEL_PROJECT_NAME" in result["missing_optional"]
        assert result["valid"] is True  # optional doesn't fail validation

    def test_unknown_platform_returns_valid_empty(self, monkeypatch):
        result = EnvironmentValidator.validate_for_platform("unknown_platform")
        assert result["valid"] is True
        assert result["missing_required"] == []

    def test_netlify_token_check(self, monkeypatch):
        monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "netlify_tok")
        result = EnvironmentValidator.validate_for_platform("netlify")
        assert result["valid"] is True

    def test_fly_token_check(self, monkeypatch):
        monkeypatch.setenv("FLY_API_TOKEN", "fly_tok")
        result = EnvironmentValidator.validate_for_platform("fly")
        assert result["valid"] is True

    def test_github_token_check(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "gh_tok")
        result = EnvironmentValidator.validate_for_platform("github")
        assert result["valid"] is True

    def test_result_keys_present(self, monkeypatch):
        result = EnvironmentValidator.validate_for_platform("vercel")
        assert "valid" in result
        assert "missing_required" in result
        assert "missing_optional" in result
        assert "available_tokens" in result


# ===========================================================================
# EnvironmentValidator.get_token
# ===========================================================================


class TestEnvironmentValidatorGetToken:
    def test_returns_value_when_present(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "secret123")
        assert EnvironmentValidator.get_token("MY_TOKEN") == "secret123"

    def test_returns_none_when_missing(self, monkeypatch):
        monkeypatch.delenv("MY_TOKEN", raising=False)
        assert EnvironmentValidator.get_token("MY_TOKEN") is None

    def test_returns_none_for_template_placeholder(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "[MY_TOKEN]")
        assert EnvironmentValidator.get_token("MY_TOKEN") is None

    def test_returns_none_for_empty_string(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "")
        assert EnvironmentValidator.get_token("MY_TOKEN") is None


# ===========================================================================
# RetryConfig
# ===========================================================================


class TestRetryConfig:
    def test_default_max_attempts(self):
        cfg = RetryConfig()
        assert cfg.max_attempts == 3

    def test_default_base_delay(self):
        cfg = RetryConfig()
        assert cfg.base_delay == 1.0

    def test_default_max_delay(self):
        cfg = RetryConfig()
        assert cfg.max_delay == 60.0

    def test_default_backoff_factor(self):
        cfg = RetryConfig()
        assert cfg.backoff_factor == 2.0

    def test_default_retryable_status_codes(self):
        cfg = RetryConfig()
        assert 429 in cfg.retryable_status_codes
        assert 500 in cfg.retryable_status_codes
        assert 503 in cfg.retryable_status_codes

    def test_custom_max_attempts(self):
        cfg = RetryConfig(max_attempts=5)
        assert cfg.max_attempts == 5

    def test_custom_retryable_codes(self):
        cfg = RetryConfig(retryable_status_codes=[502])
        assert cfg.retryable_status_codes == [502]


# ===========================================================================
# BaseDeploymentAdapter.deploy (via concrete subclass)
# ===========================================================================


class _FakeAdapter(BaseDeploymentAdapter):
    def __init__(self, platform="vercel", result=None, raise_err=None):
        super().__init__(platform)
        self._result = result or DeploymentResult(status="success", platform=platform, url="https://x.com")
        self._raise = raise_err

    async def _deploy_impl(self, project_path, project_config, env):
        if self._raise:
            raise self._raise
        return self._result


class TestBaseDeploymentAdapterDeploy:
    async def test_skipped_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        adapter = _FakeAdapter(platform="vercel")
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "skipped"

    async def test_skipped_result_has_error_message(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        adapter = _FakeAdapter(platform="vercel")
        result = await adapter.deploy("/path", {}, {})
        assert "VERCEL_TOKEN" in result.error_message

    async def test_success_when_token_present(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(platform="vercel")
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "success"

    async def test_timestamps_added_on_success(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(platform="vercel")
        result = await adapter.deploy("/path", {}, {})
        assert "completed" in result.timestamps
        assert "duration_seconds" in result.timestamps

    async def test_deployment_error_returns_failed(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(
            platform="vercel",
            raise_err=DeploymentError(platform="vercel", operation="deploy", message="build failed")
        )
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "failed"

    async def test_deployment_error_message_propagated(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(
            platform="vercel",
            raise_err=DeploymentError(platform="vercel", operation="deploy", message="build failed")
        )
        result = await adapter.deploy("/path", {}, {})
        assert result.error_message == "build failed"

    async def test_unexpected_error_returns_failed(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(platform="vercel", raise_err=RuntimeError("unexpected"))
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "failed"

    async def test_unexpected_error_message_includes_text(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "tok_real")
        adapter = _FakeAdapter(platform="vercel", raise_err=RuntimeError("disk full"))
        result = await adapter.deploy("/path", {}, {})
        assert "disk full" in result.error_message

    async def test_platform_stored_on_result(self, monkeypatch):
        monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "tok")
        adapter = _FakeAdapter(
            platform="netlify",
            result=DeploymentResult(status="success", platform="netlify")
        )
        result = await adapter.deploy("/path", {}, {})
        assert result.platform == "netlify"
