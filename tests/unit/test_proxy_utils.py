"""Regression tests for proxy credential redaction.

``redact_proxy_credentials`` is called from exception handlers that log
subprocess and HTTP failures, so anything it fails to strip is written to logs
verbatim. Every ``LEAKED`` case below reproduces text that leaked before the
two-pass implementation landed.

The helper exists in two copies -- the canonical
``src/youtube_extension/utils/proxy.py`` and the standalone
``shared/libs/youtube_proxy.py`` used by the importlib fallback path. Both are
exercised here, because a fix applied to only one of them leaves the other
leaking.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

from youtube_extension.utils.proxy import redact_proxy_credentials

_PROXY_ENV_VAR = "WEBSHARE_PROXY_URL"
_CONFIGURED = "http://user:s3cr3t@proxy.internal:8080"


def _load_shared_copy():
    """Import ``shared/libs/youtube_proxy.py`` directly, without a package."""
    path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "shared"
        / "libs"
        / "youtube_proxy.py"
    )
    name = "_shared_youtube_proxy"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec: the module uses ``from __future__ import
    # annotations``, so its dataclass field annotations are strings that
    # ``dataclasses`` resolves by looking the module up in ``sys.modules``.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[name]
        raise
    return module


@pytest.fixture(params=["canonical", "shared"])
def redact(request):
    """Both implementations, so neither can drift into leaking alone."""
    if request.param == "canonical":
        return redact_proxy_credentials
    return _load_shared_copy()._redact_proxy_credentials


@pytest.fixture(autouse=True)
def _configured_proxy(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, _CONFIGURED)


# Each case is (text, secret-that-must-not-survive).
LEAKED = [
    pytest.param(
        f"transcript fetch failed via {_CONFIGURED}",
        "s3cr3t",
        id="exact-configured-url",
    ),
    pytest.param(
        f"ProxyError: {_CONFIGURED}/",
        "s3cr3t",
        id="trailing-slash-from-urllib3",
    ),
    # requests/urllib3 lowercase the host when re-rendering a URL, so the text
    # no longer matches the env value byte-for-byte.
    pytest.param(
        "connect to http://user:s3cr3t@PROXY.INTERNAL:8080 refused",
        "s3cr3t",
        id="host-case-normalised",
    ),
    pytest.param(
        "http://user:s3cr3t%40x@proxy.internal:8080",
        "s3cr3t",
        id="percent-encoded-password",
    ),
    # A different proxy variable entirely -- never equal to WEBSHARE_PROXY_URL,
    # so the exact-match pass alone never touched it.
    pytest.param(
        "HTTPS_PROXY=http://bob:hunter2@corp.proxy:3128 connection refused",
        "hunter2",
        id="different-proxy-variable",
    ),
    # RFC 3986 requires "@" in userinfo to be percent-encoded, but real proxy
    # values carry a raw one. Matching to the FIRST "@" left the tail behind.
    pytest.param(
        "http://user:pa@ss@proxy.internal:8080",
        "ss@proxy",
        id="raw-at-sign-in-password",
    ),
    pytest.param(
        "socks5://:tokenz@proxy:1080",
        "tokenz",
        id="password-with-no-username",
    ),
    pytest.param(
        "CalledProcessError: ['yt-dlp', '--proxy', 'http://u:p4ss@h:1']",
        "p4ss",
        id="argv-repr-from-subprocess",
    ),
]


@pytest.mark.parametrize(("text", "secret"), LEAKED)
def test_credentials_never_survive_redaction(redact, text, secret):
    assert secret not in redact(text)


def test_configured_proxy_host_is_preserved(redact):
    """Operators must still be able to tell *which* proxy was in play."""
    result = redact(f"failed via {_CONFIGURED}")
    assert "proxy.internal:8080" in result
    assert "s3cr3t" not in result


# Text that must survive untouched -- over-redaction destroys diagnostics.
PRESERVED = [
    pytest.param("https://example.com/a@b", id="at-sign-in-path"),
    pytest.param("https://example.com?e=a@b", id="at-sign-in-query"),
    pytest.param("https://example.com#f=a@b", id="at-sign-in-fragment"),
    pytest.param("connect to proxy.internal:8080 failed", id="bare-host-port"),
    pytest.param("mailto is not a url: a@b.com", id="bare-email"),
]


@pytest.mark.parametrize("text", PRESERVED)
def test_non_credential_text_is_untouched(redact, text):
    assert redact(text) == text


def test_match_never_spans_two_urls(redact):
    """A greedy class must not swallow the gap between separate URLs."""
    result = redact("http://a:1@h1:1 and http://b:2@h2:2")
    assert result == "http://***:***@h1:1 and http://***:***@h2:2"


def test_redaction_is_a_noop_when_no_proxy_configured(redact, monkeypatch):
    """The generic sweep still applies with no WEBSHARE_PROXY_URL set."""
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    assert "hunter2" not in redact("http://bob:hunter2@corp.proxy:3128")
    assert redact("no credentials here") == "no credentials here"


def test_hostile_str_does_not_propagate(redact):
    """Called from except blocks -- raising here would mask the real error."""

    class Hostile:
        def __str__(self) -> str:
            raise RuntimeError("boom")

    assert redact(Hostile()) == "<unprintable error>"


def test_non_string_input_is_stringified(redact):
    assert redact(12345) == "12345"


def test_exception_object_is_accepted(redact):
    """The common call shape is redact(str(error)) -- accept the error too."""
    assert "s3cr3t" not in redact(RuntimeError(f"boom via {_CONFIGURED}"))
