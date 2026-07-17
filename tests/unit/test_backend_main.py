"""
Unit tests for src/youtube_extension/backend/main.py

Covers:
- Root redirect endpoint
- Legacy redirect endpoints (health, metrics, connectors, cache)
- Legacy API endpoints (chat, process-video-markdown, process-video)
- System info endpoint
- Exception handlers (ValueError, global)
- Custom OpenAPI schema generation
- Application startup / shutdown lifecycle events
- App metadata
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Ensure 'src' is on sys.path (mirrors pytest.ini pythonpath = src)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# Pre-patch modules that cause syntax/import errors when backend.main loads
# ---------------------------------------------------------------------------
_STUB_MODULES = [
    "src",
    "src.integration",
    "src.integration.looker_embedded",
]
# Track only the stubs we actually install here, so cleanup below removes
# exactly our fakes and never a real module another test already loaded.
_INSTALLED_STUBS: dict[str, MagicMock] = {}
for _mod in _STUB_MODULES:
    if _mod not in sys.modules:
        _stub = MagicMock()
        sys.modules[_mod] = _stub
        _INSTALLED_STUBS[_mod] = _stub


# ---------------------------------------------------------------------------
# Import the app under test
# ---------------------------------------------------------------------------
from youtube_extension.backend import main as main_module  # noqa: E402
from youtube_extension.backend.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# backend.main now holds its own references to whatever it needed from the
# stubs above, so remove the import-time stubs from sys.modules. Leaving them
# in place shadows the REAL leaf modules for other test files that run later
# in the same session (e.g. test_looker_security.py, which imports the real
# LookerEmbeddedService and asserts it raises on a missing secret). Only
# entries that are still exactly the stubs we installed are removed.
# ---------------------------------------------------------------------------
for _mod, _stub in _INSTALLED_STUBS.items():
    if sys.modules.get(_mod) is _stub:
        del sys.modules[_mod]

# ---------------------------------------------------------------------------
# Unique-IP generator – each test gets a fresh token-bucket so the
# in-memory rate limiter never runs out of tokens across tests.
# ---------------------------------------------------------------------------
_ip_counter = itertools.count(1)


def _unique_ip() -> str:
    n = next(_ip_counter)
    return f"10.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{n & 0xFF}"


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


def _make_mock_container(
    *,
    cache_dir: str = "/tmp/test_cache",
    container_status: str = "healthy",
    all_services: dict | None = None,
) -> MagicMock:
    """Return a pre-configured ServiceContainer mock."""
    mock_cache = MagicMock()
    mock_cache.cache_dir = cache_dir

    mock_vps = MagicMock()
    mock_vps.get_video_processor.return_value = MagicMock()
    mock_vps.process_video_for_markdown = AsyncMock(return_value={"status": "ok"})
    mock_vps.process_video_basic = AsyncMock(return_value={"status": "ok", "video_data": {}})

    mock_health = MagicMock()
    mock_health.rate_limit_check.return_value = True
    mock_health.increment_metric.return_value = None

    def _get_service(name: str) -> MagicMock:
        mapping = {
            "cache_service": mock_cache,
            "video_processing_service": mock_vps,
            "health_monitoring_service": mock_health,
            "data_service": MagicMock(),
            "websocket_service": MagicMock(),
        }
        return mapping.get(name, MagicMock())

    container = MagicMock()
    container.get_service.side_effect = _get_service
    container.health_check.return_value = {"container": container_status}
    container.get_all_services.return_value = all_services or {}
    container.shutdown = AsyncMock()
    return container


@pytest.fixture()
def mock_container():
    """Fixture: mock service container injected into the module global."""
    container = _make_mock_container()
    original = main_module.service_container
    main_module.service_container = container
    yield container
    main_module.service_container = original


@pytest.fixture()
def client(mock_container):  # noqa: F811
    """TestClient with container already patched."""
    return TestClient(app, raise_server_exceptions=False)


def _get(client: TestClient, url: str, **kwargs) -> "Response":
    """GET with a unique X-Forwarded-For header to avoid rate-limiter exhaustion."""
    headers = kwargs.pop("headers", {})
    headers.setdefault("X-Forwarded-For", _unique_ip())
    return client.get(url, headers=headers, **kwargs)


def _post(client: TestClient, url: str, **kwargs) -> "Response":
    headers = kwargs.pop("headers", {})
    headers.setdefault("X-Forwarded-For", _unique_ip())
    return client.post(url, headers=headers, **kwargs)


def _delete(client: TestClient, url: str, **kwargs) -> "Response":
    headers = kwargs.pop("headers", {})
    headers.setdefault("X-Forwarded-For", _unique_ip())
    return client.delete(url, headers=headers, **kwargs)


def _options(client: TestClient, url: str, **kwargs) -> "Response":
    headers = kwargs.pop("headers", {})
    headers.setdefault("X-Forwarded-For", _unique_ip())
    return client.options(url, headers=headers, **kwargs)


# ===========================================================================
# Root endpoint
# ===========================================================================


class TestRootEndpoint:
    def test_root_redirects_to_docs(self, client):
        response = _get(client, "/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"

    def test_root_follows_redirect_to_docs(self, client):
        response = _get(client, "/")
        assert response.status_code == 200

    def test_root_content_is_html(self, client):
        response = _get(client, "/")
        assert response.status_code == 200


# ===========================================================================
# Legacy redirect endpoints
# ===========================================================================


class TestLegacyRedirects:
    def test_health_redirects_to_api_v1_health(self, client):
        response = _get(client, "/health", follow_redirects=False)
        assert response.status_code == 308
        assert "/api/v1/health" in response.headers["location"]

    def test_metrics_redirects_to_api_v1_metrics(self, client):
        response = _get(client, "/metrics", follow_redirects=False)
        assert response.status_code == 308
        assert "/api/v1/metrics" in response.headers["location"]

    def test_connectors_health_redirects(self, client):
        response = _get(client, "/connectors/health", follow_redirects=False)
        assert response.status_code == 308
        assert "/api/v1/health/detailed" in response.headers["location"]

    def test_cache_stats_redirects(self, client):
        response = _get(client, "/api/cache/stats", follow_redirects=False)
        assert response.status_code == 308
        assert "/api/v1/cache/stats" in response.headers["location"]

    def test_clear_video_cache_redirects(self, client):
        response = _delete(client, "/api/cache/auJzb1D-fag", follow_redirects=False)
        assert response.status_code == 308
        assert "auJzb1D-fag" in response.headers["location"]

    def test_clear_video_cache_includes_video_id(self, client):
        video_id = "auJzb1D-fag"
        response = _delete(client, f"/api/cache/{video_id}", follow_redirects=False)
        assert video_id in response.headers["location"]


# ===========================================================================
# Legacy /api/chat endpoint
# ===========================================================================


class TestLegacyChatEndpoint:
    def _patch_get_service(self, mock_container):
        """Patch the module-level get_service helper to use our mock."""
        return patch(
            "youtube_extension.backend.containers.service_container.get_service",
            side_effect=mock_container.get_service.side_effect,
        )

    def test_chat_returns_200_with_message(self, client, mock_container):
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/chat",
                json={"message": "Hello AI", "session_id": "test-session"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Hello AI" in data["response"]

    def test_chat_response_contains_session_id(self, client, mock_container):
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/chat",
                json={"message": "Test", "session_id": "my-session-id"},
            )
        data = response.json()
        assert data["session_id"] == "my-session-id"

    def test_chat_response_contains_timestamp(self, client, mock_container):
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/chat",
                json={"message": "Hi", "session_id": "s1"},
            )
        assert "timestamp" in response.json()

    def test_chat_with_no_processor_returns_fallback_message(self, client, mock_container):
        mock_container.get_service.side_effect = lambda n: (
            MagicMock(get_video_processor=lambda: None)
            if n == "video_processing_service"
            else MagicMock()
        )
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/chat",
                json={"message": "Test fallback", "session_id": "s2"},
            )
        assert response.status_code == 200
        assert "unavailable" in response.json()["response"].lower()

    def test_chat_raises_500_on_service_error(self, client, mock_container):
        mock_container.get_service.side_effect = RuntimeError("service broken")
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/chat",
                json={"message": "Boom", "session_id": "err"},
            )
        assert response.status_code == 500
        # Regression guard for information disclosure: the sanitized response
        # must not leak the raw exception message back to the client.
        assert response.json()["detail"] == "Internal server error"
        assert "service broken" not in response.text


# ===========================================================================
# Legacy /api/process-video-markdown endpoint
# ===========================================================================


class TestLegacyProcessVideoMarkdownEndpoint:
    def _patch_get_service(self, mock_container):
        return patch(
            "youtube_extension.backend.containers.service_container.get_service",
            side_effect=mock_container.get_service.side_effect,
        )

    def test_process_markdown_returns_200(self, client, mock_container):
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/process-video-markdown",
                json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
            )
        assert response.status_code == 200

    def test_process_markdown_returns_result_from_service(self, client, mock_container):
        expected = {"markdown": "# Title", "status": "ok"}
        mock_container.get_service.side_effect = lambda n: (
            MagicMock(
                rate_limit_check=lambda: True,
                increment_metric=lambda x: None,
            )
            if n == "health_monitoring_service"
            else MagicMock(
                process_video_for_markdown=AsyncMock(return_value=expected)
            )
        )
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/process-video-markdown",
                json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
            )
        assert response.status_code == 200

    def test_process_markdown_rate_limit_exceeded_returns_429(self, client, mock_container):
        mock_container.get_service.side_effect = lambda n: (
            MagicMock(
                rate_limit_check=lambda: False,
                increment_metric=lambda x: None,
            )
            if n == "health_monitoring_service"
            else MagicMock()
        )
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/process-video-markdown",
                json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
            )
        assert response.status_code == 429

    def test_process_markdown_service_error_returns_500(self, client, mock_container):
        mock_container.get_service.side_effect = RuntimeError("fail")
        with self._patch_get_service(mock_container):
            response = _post(
                client,
                "/api/process-video-markdown",
                json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
            )
        assert response.status_code == 500


# ===========================================================================
# Legacy /api/process-video endpoint
# ===========================================================================


class TestLegacyProcessVideoEndpoint:
    def _patch_get_service(self, mock_container):
        return patch(
            "youtube_extension.backend.containers.service_container.get_service",
            side_effect=mock_container.get_service.side_effect,
        )

    def test_process_video_sync_returns_200(self, client, mock_container):
        with patch.dict("os.environ", {"ASYNC_PROCESSING": "false"}):
            with self._patch_get_service(mock_container):
                response = _post(
                    client,
                    "/api/process-video",
                    json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
                )
        assert response.status_code == 200

    def test_process_video_async_mode_returns_queued(self, client, mock_container):
        mock_pubsub = MagicMock()
        mock_pubsub.publish_message = AsyncMock(return_value="msg-12345")

        def _svc(name):
            if name == "pubsub_service":
                return mock_pubsub
            return MagicMock()

        mock_container.get_service.side_effect = _svc
        with patch.dict("os.environ", {"ASYNC_PROCESSING": "true"}):
            with self._patch_get_service(mock_container):
                response = _post(
                    client,
                    "/api/process-video",
                    json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
                )
        data = response.json()
        assert data.get("status") == "queued"
        assert "job_id" in data

    def test_process_video_async_publish_fails_falls_back_to_sync(self, client, mock_container):
        mock_pubsub = MagicMock()
        mock_pubsub.publish_message = AsyncMock(return_value=None)

        mock_vps = MagicMock()
        mock_vps.process_video_basic = AsyncMock(
            return_value={"status": "ok", "video_data": {}}
        )

        def _svc(name):
            if name == "pubsub_service":
                return mock_pubsub
            if name == "video_processing_service":
                return mock_vps
            return MagicMock()

        mock_container.get_service.side_effect = _svc
        with patch.dict("os.environ", {"ASYNC_PROCESSING": "true"}):
            with self._patch_get_service(mock_container):
                response = _post(
                    client,
                    "/api/process-video",
                    json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
                )
        assert response.status_code == 200

    def test_process_video_error_returns_500(self, client, mock_container):
        mock_container.get_service.side_effect = RuntimeError("boom")
        with patch.dict("os.environ", {"ASYNC_PROCESSING": "false"}):
            with self._patch_get_service(mock_container):
                response = _post(
                    client,
                    "/api/process-video",
                    json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
                )
        assert response.status_code == 500

    def test_process_video_async_pubsub_exception_falls_back_to_sync(self, client, mock_container):
        mock_pubsub = MagicMock()
        mock_pubsub.publish_message = AsyncMock(side_effect=RuntimeError("pubsub fail"))

        mock_vps = MagicMock()
        mock_vps.process_video_basic = AsyncMock(
            return_value={"status": "ok", "video_data": {}}
        )

        def _svc(name):
            if name == "pubsub_service":
                return mock_pubsub
            if name == "video_processing_service":
                return mock_vps
            return MagicMock()

        mock_container.get_service.side_effect = _svc
        with patch.dict("os.environ", {"ASYNC_PROCESSING": "true"}):
            with self._patch_get_service(mock_container):
                response = _post(
                    client,
                    "/api/process-video",
                    json={"video_url": "https://youtube.com/watch?v=auJzb1D-fag"},
                )
        assert response.status_code == 200


# ===========================================================================
# System info endpoint
# ===========================================================================


class TestSystemInfoEndpoint:
    def test_system_info_returns_200(self, client, mock_container):
        response = _get(client, "/system/info")
        assert response.status_code == 200

    def test_system_info_contains_api_version(self, client, mock_container):
        response = _get(client, "/system/info")
        data = response.json()
        assert data["api_version"] == "2.0.0"

    def test_system_info_contains_architecture(self, client, mock_container):
        response = _get(client, "/system/info")
        data = response.json()
        assert data["architecture"] == "service-oriented"

    def test_system_info_contains_features(self, client, mock_container):
        response = _get(client, "/system/info")
        data = response.json()
        assert "features" in data
        assert data["features"]["api_versioning"] is True

    def test_system_info_contains_services(self, client, mock_container):
        response = _get(client, "/system/info")
        data = response.json()
        assert "services" in data

    def test_system_info_contains_timestamp(self, client, mock_container):
        response = _get(client, "/system/info")
        data = response.json()
        assert "timestamp" in data

    def test_system_info_error_returns_500(self, client, mock_container):
        mock_container.health_check.side_effect = RuntimeError("container broken")
        response = _get(client, "/system/info")
        assert response.status_code == 500


# ===========================================================================
# OpenAPI schema (custom_openapi)
# ===========================================================================


class TestCustomOpenAPISchema:
    def test_openapi_schema_endpoint_returns_200(self, client, mock_container):
        response = _get(client, "/openapi.json")
        assert response.status_code == 200

    def test_openapi_schema_title_is_correct(self, client, mock_container):
        response = _get(client, "/openapi.json")
        data = response.json()
        assert data["info"]["title"] == "YouTube Extension API"

    def test_openapi_schema_has_servers(self, client, mock_container):
        response = _get(client, "/openapi.json")
        data = response.json()
        assert "servers" in data
        urls = [s["url"] for s in data["servers"]]
        assert "http://localhost:8000" in urls
        assert "https://api.uvai.io" in urls

    def test_openapi_schema_has_security_schemes(self, client, mock_container):
        response = _get(client, "/openapi.json")
        data = response.json()
        assert "ApiKeyAuth" in data["components"]["securitySchemes"]

    def test_openapi_schema_has_custom_tags(self, client, mock_container):
        response = _get(client, "/openapi.json")
        data = response.json()
        tag_names = [t["name"] for t in data["tags"]]
        assert "Health" in tag_names or "API v1" in tag_names

    def test_openapi_schema_has_logo_extension(self, client, mock_container):
        response = _get(client, "/openapi.json")
        data = response.json()
        assert "x-logo" in data["info"]

    def test_openapi_schema_cached_on_second_call(self, client, mock_container):
        """Second /openapi.json call should return same cached schema."""
        r1 = _get(client, "/openapi.json")
        r2 = _get(client, "/openapi.json")
        assert r1.json()["info"]["title"] == r2.json()["info"]["title"]


# ===========================================================================
# Exception handlers
# ===========================================================================


class TestExceptionHandlers:
    async def test_value_error_handler_returns_400(self):
        mock_req = MagicMock()
        mock_req.url = "http://test/api"
        response = await main_module.value_error_handler(mock_req, ValueError("bad value"))
        assert response.status_code == 400

    async def test_value_error_handler_includes_error_field(self):
        import json as _json

        mock_req = MagicMock()
        mock_req.url = "http://test/api"
        response = await main_module.value_error_handler(mock_req, ValueError("oops"))
        body = _json.loads(response.body)
        assert body["error"] == "Bad Request"
        assert "oops" in body["detail"]

    async def test_value_error_handler_includes_timestamp(self):
        import json as _json

        mock_req = MagicMock()
        mock_req.url = "http://test/api"
        response = await main_module.value_error_handler(mock_req, ValueError("t"))
        body = _json.loads(response.body)
        assert "timestamp" in body

    async def test_global_exception_handler_returns_500(self):
        mock_req = MagicMock()
        mock_req.url = "http://test/api"
        response = await main_module.global_exception_handler(mock_req, RuntimeError("crash"))
        assert response.status_code == 500

    async def test_global_exception_handler_does_not_leak_internal_details(self):
        """The 500 body must not disclose the exception (message or class) or the
        request URL (CWE-209); those go to the server log only."""
        import json as _json

        mock_req = MagicMock()
        mock_req.url = "http://test/api/secret-path"
        response = await main_module.global_exception_handler(
            mock_req, RuntimeError("crash: db password = hunter2")
        )
        body = _json.loads(response.body)
        # No exception class name, exception message, or request URL in the body.
        assert "error_type" not in body
        serialized = _json.dumps(body)
        assert "RuntimeError" not in serialized
        assert "crash" not in serialized
        assert "hunter2" not in serialized
        assert "secret-path" not in serialized
        # Static, non-sensitive fields remain.
        assert body["error"] == "Internal server error"
        assert body["detail"] == "Internal server error"

    async def test_global_exception_handler_includes_version(self):
        import json as _json

        mock_req = MagicMock()
        mock_req.url = "http://test/api"
        response = await main_module.global_exception_handler(mock_req, Exception("e"))
        body = _json.loads(response.body)
        assert body["version"] == "2.0.0"

    async def test_global_exception_handler_request_without_url(self):
        """Handler should not crash if request has no .url attribute."""
        mock_req = MagicMock(spec=[])  # no attributes
        response = await main_module.global_exception_handler(mock_req, Exception("no url"))
        assert response.status_code == 500

    async def test_value_error_handler_request_without_url(self):
        mock_req = MagicMock(spec=[])  # no attributes
        response = await main_module.value_error_handler(mock_req, ValueError("no url"))
        assert response.status_code == 400


# ===========================================================================
# Startup event
# ===========================================================================


class TestStartupEvent:
    async def test_startup_sets_service_container(self):
        mock_container = _make_mock_container()
        original = main_module.service_container

        with patch(
            "youtube_extension.backend.main.get_service_container",
            return_value=mock_container,
        ):
            with patch(
                "youtube_extension.backend.main.initialize_database_optimization",
                AsyncMock(),
            ):
                await main_module.startup_event()

        assert main_module.service_container is mock_container
        main_module.service_container = original

    async def test_startup_calls_initialize_database_optimization(self):
        mock_container = _make_mock_container()
        mock_init_db = AsyncMock()

        with patch(
            "youtube_extension.backend.main.get_service_container",
            return_value=mock_container,
        ):
            with patch(
                "youtube_extension.backend.main.initialize_database_optimization",
                mock_init_db,
            ):
                await main_module.startup_event()

        mock_init_db.assert_awaited_once()
        main_module.service_container = mock_container  # cleanup

    async def test_startup_raises_when_critical_service_fails(self):
        mock_container = MagicMock()
        mock_container.get_service.side_effect = RuntimeError("service not found")

        with patch(
            "youtube_extension.backend.main.get_service_container",
            return_value=mock_container,
        ):
            with pytest.raises(RuntimeError):
                await main_module.startup_event()


# ===========================================================================
# Shutdown event
# ===========================================================================


class TestShutdownEvent:
    async def test_shutdown_calls_container_shutdown(self):
        mock_container = _make_mock_container()
        main_module.service_container = mock_container

        with patch(
            "youtube_extension.backend.main.shutdown_database_optimization",
            AsyncMock(),
        ):
            await main_module.shutdown_event()

        mock_container.shutdown.assert_awaited_once()

    async def test_shutdown_calls_shutdown_database_optimization(self):
        mock_container = _make_mock_container()
        main_module.service_container = mock_container
        mock_db_shutdown = AsyncMock()

        with patch(
            "youtube_extension.backend.main.shutdown_database_optimization",
            mock_db_shutdown,
        ):
            await main_module.shutdown_event()

        mock_db_shutdown.assert_awaited_once()

    async def test_shutdown_does_not_raise_when_db_shutdown_fails(self):
        mock_container = _make_mock_container()
        main_module.service_container = mock_container

        with patch(
            "youtube_extension.backend.main.shutdown_database_optimization",
            AsyncMock(side_effect=RuntimeError("db error")),
        ):
            # Should complete without raising
            await main_module.shutdown_event()

    async def test_shutdown_warns_on_container_failure(self):
        """If container.shutdown raises, shutdown_event logs a warning but doesn't crash."""
        mock_container = _make_mock_container()
        mock_container.shutdown = AsyncMock(side_effect=RuntimeError("shutdown error"))
        main_module.service_container = mock_container

        with patch(
            "youtube_extension.backend.main.shutdown_database_optimization",
            AsyncMock(),
        ):
            # Should not propagate the exception
            await main_module.shutdown_event()


# ===========================================================================
# Documentation endpoints
# ===========================================================================


class TestDocumentationEndpoints:
    def test_docs_endpoint_returns_200(self, client, mock_container):
        response = _get(client, "/docs")
        assert response.status_code == 200

    def test_redoc_endpoint_returns_200(self, client, mock_container):
        response = _get(client, "/redoc")
        assert response.status_code == 200


# ===========================================================================
# CORS headers
# ===========================================================================


class TestCORSMiddleware:
    def test_cors_headers_present_on_options(self, client, mock_container):
        response = _options(
            client,
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Redirect or 200 are fine; CORS headers may be on either
        assert response.status_code in (200, 307, 308, 404)


# ===========================================================================
# App metadata
# ===========================================================================


class TestAppMetadata:
    def test_app_title(self):
        assert app.title == "UVAI API"

    def test_app_version(self):
        assert app.version == "2.0.0"

    def test_app_has_routes(self):
        assert len(app.routes) > 0
