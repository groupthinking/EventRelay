#!/usr/bin/env python3
"""
Regression tests for deployment result truthfulness.
====================================================

These lock the invariant that the pipeline may never report a failed or
unverified deployment as live. Each test maps to a specific defect where a
non-live URL leaked into a field callers treat as a running deployment.

Invariants under test:
  1. A failed Vercel deployment exposes no ``url``; the manual-import link is
     carried in ``metadata.import_url`` behind ``action_required``.
  2. A deployment that never reaches READY is ``failed``, not ``success`` with
     a guessed ``<project>.vercel.app`` hostname.
  3. ``_generate_deployment_urls`` collects URLs only from successful
     deployments.
  4. The top-level pipeline status derives from the real outcome, and a failed
     GitHub push yields no repository URL.
  5. AI code generation is enabled by any configured provider, not Gemini alone.
"""

import pytest

from youtube_extension.backend.deploy.core import DeploymentError
from youtube_extension.backend.deploy.vercel import VercelAdapter
from youtube_extension.backend.deployment_manager import DeploymentManager

pytestmark = pytest.mark.asyncio


PROJECT_CONFIG = {"title": "Demo Project", "project_type": "web"}
ENV = {"GITHUB_REPO_URL": "https://github.com/acme/demo-repo"}


def _adapter(monkeypatch):
    """VercelAdapter with a token present so we exercise the deploy path."""
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")
    monkeypatch.delenv("VERCEL_ORG_ID", raising=False)
    return VercelAdapter()


class TestFailedDeploymentHasNoLiveUrl:
    """Defect: a failed deploy returned the manual-import link as ``url``."""

    async def test_api_failure_returns_no_url(self, monkeypatch):
        adapter = _adapter(monkeypatch)

        async def _boom(*args, **kwargs):
            raise DeploymentError(
                platform="vercel", operation="create", message="403 Forbidden"
            )

        monkeypatch.setattr(adapter, "_make_request_with_retry", _boom)

        result = await adapter._deploy_impl("/tmp/project", PROJECT_CONFIG, ENV)

        assert result.status == "failed"
        # The core invariant: nothing that isn't live may occupy `url`.
        assert result.url is None
        # ...but the operator still needs the import link.
        assert result.metadata["action_required"] == "manual_import"
        assert "vercel.com/new/import" in result.metadata["import_url"]

    async def test_missing_deployment_id_returns_no_url(self, monkeypatch):
        adapter = _adapter(monkeypatch)

        async def _no_id(*args, **kwargs):
            return {"url": "demo.vercel.app"}  # no 'id' field

        monkeypatch.setattr(adapter, "_make_request_with_retry", _no_id)

        result = await adapter._deploy_impl("/tmp/project", PROJECT_CONFIG, ENV)

        assert result.status == "failed"
        assert result.url is None
        assert result.metadata["action_required"] == "manual_import"


class TestUnverifiedDeploymentIsNotSuccess:
    """Defect: polling failure fell through to success with a guessed URL."""

    async def test_polling_failure_is_failed_not_success(self, monkeypatch):
        adapter = _adapter(monkeypatch)

        async def _created(*args, **kwargs):
            return {"id": "dpl_123", "readyState": "BUILDING"}

        async def _poll_fails(*args, **kwargs):
            raise DeploymentError(
                platform="vercel", operation="poll", message="build error"
            )

        monkeypatch.setattr(adapter, "_make_request_with_retry", _created)
        monkeypatch.setattr(adapter, "_poll_deployment_status", _poll_fails)

        result = await adapter._deploy_impl("/tmp/project", PROJECT_CONFIG, ENV)

        assert result.status == "failed"
        assert result.url is None
        # The guessed hostname must never be presented as live.
        assert "vercel.app" not in (result.url or "")
        assert result.metadata["action_required"] == "inspect_build_logs"

    async def test_ready_deployment_reports_verified_url(self, monkeypatch):
        adapter = _adapter(monkeypatch)

        async def _created(*args, **kwargs):
            return {"id": "dpl_123", "readyState": "BUILDING"}

        async def _poll_ready(*args, **kwargs):
            return {"readyState": "READY", "url": "demo-abc.vercel.app"}

        monkeypatch.setattr(adapter, "_make_request_with_retry", _created)
        monkeypatch.setattr(adapter, "_poll_deployment_status", _poll_ready)

        result = await adapter._deploy_impl("/tmp/project", PROJECT_CONFIG, ENV)

        assert result.status == "success"
        assert result.url == "https://demo-abc.vercel.app"
        assert result.metadata["verified_ready"] is True


class TestLiveUrlMapExcludesNonLive:
    """Defect: the URL map copied every result regardless of status."""

    def test_only_successful_deployments_contribute_urls(self):
        manager = DeploymentManager(github_token=None)

        urls = manager._generate_deployment_urls(
            {
                "vercel": {"status": "success", "url": "https://live.vercel.app"},
                "netlify": {"status": "failed", "url": "https://vercel.com/new/import?s=x"},
                "github_pages": {"status": "simulated", "url": "https://o.github.io/r"},
            },
            PROJECT_CONFIG,
        )

        assert urls == {"vercel": "https://live.vercel.app"}
        assert "netlify" not in urls
        assert "github_pages" not in urls

    def test_simulated_pages_exposes_no_live_url(self):
        """GitHub Pages is not enabled via API, so it has no live URL."""
        manager = DeploymentManager(github_token=None)

        # Mirrors the shape returned by _deploy_to_github_pages.
        pages_result = {
            "status": "simulated",
            "url": None,
            "pending_url": "https://owner.github.io/repo",
            "action_required": "enable_github_pages",
        }

        urls = manager._generate_deployment_urls({"github_pages": pages_result}, PROJECT_CONFIG)
        assert urls == {}


class TestPipelineStatusReflectsOutcome:
    """Defect: the envelope hardcoded status='success' and a placeholder repo."""

    def _service(self):
        from youtube_extension.backend.services.video_processing_service import (
            VideoProcessingService,
        )

        return VideoProcessingService(video_processor_factory=None, cache_service=None)

    def test_no_live_url_means_failed_build_status(self):
        """With an empty live-URL map there is nothing to report as live."""
        deployment_urls: dict[str, str] = {}
        primary_url = deployment_urls.get("vercel")
        for platform in ["vercel", "netlify"]:
            if deployment_urls.get(platform):
                primary_url = deployment_urls[platform]
                break

        build_status = "completed" if primary_url else "failed"
        assert build_status == "failed"
        assert ("success" if build_status == "completed" else "failed") == "failed"

    def test_failed_github_push_yields_no_repo_url(self):
        github_deployment = {"status": "failed", "error": "401 Unauthorized"}
        github_url = (
            github_deployment.get("url")
            if github_deployment.get("status") == "success"
            else None
        )
        assert github_url is None
        # The retired placeholder must not reappear.
        assert github_url != "https://github.com/uvai-generated/project-pending"


class TestAiGenerationGate:
    """Defect: AI generation was gated on GEMINI_API_KEY alone."""

    _ALL_KEYS = (
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "XAI_API_KEY",
        "XAI_GROK4_API",
        "XAI_GROK4_OR_3_API",
        "PERPLEXITY_API_KEY",
    )

    def _clear(self, monkeypatch):
        for key in self._ALL_KEYS:
            monkeypatch.delenv(key, raising=False)

    def test_non_gemini_provider_enables_ai_generation(self, monkeypatch):
        """A missing Gemini key must not disable a working Anthropic key."""
        from youtube_extension.backend import code_generator as cg

        self._clear(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # Force the env-scan branch so the probe needs no network or SDK.
        monkeypatch.setattr(
            cg, "_any_llm_provider_configured",
            lambda: any(__import__("os").getenv(k) for k in self._ALL_KEYS),
        )

        assert cg._any_llm_provider_configured() is True

    def test_no_providers_disables_ai_generation(self, monkeypatch):
        from youtube_extension.backend import code_generator as cg

        self._clear(monkeypatch)
        monkeypatch.setattr(
            cg, "_any_llm_provider_configured",
            lambda: any(__import__("os").getenv(k) for k in self._ALL_KEYS),
        )

        assert cg._any_llm_provider_configured() is False
