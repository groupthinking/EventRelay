"""Unit tests for ``youtube_extension.utils.proxy`` credential hygiene.

Regression coverage for #1113 — "Prevent proxy credential leakage from urlparse
errors". Three distinct defects are pinned here:

1. ``get_proxy_url()`` raised ``ValueError`` out of ``urllib.parse`` for several
   malformed inputs instead of honouring its documented "malformed ⇒ None"
   contract, so the exception escaped to callers that log it.
2. The warning emitted for a malformed value must never carry the URL, because
   the URL is exactly where the credentials live.
3. ``redact_proxy_credentials()`` only stripped an *exact* match of the
   configured env value, so a ``CalledProcessError`` argv dump, a yt-dlp stderr
   echo, or a different proxy variable leaked ``user:pass`` verbatim.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from youtube_extension.utils import proxy as proxy_module  # noqa: E402
from youtube_extension.utils.proxy import (  # noqa: E402
    _PROXY_ENV_VAR,
    get_proxy_dict,
    get_proxy_url,
    redact_proxy_credentials,
)

USER = "wsuser"
PASSWORD = "sup3r-s3cret-pw"
PROXY_URL = f"http://{USER}:{PASSWORD}@p.webshare.io:80"

SECRETS = (USER, PASSWORD)


def _assert_no_secrets(text: str) -> None:
    for secret in SECRETS:
        assert secret not in text, f"credential {secret!r} leaked into: {text!r}"


# ---------------------------------------------------------------------------
# get_proxy_url — validation must never raise and never log the URL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(f"http://{USER}:{PASSWORD}@[::1", id="unterminated-ipv6"),
        pytest.param(f"http://{USER}:{PASSWORD}@host:notaport", id="non-numeric-port"),
        pytest.param(f"http://{USER}:{PASSWORD}@host:99999", id="port-out-of-range"),
        pytest.param(f"ftp://{USER}:{PASSWORD}@host:21", id="unsupported-scheme"),
        pytest.param(f"{USER}:{PASSWORD}@host:80", id="no-scheme"),
        pytest.param("http://", id="no-host"),
    ],
)
def test_malformed_proxy_url_returns_none_without_raising(monkeypatch, raw):
    """Malformed values fall back to a direct connection instead of exploding.

    Before the fix, the IPv6 and port cases raised ``ValueError`` out of
    ``urllib.parse``, breaking the documented contract.
    """
    monkeypatch.setenv(_PROXY_ENV_VAR, raw)
    assert get_proxy_url() is None
    assert get_proxy_dict() is None


@pytest.mark.parametrize(
    "raw",
    [
        f"http://{USER}:{PASSWORD}@[::1",
        f"http://{USER}:{PASSWORD}@host:notaport",
        f"ftp://{USER}:{PASSWORD}@host:21",
    ],
)
def test_malformed_proxy_warning_never_contains_credentials(monkeypatch, caplog, raw):
    """The 'malformed' warning names the variable, never its value."""
    monkeypatch.setenv(_PROXY_ENV_VAR, raw)
    with caplog.at_level(logging.WARNING, logger="youtube_extension.utils.proxy"):
        assert get_proxy_url() is None

    assert caplog.records, "expected a warning for a malformed proxy URL"
    for record in caplog.records:
        _assert_no_secrets(record.getMessage())
        assert raw not in record.getMessage()
    assert _PROXY_ENV_VAR in caplog.text


@pytest.mark.parametrize(
    "raw",
    [
        PROXY_URL,
        "https://p.webshare.io",
        f"socks5://{USER}:{PASSWORD}@p.webshare.io:1080",
        f"socks5h://{USER}:{PASSWORD}@p.webshare.io:1080",
    ],
)
def test_valid_proxy_urls_are_returned_verbatim(monkeypatch, raw):
    """A well-formed proxy is passed through untouched — the value is the secret
    the outbound client needs, so redaction belongs at the log boundary only."""
    monkeypatch.setenv(_PROXY_ENV_VAR, raw)
    assert get_proxy_url() == raw
    assert get_proxy_dict() == {"http": raw, "https": raw}


@pytest.mark.parametrize("raw", ["", "   "])
def test_unset_or_blank_proxy_is_direct_connection(monkeypatch, raw):
    monkeypatch.setenv(_PROXY_ENV_VAR, raw)
    assert get_proxy_url() is None
    assert get_proxy_dict() is None


def test_missing_env_var_is_direct_connection(monkeypatch):
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    assert get_proxy_url() is None


# ---------------------------------------------------------------------------
# redact_proxy_credentials
# ---------------------------------------------------------------------------


def test_exact_configured_url_is_redacted_but_host_preserved(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    out = redact_proxy_credentials(f"connect failed via {PROXY_URL} after 3 tries")
    _assert_no_secrets(out)
    assert "p.webshare.io:80" in out, "host should survive so operators can triage"


def test_credentials_are_redacted_even_when_env_var_is_unset(monkeypatch):
    """The generic sweep is what makes this safe for stderr echoes and for
    ``HTTPS_PROXY``-style variables the helper does not own."""
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    out = redact_proxy_credentials(
        f"ERROR: unable to connect to socks5://{USER}:{PASSWORD}@10.0.0.1:1080"
    )
    _assert_no_secrets(out)
    assert "10.0.0.1:1080" in out


def test_credentials_are_redacted_when_they_differ_from_the_env_var(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    out = redact_proxy_credentials("via http://other-user:other-pass@10.0.0.1:1080")
    assert "other-pass" not in out
    assert "other-user" not in out
    assert "10.0.0.1:1080" in out


def test_userinfo_without_password_is_redacted(monkeypatch):
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    out = redact_proxy_credentials(f"http://{USER}@10.0.0.1:1080")
    assert USER not in out
    assert "10.0.0.1:1080" in out


def test_path_containing_at_sign_is_not_over_redacted(monkeypatch):
    """``@`` after a path separator is not userinfo — do not mangle real URLs."""
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    text = "fetched https://example.com/users/a@b.txt ok"
    assert redact_proxy_credentials(text) == text


def test_credentials_with_empty_username_are_redacted(monkeypatch):
    """Userinfo with no username (``http://:secret@host``) still carries a
    password. The generic pass must redact it even when the URL is not the
    configured ``WEBSHARE_PROXY_URL`` (e.g. a different proxy variable)."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    secret = "empty-user-s3cret"
    out = redact_proxy_credentials(
        f"HTTP_PROXY=http://:{secret}@other.example.com:8080"
    )
    assert secret not in out
    assert "***" in out


def test_unencoded_at_sign_in_password_is_fully_redacted(monkeypatch):
    """RFC 3986 requires ``@`` in userinfo to be percent-encoded, but real
    ``*_PROXY`` values are frequently set with a raw ``@`` in the password. The
    userinfo classes must therefore permit ``@`` and rely on greedy backtracking
    to the *last* separator, otherwise the match ends at the first ``@`` and the
    password tail survives into the log line."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    secret = "pa@ss"
    out = redact_proxy_credentials(
        f"HTTPS_PROXY=http://user:{secret}@proxy.internal:8080 connection refused"
    )
    # The tail after the first "@" is the part that used to leak.
    assert "ss@proxy.internal" not in out
    assert secret not in out
    assert "proxy.internal:8080" in out, "host:port must survive for triage"


def test_multiple_at_signs_in_password_are_fully_redacted(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    secret = "se@cr@et"
    out = redact_proxy_credentials(f"http://u:{secret}@h.example.com:1 failed")
    assert secret not in out
    for fragment in ("cr@et", "et@h.example.com"):
        assert fragment not in out
    assert "h.example.com:1" in out


def test_at_sign_greed_does_not_span_two_urls(monkeypatch):
    """Greedy userinfo matching must stay inside one authority. Whitespace and
    ``/`` are excluded from the classes, so a match cannot run from the first
    URL's userinfo to the second URL's ``@``."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    for text in (
        "http://u1:p1@h1.example.com:80 and http://u2:p2@h2.example.com:80",
        "http://u1:p1@h1.example.com:80,http://u2:p2@h2.example.com:80",
    ):
        out = redact_proxy_credentials(text)
        for secret in ("p1", "p2", "u1", "u2"):
            assert secret not in out, f"{secret!r} leaked from {text!r}: {out!r}"
        assert "h1.example.com:80" in out
        assert "h2.example.com:80" in out


def test_fragment_at_sign_is_not_over_redacted(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    text = "opened https://example.com#tag@x done"
    assert redact_proxy_credentials(text) == text


def test_credential_free_url_with_port_is_untouched(monkeypatch):
    """``host:port`` looks like ``user:password`` until the required ``@`` fails
    to appear. Permitting ``@`` in the classes must not make these match."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    for text in (
        "http://proxy.internal:8080/path",
        "http://proxy.internal:8080",
        "http://api.example.com contacted by user@corp.com",
    ):
        assert redact_proxy_credentials(text) == text


def test_query_string_at_sign_is_not_over_redacted(monkeypatch):
    """A query value containing ``@`` must not be mistaken for userinfo: ``?``
    (and ``#``) are authority delimiters, so redaction must stop there."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    text = "fetched https://example.com?email=a@b.com ok"
    assert redact_proxy_credentials(text) == text


@pytest.mark.parametrize(
    "value",
    [None, 42, ValueError("boom"), ["a", "b"], {"k": "v"}],
)
def test_non_string_input_is_coerced_and_never_raises(monkeypatch, value):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    assert isinstance(redact_proxy_credentials(value), str)


def test_object_with_raising_str_returns_placeholder(monkeypatch):
    """The ``never raises`` contract must hold even when ``str(text)`` itself
    fails: an object whose ``__str__`` raises must not defeat the sanitizer and
    mask the original error inside an ``except`` block."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)

    class Unprintable:
        def __str__(self) -> str:
            raise RuntimeError("cannot stringify")

    out = redact_proxy_credentials(Unprintable())
    assert out == "<unprintable error>"
    _assert_no_secrets(out)


def test_redaction_survives_a_malformed_configured_url(monkeypatch):
    """Redaction runs inside ``except`` blocks; a bad env value must not make it
    raise and mask the original error."""
    monkeypatch.setenv(_PROXY_ENV_VAR, f"http://{USER}:{PASSWORD}@[::1")
    out = redact_proxy_credentials(f"boom http://{USER}:{PASSWORD}@[::1 boom")
    assert isinstance(out, str)
    _assert_no_secrets(out)


# ---------------------------------------------------------------------------
# The concrete leak: subprocess errors stringify the whole argv
# ---------------------------------------------------------------------------


def test_called_process_error_argv_is_redacted(monkeypatch):
    """``subprocess.run(..., check=True)`` raises ``CalledProcessError`` whose
    ``str()`` embeds ``--proxy <url-with-credentials>``. That string was logged
    *and* returned in an API error field (CWE-532 / CWE-209)."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    argv = ["yt-dlp", "-x", "--proxy", PROXY_URL, "--", "https://youtu.be/auJzb1D-fag"]
    error = subprocess.CalledProcessError(returncode=1, cmd=argv)

    assert PASSWORD in str(error), "precondition: the raw error does leak"
    _assert_no_secrets(redact_proxy_credentials(error))


def test_timeout_expired_argv_is_redacted(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    argv = ["yt-dlp", "--dump-json", "--proxy", PROXY_URL, "--", "https://youtu.be/x"]
    error = subprocess.TimeoutExpired(cmd=argv, timeout=30)

    assert PASSWORD in str(error), "precondition: the raw error does leak"
    _assert_no_secrets(redact_proxy_credentials(error))


# ---------------------------------------------------------------------------
# "Never raises" is a hard contract: the helper only ever runs inside an
# ``except`` block, so if it raises it masks the original failure entirely --
# no log line, no API response, just a different traceback.
# ---------------------------------------------------------------------------


class _HostileStr(Exception):
    """An exception whose ``__str__`` raises.

    Not hypothetical: third-party errors that format their message lazily can
    fail this way (a missing interpolation key, a repr that touches a closed
    resource), and they surface exactly where this helper is used.
    """

    def __str__(self):
        raise RuntimeError("boom in __str__")


class _HostileRepr:
    def __str__(self):
        raise ValueError("boom in __str__")

    def __repr__(self):
        raise ValueError("boom in __repr__")


def test_unstringifiable_exception_does_not_propagate(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    result = redact_proxy_credentials(_HostileStr())
    assert isinstance(result, str)
    _assert_no_secrets(result)


def test_unstringifiable_plain_object_does_not_propagate(monkeypatch):
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)
    assert isinstance(redact_proxy_credentials(_HostileRepr()), str)


def test_unstringifiable_input_returns_placeholder_not_empty():
    """A silent empty string would make the log line useless; the caller needs
    to be able to tell *why* there is no detail."""
    result = redact_proxy_credentials(_HostileStr())
    assert result.strip(), "placeholder must be non-empty"
    assert "boom" not in result, "must not smuggle the secondary failure through"


def test_redaction_failure_returns_placeholder_not_raw_text(monkeypatch):
    """If the redaction machinery itself fails we must fail *closed*: returning
    the unredacted text would leak the credential this function exists to strip."""
    monkeypatch.setenv(_PROXY_ENV_VAR, PROXY_URL)

    class _ExplodingPattern:
        def sub(self, *_args, **_kwargs):
            raise RuntimeError("regex exploded")

    monkeypatch.setattr(proxy_module, "_USERINFO_RE", _ExplodingPattern())
    result = redact_proxy_credentials(f"failed via {PROXY_URL}")
    _assert_no_secrets(result)
    assert "regex exploded" not in result


def test_hostile_input_still_safe_when_no_proxy_configured(monkeypatch):
    monkeypatch.delenv(_PROXY_ENV_VAR, raising=False)
    assert isinstance(redact_proxy_credentials(_HostileStr()), str)
