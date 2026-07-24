"""Unit tests for the fail-closed production readiness auditor script."""

import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

import scripts.check_production_readiness as readiness


def test_mask_secret_empty():
    assert readiness.mask_secret("") == "[EMPTY]"
    assert readiness.mask_secret(None) == "[EMPTY]"


def test_mask_secret_present():
    secret = "sk_test_51ToS02AmTgsI2zgNSu5"
    masked = readiness.mask_secret(secret)
    # Ensure no prefix or suffix of the secret is present in the output
    assert "sk_test" not in masked
    assert "S02" not in masked
    assert "PRESENT" in masked
    assert f"len={len(secret)}" in masked


def test_get_uncommented_assignments(tmp_path):
    env_content = """
# Commented out variables
# STRIPE_SECRET_KEY=sk_test_123

# Uncommented assignments
STRIPE_SECRET_KEY=sk_test_abc
DATABASE_URL = postgresql://localhost/db
PORT=8080
# Empty line

# Invalid line
INVALID_LINE_NO_EQUALS
"""
    env_file = tmp_path / ".env.test"
    env_file.write_text(env_content, encoding="utf-8")

    assignments = readiness.get_uncommented_assignments(env_file)
    assert "STRIPE_SECRET_KEY" in assignments
    assert "DATABASE_URL" in assignments
    assert "PORT" in assignments
    assert "INVALID_LINE_NO_EQUALS" not in assignments


@patch("scripts.check_production_readiness.get_uncommented_assignments")
def test_check_configuration_templates_success(mock_assignments, tmp_path):
    # Mock template parsing to return all required keys
    all_keys = set(readiness.REQUIRED_BACKEND_KEYS + readiness.REQUIRED_WEB_KEYS)
    mock_assignments.return_value = all_keys

    # Mock Path exists checks
    with patch.object(Path, "exists", return_value=True):
        assert readiness.check_configuration_templates() is True


@patch("scripts.check_production_readiness.get_uncommented_assignments")
def test_check_configuration_templates_missing_keys(mock_assignments):
    # Missing a required key
    mock_assignments.return_value = set(["STRIPE_SECRET_KEY"])

    with patch.object(Path, "exists", return_value=True):
        assert readiness.check_configuration_templates() is False


def test_check_live_environment_ci_mode_warnings_allowed():
    # In CI mode, missing keys should only warn, not fail the check
    with patch.dict(os.environ, {}, clear=True):
        assert readiness.check_live_environment("ci") is True


def test_check_live_environment_live_mode_fails_closed():
    # In live/production mode, missing keys must fail the check
    with patch.dict(os.environ, {}, clear=True):
        assert readiness.check_live_environment("live") is False


def test_check_live_environment_live_mode_success_when_keys_present():
    # All required keys are defined
    dummy_env = {key: "dummy_value" for key in readiness.REQUIRED_BACKEND_KEYS + readiness.REQUIRED_WEB_KEYS}
    with patch.dict(os.environ, dummy_env, clear=True):
        assert readiness.check_live_environment("live") is True


def test_check_cors_and_headers_success(tmp_path):
    # Mock main.py content with all secure CORS and Header implementations
    dummy_main_content = """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
    )
    def _is_loopback_origin(origin: str) -> bool:
        pass
    _IS_PRODUCTION = True
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        response.headers["X-Frame-Options"] = "DENY"
    os.getenv("LOG_LEVEL")
    """
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "read_text", return_value=dummy_main_content):
            assert readiness.check_cors_and_headers() is True


def test_check_cors_and_headers_missing_security_headers():
    # Missing SecurityHeadersMiddleware in main.py
    dummy_main_content = """
    app.add_middleware(CORSMiddleware)
    """
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "read_text", return_value=dummy_main_content):
            assert readiness.check_cors_and_headers() is False


@patch("scripts.check_production_readiness.check_configuration_templates")
@patch("scripts.check_production_readiness.check_live_environment")
@patch("scripts.check_production_readiness.check_cors_and_headers")
@patch("scripts.check_production_readiness.check_dependencies")
def test_run_checks_aggregate_status(mock_dep, mock_cors, mock_live, mock_templates):
    # Verify aggregate exit status (0 for success, 1 for failure)
    mock_templates.return_value = True
    mock_live.return_value = True
    mock_cors.return_value = True
    mock_dep.return_value = True
    assert readiness.run_checks("ci") == 0

    mock_cors.return_value = False
    assert readiness.run_checks("ci") == 1
