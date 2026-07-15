import os
import pytest
import types
from unittest.mock import MagicMock
import sys

# Mock pydantic if it's not available
try:
    import pydantic
except ImportError:
    mock_pydantic = MagicMock()
    sys.modules["pydantic"] = mock_pydantic

# Other unit tests (e.g. test_cloud_routes, test_backend_main) register a
# MagicMock stand-in for these modules via `sys.modules.setdefault(...)` and
# never tear it down. When those files are collected before this one, the stale
# mock leaks in, turning LookerEmbeddedService/LookerEmbedService into MagicMocks
# so the security assertions below silently pass through a mock instead of the
# real constructor. Evict any non-module (mock) stand-in so we always import the
# real implementations, regardless of collection order.
for _mod_name in ("src.integration.looker_embedded", "src.integration.looker_embed"):
    if not isinstance(sys.modules.get(_mod_name), types.ModuleType):
        sys.modules.pop(_mod_name, None)

from src.integration.looker_embedded import LookerEmbeddedService  # noqa: E402
from src.integration.looker_embed import LookerEmbedService  # noqa: E402


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
