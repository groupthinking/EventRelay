import os
import pytest
from unittest.mock import MagicMock
import sys

# Mock pydantic if it's not available
try:
    import pydantic
except ImportError:
    mock_pydantic = MagicMock()
    sys.modules["pydantic"] = mock_pydantic

from src.integration.looker_embedded import LookerEmbeddedService
from src.integration.looker_embed import LookerEmbedService


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
