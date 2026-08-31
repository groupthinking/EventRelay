import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock pydantic if it's not available
try:
    import pydantic
except ImportError:
    mock_pydantic = MagicMock()
    sys.modules["pydantic"] = mock_pydantic

# These security tests must exercise the REAL Looker services, not a mock.
# Other unit-test modules (test_backend_main, test_cloud_routes) install a
# MagicMock at "src.integration.looker_embedded" in sys.modules at import time,
# and test_backend_main does not remove it. Depending on pytest's collection
# order that stale stub would otherwise make LookerEmbeddedService resolve to a
# MagicMock here (the class would no longer raise on a missing secret). Load
# the modules directly from their source files under private names so this test
# is hermetic regardless of sys.modules state.
_SRC = Path(__file__).resolve().parents[2] / "src"


def _load_real(module_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(module_name, _SRC / rel_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LookerEmbeddedService = _load_real(
    "_real_looker_embedded", "integration/looker_embedded.py"
).LookerEmbeddedService
LookerEmbedService = _load_real(
    "_real_looker_embed", "integration/looker_embed.py"
).LookerEmbedService


def test_looker_embedded_service_no_secret():
    # Ensure environment variable is not set
    if "LOOKER_EMBED_SECRET" in os.environ:
        del os.environ["LOOKER_EMBED_SECRET"]

    with pytest.raises(RuntimeError) as excinfo:
        LookerEmbeddedService()
    assert "LOOKER_EMBED_SECRET is not set" in str(excinfo.value)


def test_looker_embedded_service_with_secret():
    os.environ["LOOKER_EMBED_SECRET"] = "test_secret"
    try:
        service = LookerEmbeddedService()
        assert service.looker_secret == "test_secret"
    finally:
        del os.environ["LOOKER_EMBED_SECRET"]


def test_looker_embed_service_no_secret():
    # Ensure environment variable is not set
    if "LOOKER_EMBED_SECRET" in os.environ:
        del os.environ["LOOKER_EMBED_SECRET"]

    with pytest.raises(RuntimeError) as excinfo:
        LookerEmbedService()
    assert "LOOKER_EMBED_SECRET is not set" in str(excinfo.value)


def test_looker_embed_service_with_constructor_secret():
    # Ensure environment variable is not set
    if "LOOKER_EMBED_SECRET" in os.environ:
        del os.environ["LOOKER_EMBED_SECRET"]

    service = LookerEmbedService(secret="constructor_secret")
    assert service.secret == "constructor_secret"


def test_looker_embed_service_with_env_secret():
    os.environ["LOOKER_EMBED_SECRET"] = "env_secret"
    try:
        service = LookerEmbedService()
        assert service.secret == "env_secret"
    finally:
        del os.environ["LOOKER_EMBED_SECRET"]
