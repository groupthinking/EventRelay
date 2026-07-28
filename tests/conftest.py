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
try:
    import src  # noqa: F401
    import src.integration  # noqa: F401
except Exception:
    pass

# Enable dev-mode auth bypass for tests by default.
# We set EVENTRELAY_API_KEY to empty string to override any .env file setting,
# unless it was explicitly configured in the shell environment.
# Since main.py loads .env with override=False, setting EVENTRELAY_API_KEY to ""
# in os.environ before main.py imports will prevent it from loading the real key.
# We also wrap dotenv.load_dotenv in case any module calls it with override=True later.
if "EVENTRELAY_API_KEY" not in os.environ:
    os.environ["EVENTRELAY_API_KEY"] = ""
    os.environ["ALLOW_UNAUTHENTICATED"] = "1"

    try:
        import dotenv
        _real_load_dotenv = dotenv.load_dotenv

        def _wrapped_load_dotenv(*args, **kwargs):
            res = _real_load_dotenv(*args, **kwargs)
            os.environ["EVENTRELAY_API_KEY"] = ""
            os.environ["ALLOW_UNAUTHENTICATED"] = "1"
            return res

        dotenv.load_dotenv = _wrapped_load_dotenv
    except ImportError:
        pass

