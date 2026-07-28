import os
import pytest
from youtube_extension.utils.proxy import (
    get_proxy_url,
    get_proxy_dict,
    get_transcript_proxy_config,
    redact_proxy_credentials,
)

def test_get_proxy_url_unset(monkeypatch):
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)
    assert get_proxy_url() is None

def test_get_proxy_url_valid(monkeypatch):
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://user:pass@127.0.0.1:8080")
    assert get_proxy_url() == "http://user:pass@127.0.0.1:8080"

def test_get_proxy_url_malformed(monkeypatch):
    monkeypatch.setenv("WEBSHARE_PROXY_URL", "ftp://invalid-scheme.com")
    assert get_proxy_url() is None

def test_get_proxy_dict(monkeypatch):
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)
    assert get_proxy_dict() is None

    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://127.0.0.1:8080")
    assert get_proxy_dict() == {
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080",
    }

def test_get_transcript_proxy_config(monkeypatch):
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)
    assert get_transcript_proxy_config() is None

    monkeypatch.setenv("WEBSHARE_PROXY_URL", "http://127.0.0.1:8080")
    config = get_transcript_proxy_config()
    # It might be None or a GenericProxyConfig depending on HAS_PROXY_CONFIG
    # Just verify it doesn't crash
    if config is not None:
        assert config.http_url == "http://127.0.0.1:8080"

def test_redact_proxy_credentials(monkeypatch):
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)
    assert redact_proxy_credentials("some proxy info http://127.0.0.1") == "some proxy info http://127.0.0.1"

    proxy_url = "http://user:pass@127.0.0.1:8080"
    monkeypatch.setenv("WEBSHARE_PROXY_URL", proxy_url)
    text = f"Connecting to {proxy_url} to download..."
    redacted = redact_proxy_credentials(text)
    assert "user:pass" not in redacted
    assert "127.0.0.1:8080" in redacted
