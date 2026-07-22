from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is in sys.path so we can import scripts
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import scripts.check_production_readiness as module


def test_check_cors_present(tmp_path):
    # Mock src/youtube_extension/main.py path
    main_py = tmp_path / "main.py"
    main_py.write_text('_IS_PRODUCTION = _ENVIRONMENT == "production"')

    # Patch Path within check_cors
    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors() is False  # False means NO error


def test_check_cors_missing(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('some other content')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors() is True  # True means error


def test_check_headers_present(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('response.headers["X-Frame-Options"] = "DENY"\nresponse.headers["X-Content-Type-Options"] = "nosniff"')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_headers() is False


def test_check_headers_missing(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('some content')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_headers() is True


def test_check_logging_debug_fails(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('logging.basicConfig(level=logging.DEBUG)')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_logging() is True


def test_check_logging_root_setlevel_debug_fails(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text("logging.root.setLevel(logging.DEBUG)")

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_logging() is True


def test_check_logging_sentry_pii_hardcoded_fails(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('send_default_pii = True')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_logging() is True


def test_check_logging_safe_passes(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text('logging.basicConfig(level=logging.INFO)\nsend_default_pii=os.getenv("SENTRY_SEND_PII", "false").lower() == "true"')

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_logging() is False


def test_check_dependencies_wildcard_requirements_fails(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text('fastapi==*')
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^19"}}')

    def mock_path(p):
        if str(p) == "requirements.txt":
            return req_txt
        if str(p) == "package.json":
            return pkg_json
        return Path(p)

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1) # mock 'which' failing
        assert module.check_dependencies() is True


def test_check_dependencies_wildcard_package_fails(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text('fastapi>=0.110.0')
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "*"}}')

    def mock_path(p):
        if str(p) == "requirements.txt":
            return req_txt
        if str(p) == "package.json":
            return pkg_json
        return Path(p)

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1) # mock 'which' failing
        assert module.check_dependencies() is True


def test_check_dependencies_safe_passes(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text('fastapi>=0.110.0')
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^19"}}')

    def mock_path(p):
        if str(p) == "requirements.txt":
            return req_txt
        if str(p) == "package.json":
            return pkg_json
        return Path(p)

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1) # mock 'which' failing
        assert module.check_dependencies() is False


def test_check_env_vars_production_missing_fails(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert module.check_env_vars() is True


def test_check_env_vars_development_missing_passes(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert module.check_env_vars() is False
