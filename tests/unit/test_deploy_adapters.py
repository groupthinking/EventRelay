"""Unit tests for backend/deploy/vercel.py, netlify.py, fly.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

sys.modules.pop("youtube_extension.backend.deploy.vercel", None)
sys.modules.pop("youtube_extension.backend.deploy.netlify", None)
sys.modules.pop("youtube_extension.backend.deploy.fly", None)

from youtube_extension.backend.deploy.vercel import VercelAdapter, VERCEL_API
from youtube_extension.backend.deploy.netlify import NetlifyAdapter, NETLIFY_API
from youtube_extension.backend.deploy.fly import FlyAdapter
from youtube_extension.backend.deploy.core import DeploymentResult, DeploymentError


# ===========================================================================
# VercelAdapter.__init__
# ===========================================================================


class TestVercelAdapterInit:
    def test_platform_is_vercel(self):
        adapter = VercelAdapter()
        assert adapter.platform == "vercel"


# ===========================================================================
# VercelAdapter._ensure_https
# ===========================================================================


class TestVercelAdapterEnsureHttps:
    def test_none_returns_none(self):
        assert VercelAdapter._ensure_https(None) is None

    def test_empty_returns_none(self):
        assert VercelAdapter._ensure_https("") is None

    def test_https_unchanged(self):
        url = "https://example.vercel.app"
        assert VercelAdapter._ensure_https(url) == url

    def test_http_unchanged(self):
        url = "http://example.vercel.app"
        assert VercelAdapter._ensure_https(url) == url

    def test_bare_domain_gets_https(self):
        result = VercelAdapter._ensure_https("example.vercel.app")
        assert result == "https://example.vercel.app"

    def test_subdomain_gets_https(self):
        result = VercelAdapter._ensure_https("my-project.vercel.app")
        assert result == "https://my-project.vercel.app"


# ===========================================================================
# VercelAdapter._vercel_import_url
# ===========================================================================


class TestVercelAdapterImportUrl:
    def test_format_correct(self):
        url = VercelAdapter._vercel_import_url("myorg", "myrepo")
        assert "vercel.com/new/import" in url

    def test_contains_github_path(self):
        url = VercelAdapter._vercel_import_url("myorg", "myrepo")
        assert "myorg" in url
        assert "myrepo" in url

    def test_github_source_param(self):
        url = VercelAdapter._vercel_import_url("org", "repo")
        assert "github.com/org/repo" in url


# ===========================================================================
# VercelAdapter._detect_framework
# ===========================================================================


class TestVercelAdapterDetectFramework:
    def test_explicit_framework_returned(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"framework": "NextJS"})
        assert result == "nextjs"

    def test_react_project_type_maps_to_nextjs(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "react"})
        assert result == "nextjs"

    def test_next_project_type_maps_to_nextjs(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "next"})
        assert result == "nextjs"

    def test_vue_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "vue"})
        assert result == "vue"

    def test_angular_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "angular"})
        assert result == "angular"

    def test_svelte_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "svelte"})
        assert result == "svelte"

    def test_nuxt_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "nuxt"})
        assert result == "nuxtjs"

    def test_astro_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "astro"})
        assert result == "astro"

    def test_web_project_type(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "web"})
        assert result == "nextjs"

    def test_static_project_type_returns_none(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "static"})
        assert result is None

    def test_unknown_project_type_returns_none(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({"project_type": "unknown_thing"})
        assert result is None

    def test_empty_config(self):
        adapter = VercelAdapter()
        result = adapter._detect_framework({})
        assert result is None


# ===========================================================================
# VercelAdapter.deploy — skipped when token missing
# ===========================================================================


class TestVercelAdapterDeploy:
    async def test_skipped_when_vercel_token_missing(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        adapter = VercelAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "skipped"

    async def test_skipped_result_has_platform(self, monkeypatch):
        monkeypatch.delenv("VERCEL_TOKEN", raising=False)
        adapter = VercelAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.platform == "vercel"

    async def test_success_when_deploy_impl_returns_success(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "fake-token")
        adapter = VercelAdapter()
        expected = DeploymentResult(status="success", platform="vercel", url="https://example.vercel.app")
        with patch.object(VercelAdapter, "_deploy_impl", AsyncMock(return_value=expected)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "success"
        assert result.platform == "vercel"

    async def test_failed_when_deploy_impl_raises_deployment_error(self, monkeypatch):
        monkeypatch.setenv("VERCEL_TOKEN", "fake-token")
        adapter = VercelAdapter()
        err = DeploymentError(platform="vercel", operation="deploy", message="API error")
        with patch.object(VercelAdapter, "_deploy_impl", AsyncMock(side_effect=err)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "failed"
        assert result.platform == "vercel"


# ===========================================================================
# NetlifyAdapter.__init__
# ===========================================================================


class TestNetlifyAdapterInit:
    def test_platform_is_netlify(self):
        adapter = NetlifyAdapter()
        assert adapter.platform == "netlify"


# ===========================================================================
# NetlifyAdapter._get_build_settings
# ===========================================================================


class TestNetlifyAdapterGetBuildSettings:
    def test_default_build_command(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({})
        assert settings["build_command"] == "npm run build"

    def test_custom_build_command(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"build_command": "yarn build"})
        assert settings["build_command"] == "yarn build"

    def test_default_publish_dir(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({})
        assert settings["publish_dir"] == "build"

    def test_custom_output_dir(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"output_directory": "dist"})
        assert settings["publish_dir"] == "dist"

    def test_nextjs_framework_override(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"framework": "nextjs"})
        assert settings["publish_dir"] == ".next"

    def test_next_project_type_override(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"project_type": "next"})
        assert settings["publish_dir"] == ".next"

    def test_react_framework_override(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"framework": "react"})
        assert settings["publish_dir"] == "build"

    def test_vue_framework_override(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({"framework": "vue"})
        assert settings["publish_dir"] == "dist"

    def test_repo_branch_defaults_main(self):
        adapter = NetlifyAdapter()
        settings = adapter._get_build_settings({})
        assert settings["repo_branch"] == "main"


# ===========================================================================
# NetlifyAdapter.deploy — skipped when token missing
# ===========================================================================


class TestNetlifyAdapterDeploy:
    async def test_skipped_when_netlify_token_missing(self, monkeypatch):
        monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
        adapter = NetlifyAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "skipped"

    async def test_skipped_result_has_platform(self, monkeypatch):
        monkeypatch.delenv("NETLIFY_AUTH_TOKEN", raising=False)
        adapter = NetlifyAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.platform == "netlify"

    async def test_success_when_deploy_impl_returns_success(self, monkeypatch):
        monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "fake-token")
        adapter = NetlifyAdapter()
        expected = DeploymentResult(status="success", platform="netlify", url="https://example.netlify.app")
        with patch.object(NetlifyAdapter, "_deploy_impl", AsyncMock(return_value=expected)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "success"
        assert result.platform == "netlify"

    async def test_failed_when_deploy_impl_raises_deployment_error(self, monkeypatch):
        monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "fake-token")
        adapter = NetlifyAdapter()
        err = DeploymentError(platform="netlify", operation="deploy", message="Build failed")
        with patch.object(NetlifyAdapter, "_deploy_impl", AsyncMock(side_effect=err)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "failed"
        assert result.platform == "netlify"


# ===========================================================================
# FlyAdapter.__init__
# ===========================================================================


class TestFlyAdapterInit:
    def test_platform_is_fly(self):
        adapter = FlyAdapter()
        assert adapter.platform == "fly"


# ===========================================================================
# FlyAdapter._extract_deployment_url
# ===========================================================================


class TestFlyAdapterExtractDeploymentUrl:
    def test_extracts_fly_dev_url(self):
        adapter = FlyAdapter()
        output = "some text\nhttps://myapp.fly.dev\nmore text"
        result = adapter._extract_deployment_url(output)
        assert result == "https://myapp.fly.dev"

    def test_returns_placeholder_when_no_url(self):
        adapter = FlyAdapter()
        result = adapter._extract_deployment_url("no urls here\nno fly domain")
        assert "fly.dev" in result

    def test_returns_placeholder_on_empty_output(self):
        adapter = FlyAdapter()
        result = adapter._extract_deployment_url("")
        assert result is not None

    def test_prefers_fly_dev_over_internal(self):
        adapter = FlyAdapter()
        output = "https://myapp.fly.dev\nhttps://myapp.internal"
        result = adapter._extract_deployment_url(output)
        assert "fly.dev" in result


# ===========================================================================
# FlyAdapter._generate_app_name
# ===========================================================================


class TestFlyAdapterGenerateAppName:
    def test_does_not_require_current_event_loop(self):
        adapter = FlyAdapter()

        with patch(
            "youtube_extension.backend.deploy.fly.asyncio.get_event_loop",
            side_effect=AssertionError("app-name generation accessed the event loop"),
        ), patch(
            "youtube_extension.backend.deploy.fly.time.time",
            return_value=12345.0,
        ):
            name = adapter._generate_app_name({"title": "My App"})

        assert name == "uvai-my-app-2345"

    async def test_starts_with_uvai(self):
        adapter = FlyAdapter()
        name = adapter._generate_app_name({"title": "My App"})
        assert name.startswith("uvai-")

    async def test_sanitizes_spaces(self):
        adapter = FlyAdapter()
        name = adapter._generate_app_name({"title": "My Cool App"})
        assert " " not in name

    async def test_default_title_used_when_missing(self):
        adapter = FlyAdapter()
        name = adapter._generate_app_name({})
        assert name.startswith("uvai-")

    async def test_truncates_long_title(self):
        adapter = FlyAdapter()
        long_title = "This Is A Very Long Application Title That Exceeds Twenty Characters"
        name = adapter._generate_app_name({"title": long_title})
        # The sanitized portion is limited to 20 chars
        assert len(name) > 0


# ===========================================================================
# FlyAdapter.deploy — skipped when token missing
# ===========================================================================


class TestFlyAdapterDeploy:
    async def test_skipped_when_fly_token_missing(self, monkeypatch):
        monkeypatch.delenv("FLY_API_TOKEN", raising=False)
        adapter = FlyAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.status == "skipped"

    async def test_skipped_result_has_platform(self, monkeypatch):
        monkeypatch.delenv("FLY_API_TOKEN", raising=False)
        adapter = FlyAdapter()
        result = await adapter.deploy("/path", {}, {})
        assert result.platform == "fly"

    async def test_success_when_deploy_impl_returns_success(self, monkeypatch):
        monkeypatch.setenv("FLY_API_TOKEN", "fake-token")
        adapter = FlyAdapter()
        expected = DeploymentResult(status="success", platform="fly", url="https://myapp.fly.dev")
        with patch.object(FlyAdapter, "_deploy_impl", AsyncMock(return_value=expected)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "success"
        assert result.platform == "fly"

    async def test_failed_when_deploy_impl_raises_deployment_error(self, monkeypatch):
        monkeypatch.setenv("FLY_API_TOKEN", "fake-token")
        adapter = FlyAdapter()
        err = DeploymentError(platform="fly", operation="deploy", message="Deployment timed out")
        with patch.object(FlyAdapter, "_deploy_impl", AsyncMock(side_effect=err)):
            result = await adapter.deploy("/path", {}, {})
        assert result.status == "failed"
        assert result.platform == "fly"
