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


def test_check_configuration_templates_missing(tmp_path):
    # Mock files missing
    with patch("scripts.check_production_readiness.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        assert module.check_configuration_templates() is False


def test_check_configuration_templates_present(tmp_path):
    root_example = tmp_path / "env.example"
    root_example.write_text("BACKEND_URL=foo\nENVIRONMENT=dev")

    web_example = tmp_path / "web_env.example"
    web_example.write_text("\n".join(f"{key}=val" for key in module.REQUIRED_WEB_KEYS))

    def mock_path(p):
        if "apps/web" in str(p):
            return web_example
        return root_example

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path):
        assert module.check_configuration_templates() is True


def test_check_live_environment():
    with patch("os.getenv", return_value="some_value"):
        assert module.check_live_environment() is True


def test_check_cors_and_headers_present(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text(
        'CORSMiddleware\n'
        'allow_credentials=True\n'
        'allow_origins=_allowed_origins\n'
        '_is_loopback_origin\n'
        '_IS_PRODUCTION\n'
        'SecurityHeadersMiddleware\n'
        '"X-Frame-Options"\n'
        'logging.basicConfig\n'
        'logging.getLogger\n'
        'send_default_pii=os.getenv("SENTRY_SEND_PII", "false")\n'
    )

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors_and_headers() is True


def test_check_cors_and_headers_fails_on_debug_logging(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text(
        'CORSMiddleware\n'
        'allow_credentials=True\n'
        'allow_origins=_allowed_origins\n'
        '_is_loopback_origin\n'
        '_IS_PRODUCTION\n'
        'SecurityHeadersMiddleware\n'
        '"X-Frame-Options"\n'
        'logging.basicConfig(level=logging.DEBUG)\n'
        'logging.getLogger\n'
    )

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors_and_headers() is False


def test_check_cors_and_headers_fails_on_setlevel_debug(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text(
        'CORSMiddleware\n'
        'allow_credentials=True\n'
        'allow_origins=_allowed_origins\n'
        '_is_loopback_origin\n'
        '_IS_PRODUCTION\n'
        'SecurityHeadersMiddleware\n'
        '"X-Frame-Options"\n'
        'logging.basicConfig\n'
        'logging.root.setLevel(logging.DEBUG)\n'
        'logging.getLogger\n'
    )

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors_and_headers() is False


def test_check_cors_and_headers_fails_on_sentry_pii(tmp_path):
    main_py = tmp_path / "main.py"
    main_py.write_text(
        'CORSMiddleware\n'
        'allow_credentials=True\n'
        'allow_origins=_allowed_origins\n'
        '_is_loopback_origin\n'
        '_IS_PRODUCTION\n'
        'SecurityHeadersMiddleware\n'
        '"X-Frame-Options"\n'
        'logging.basicConfig\n'
        'logging.getLogger\n'
        'send_default_pii = True\n'
    )

    with patch("scripts.check_production_readiness.Path", return_value=main_py):
        assert module.check_cors_and_headers() is False


def test_check_dependencies_wildcards_fails(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text('fastapi==*')
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "*"}}')

    def mock_path(p):
        if "package.json" in str(p):
            return pkg_json
        return req_txt

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert module.check_dependencies() is False


def test_check_dependencies_safe_passes(tmp_path):
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text('fastapi>=0.110.0')
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^19"}}')

    def mock_path(p):
        if "package.json" in str(p):
            return pkg_json
        return req_txt

    with patch("scripts.check_production_readiness.Path", side_effect=mock_path), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert module.check_dependencies() is True
