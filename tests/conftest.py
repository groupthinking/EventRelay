"""Global pytest configuration.

Imported by pytest before any test module is collected, so environment
defaults set here take effect before the FastAPI app (and its
``APIKeyAuthMiddleware``) are constructed at import time.

The deny-by-default API-key auth middleware fails closed with HTTP 503 when
neither ``EVENTRELAY_API_KEY`` nor ``ALLOW_UNAUTHENTICATED`` is configured.
The test suite exercises endpoint logic, not the auth gate (which has its own
dedicated tests in ``test_api_key_auth.py`` that override these vars via
``monkeypatch``), so we opt into the local-dev "open" mode here.

``setdefault`` is used so an explicitly configured environment (e.g. a CI job
that sets ``EVENTRELAY_API_KEY`` on purpose) is never overridden.
"""

import os
import socket
import sys
from pathlib import Path


# Live smoke modules are excluded during collection, before their top-level
# imports can load SDKs, read local .env files, connect to localhost, or make
# network calls.  RUN_LIVE_E2E=1 opts into non-deployment live smoke coverage.
# Deployment-capable pipelines require the additional RUN_LIVE_DEPLOY=1 opt-in
# so enabling live reads cannot implicitly publish code or infrastructure.
_LIVE_E2E_TESTS = frozenset(
    {
        "testing/test_agent_network.py",
        "testing/test_api_validation.py",
        "testing/test_enhanced_backend.py",
        "testing/test_full_mcp_pipeline.py",
        "testing/test_full_pipeline.py",
        "testing/test_integrated_pipeline.py",
        "testing/test_integration.py",
        "testing/test_live_integration.py",
        "testing/test_mcp_integration.py",
        "testing/test_mcp_tool_direct.py",
        "testing/test_multi_agent_learning.py",
        "testing/test_production_video.py",
        "testing/test_real_video_processing.py",
        "testing/test_skill_connector.py",
        "testing/test_tri_model_consensus.py",
        "testing/test_youtube_api.py",
    }
)
_LIVE_DEPLOY_TESTS = frozenset(
    {
        "testing/test_full_mcp_pipeline.py",
        "testing/test_integrated_pipeline.py",
    }
)
_TESTS_ROOT = Path(__file__).resolve().parent


# Ordinary unit/coverage runs must never discover ambient cloud credentials.
# Some Google client constructors fall back to the instance-metadata service
# when a test accidentally leaves credentials unconfigured.  That turns an
# otherwise local test into a network probe and can make CI depend on the
# runner's identity.  Block only the well-known metadata endpoints here; live
# smoke/deployment runs remain an explicit opt-in below.
_CLOUD_METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "fd00:ec2::254",
        "metadata.google.internal",
    }
)
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_ORIGINAL_SOCKET_CONNECT = socket.socket.connect


def _metadata_host(value: object) -> bool:
    """Return whether *value* names a well-known cloud metadata endpoint."""

    return str(value).strip("[]").lower().rstrip(".") in _CLOUD_METADATA_HOSTS


def _safe_getaddrinfo(host: object, *args: object, **kwargs: object):
    if _metadata_host(host):
        raise RuntimeError("tests must not resolve cloud instance metadata")
    return _ORIGINAL_GETADDRINFO(host, *args, **kwargs)


def _safe_socket_connect(sock: socket.socket, address: object):
    host = address[0] if isinstance(address, tuple) and address else address
    if _metadata_host(host):
        raise RuntimeError("tests must not connect to cloud instance metadata")
    return _ORIGINAL_SOCKET_CONNECT(sock, address)  # type: ignore[arg-type]


if os.getenv("RUN_LIVE_E2E") != "1":
    socket.getaddrinfo = _safe_getaddrinfo  # type: ignore[assignment]
    socket.socket.connect = _safe_socket_connect  # type: ignore[method-assign]


def _enabled(name: str) -> bool:
    """Require an exact, auditable opt-in instead of truthy env parsing."""

    return os.getenv(name) == "1"


def pytest_ignore_collect(collection_path: Path, config: object) -> bool:
    """Keep live smoke modules out of ordinary pytest collection entirely."""

    del config
    try:
        relative_path = Path(collection_path).resolve().relative_to(_TESTS_ROOT)
    except ValueError:
        return False

    test_path = relative_path.as_posix()
    if test_path not in _LIVE_E2E_TESTS:
        return False
    if not _enabled("RUN_LIVE_E2E"):
        return True
    return test_path in _LIVE_DEPLOY_TESTS and not _enabled("RUN_LIVE_DEPLOY")

# Ensure the repository root is importable so `src` resolves as a real package.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Pre-import the real, lightweight package namespaces before collection.
# Several test modules use ``sys.modules.setdefault`` for optional dependency
# stubs. Loading these namespaces first prevents those fallbacks from replacing
# a package with a bare synthetic module and breaking later imports. These are
# required test-harness imports, so an import failure must fail collection.
# Deliberately do not import ``src.agents``; its initializer is heavyweight and
# tests that exercise its leaves provide their own scoped dependencies.
import src  # noqa: F401, E402
import src.integration  # noqa: F401, E402
import youtube_extension  # noqa: F401, E402
import youtube_extension.processors  # noqa: F401, E402

# Preserve the real optional yt-dlp package before collection-only tests can
# install a bare fallback with ``sys.modules.setdefault``. Absence is allowed
# because yt-dlp is an optional extra; a broken installed package is not.
try:
    import yt_dlp  # noqa: F401, E402
except ModuleNotFoundError as exc:
    if exc.name != "yt_dlp":
        raise

# Enable dev-mode auth bypass unless the environment already configures auth.
if not os.getenv("EVENTRELAY_API_KEY"):
    os.environ.setdefault("ALLOW_UNAUTHENTICATED", "1")
