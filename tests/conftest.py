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
import sys

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
