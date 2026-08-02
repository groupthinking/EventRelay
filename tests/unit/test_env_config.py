"""Tests for the shared environment-override parsers.

``tests/unit/test_firestore_state.py`` already exercises these helpers through
the constants they back. This module covers them at their canonical location,
plus the two things that can only be observed end to end:

* the error messages name the offending variable, so a misconfiguration is
  diagnosable from the startup log alone; and
* the constants really are wired at **import time**, which is checked by
  importing the module under test in a subprocess with the override set.
  A subprocess is used deliberately: ``importlib.reload`` would rebind the
  module's classes and leave the rest of the session holding stale references.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import youtube_extension
from youtube_extension.core.env_config import (
    positive_finite_float_env,
    positive_int_env,
)

_VAR = "ENV_CONFIG_TEST_VALUE"

# Directory that must be on PYTHONPATH for a subprocess to import the package.
_SRC_ROOT = str(Path(youtube_extension.__file__).resolve().parent.parent)


# ===========================================================================
# positive_int_env
# ===========================================================================


class TestPositiveIntEnv:
    def test_unset_falls_back_to_default(self):
        os.environ.pop(_VAR, None)
        assert positive_int_env(_VAR, 8) == 8

    @pytest.mark.parametrize("raw", ["", "   ", "\t", "\n"])
    def test_blank_falls_back_to_default(self, raw):
        """Compose/Helm render an empty string for an unconfigured value."""
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            assert positive_int_env(_VAR, 8) == 8

    @pytest.mark.parametrize(("raw", "expected"), [("1", 1), ("3", 3), (" 12 ", 12)])
    def test_parses_valid_override(self, raw, expected):
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            assert positive_int_env(_VAR, 8) == expected

    @pytest.mark.parametrize("raw", ["0", "-1", "-42"])
    def test_rejects_non_positive(self, raw):
        """Out of range raises rather than clamping, so a typo is not masked."""
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            with pytest.raises(ValueError, match=">= 1"):
                positive_int_env(_VAR, 8)

    @pytest.mark.parametrize("raw", ["abc", "1.5", "inf", "nan", "8x", "0x10"])
    def test_rejects_malformed(self, raw):
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            with pytest.raises(ValueError, match="must be an integer >= 1"):
                positive_int_env(_VAR, 8)

    def test_error_names_variable_and_echoes_input(self):
        with patch.dict(os.environ, {_VAR: "oops"}, clear=False):
            with pytest.raises(ValueError) as excinfo:
                positive_int_env(_VAR, 8)
        message = str(excinfo.value)
        assert _VAR in message
        assert "oops" in message

    def test_malformed_error_does_not_chain_raw_int_error(self):
        """``from None`` keeps the confusing built-in message out of the log."""
        with patch.dict(os.environ, {_VAR: "abc"}, clear=False):
            with pytest.raises(ValueError) as excinfo:
                positive_int_env(_VAR, 8)
        assert excinfo.value.__cause__ is None


# ===========================================================================
# positive_finite_float_env
# ===========================================================================


class TestPositiveFiniteFloatEnv:
    def test_unset_falls_back_to_default(self):
        os.environ.pop(_VAR, None)
        assert positive_finite_float_env(_VAR, 30.0) == 30.0

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_falls_back_to_default(self, raw):
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            assert positive_finite_float_env(_VAR, 30.0) == 30.0

    @pytest.mark.parametrize(
        ("raw", "expected"), [("12.5", 12.5), (" 0.25 ", 0.25), ("5", 5.0)]
    )
    def test_parses_valid_override(self, raw, expected):
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            assert positive_finite_float_env(_VAR, 30.0) == expected

    @pytest.mark.parametrize(
        "raw", ["inf", "Infinity", "-inf", "nan", "NaN", "0", "0.0", "-1"]
    )
    def test_rejects_non_finite_and_non_positive(self, raw):
        """``float()`` accepts inf/nan; an infinite deadline is not a deadline."""
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            with pytest.raises(ValueError, match="positive, finite"):
                positive_finite_float_env(_VAR, 30.0)

    @pytest.mark.parametrize("raw", ["abc", "1.2.3", "12s"])
    def test_rejects_malformed(self, raw):
        with patch.dict(os.environ, {_VAR: raw}, clear=False):
            with pytest.raises(ValueError, match="positive, finite"):
                positive_finite_float_env(_VAR, 30.0)

    def test_error_names_variable_and_echoes_input(self):
        with patch.dict(os.environ, {_VAR: "later"}, clear=False):
            with pytest.raises(ValueError) as excinfo:
                positive_finite_float_env(_VAR, 30.0)
        message = str(excinfo.value)
        assert _VAR in message
        assert "later" in message


# ===========================================================================
# Import-time wiring of the tunable constants
# ===========================================================================


def _import_constant(module: str, constant: str, override: str | None):
    """Import ``module`` in a clean interpreter and report ``constant``.

    Redis is not installed in the test environment, so the stub that
    ``test_intelligent_cache.py`` installs is reproduced here for the child
    process. Returns the ``CompletedProcess`` so callers can assert on both the
    printed value and a fail-fast non-zero exit.
    """
    code = (
        "import sys, types;"
        "m = types.ModuleType('redis');"
        "a = types.ModuleType('redis.asyncio');"
        "a.Redis = object;"
        "a.ConnectionPool = object;"
        "a.from_url = lambda url, **kw: None;"
        "m.asyncio = a;"
        "sys.modules['redis'] = m;"
        "sys.modules['redis.asyncio'] = a;"
        f"import {module} as mod;"
        f"print(mod.{constant})"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = _SRC_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env.pop(constant, None)
    if override is not None:
        env[constant] = override
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


_CACHE_MODULE = "youtube_extension.backend.services.intelligent_cache"
_FIRESTORE_MODULE = "youtube_extension.services.cloud.firestore_state"


class TestTunableConstantWiring:
    """The acceptance criterion that matters: unset env == shipped behaviour."""

    @pytest.mark.parametrize(
        ("module", "constant", "default"),
        [
            (_CACHE_MODULE, "TAG_WRITE_CONCURRENCY", "8"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_CONCURRENCY", "16"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_TIMEOUT_SECONDS", "30.0"),
        ],
    )
    def test_unset_keeps_shipped_default(self, module, constant, default):
        result = _import_constant(module, constant, None)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == default

    @pytest.mark.parametrize(
        ("module", "constant", "override"),
        [
            (_CACHE_MODULE, "TAG_WRITE_CONCURRENCY", "3"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_CONCURRENCY", "4"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_TIMEOUT_SECONDS", "2.5"),
        ],
    )
    def test_override_is_applied_at_import(self, module, constant, override):
        result = _import_constant(module, constant, override)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == override

    @pytest.mark.parametrize(
        ("module", "constant"),
        [
            (_CACHE_MODULE, "TAG_WRITE_CONCURRENCY"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_CONCURRENCY"),
            (_FIRESTORE_MODULE, "CLEANUP_DELETE_TIMEOUT_SECONDS"),
        ],
    )
    def test_invalid_override_fails_fast_at_import(self, module, constant):
        """A bad value must stop the process, not run with a value nobody chose."""
        result = _import_constant(module, constant, "0")
        assert result.returncode != 0
        assert constant in result.stderr
