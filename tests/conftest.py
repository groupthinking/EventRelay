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

# Enable dev-mode auth bypass unless the environment already configures auth.
if not os.getenv("EVENTRELAY_API_KEY"):
    os.environ.setdefault("ALLOW_UNAUTHENTICATED", "1")
