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

# Pre-import the real (empty, cheap) src / src.integration packages BEFORE any
# test module is collected. Several test modules stub `src` in sys.modules as a
# bare, non-package module via setdefault() at import time (to avoid heavy
# transitive imports). If one of those runs first, `src` becomes a non-package
# and later modules importing real `src.integration.*` leaves fail to collect
# ("'src.integration' is not a package"). Importing the real packages here makes
# those setdefault() calls no-ops, keeping `src` a proper package.
# NOTE: we deliberately do NOT import src.agents — its __init__ is heavy and
# some tests intentionally stub the src.agents namespace.
#
# We also pre-import src.integration.looker_embedded specifically: test_backend_main
# stubs that submodule as a MagicMock in sys.modules (guarded by `if not in
# sys.modules`), and it never restores it. Once real test_looker_security started
# importing the real class, that leaked mock made it fail. Pre-importing the real
# (cheap) submodule here turns the guarded stub into a no-op. It imports only
# stdlib + pydantic, so it is safe to load eagerly.
try:
    import src  # noqa: F401
    import src.integration  # noqa: F401
    import src.integration.looker_embedded  # noqa: F401
except Exception:
    pass

# Enable dev-mode auth bypass unless the environment already configures auth.
if not os.getenv("EVENTRELAY_API_KEY"):
    os.environ.setdefault("ALLOW_UNAUTHENTICATED", "1")
