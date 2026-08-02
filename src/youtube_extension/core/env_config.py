"""Validated parsing of environment overrides for tunable runtime constants.

Several services expose performance knobs -- worker-pool sizes, RPC deadlines --
as module-level constants so they are cheap to read on hot paths. Making those
knobs operator-tunable means reading ``os.environ`` at import time, and that is
exactly where a bare ``int(os.getenv(...))`` is most dangerous: a typo in a
deployment manifest stops being a configuration error and becomes an
unimportable module, surfacing as a confusing traceback far from its cause.

These helpers centralise that parsing so every tunable behaves identically:

* **Absent or blank falls back.** Unset, empty, and whitespace-only values all
  return the caller's default, so a deployment that sets nothing keeps the
  shipped behaviour byte-for-byte. Blank is treated as unset deliberately --
  Compose and Helm templates routinely render an empty string for an
  unconfigured value, and that should mean "default", not "invalid".
* **Malformed fails fast, loudly.** Anything else must parse and satisfy the
  documented bound. Out-of-range values raise rather than being silently
  clamped, because clamping hides an operator's typo behind behaviour they did
  not ask for. The raised ``ValueError`` names the variable and echoes the
  offending input, so the message is self-describing at startup.

The fail-fast half is a deliberate trade: an invalid override takes the process
down at import rather than running with a value nobody chose. For a
concurrency limit or a deadline, running with a silently-substituted value is
the worse outcome -- it is the kind of misconfiguration that only reveals
itself under production load.
"""

from __future__ import annotations

import math
import os

__all__ = ["positive_int_env", "positive_finite_float_env"]


def _raw_override(name: str) -> str | None:
    """Return the stripped override for ``name``, or ``None`` to use the default.

    Blank and whitespace-only values are folded into ``None`` so that every
    caller treats "rendered but empty" identically to "never set".
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


def positive_int_env(name: str, default: int) -> int:
    """Read a positive integer override, failing fast on invalid configuration.

    Args:
        name: Environment variable to read.
        default: Value used when the variable is unset or blank.

    Returns:
        The parsed override, or ``default`` when no override is present.

    Raises:
        ValueError: The variable is set to something that is not an integer, or
            to an integer below 1.
    """
    raw = _raw_override(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer >= 1, got {raw!r}") from None
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {raw!r}")
    return value


def positive_finite_float_env(name: str, default: float) -> float:
    """Read a positive, finite float override, failing fast on invalid configuration.

    ``float()`` happily accepts ``inf``/``-inf``/``nan``. An infinite timeout
    would silently remove a deadline (or be rejected downstream by gRPC timeout
    validation), and ``nan`` compares false against every bound, so non-finite
    values are rejected outright rather than clamped into range.

    Args:
        name: Environment variable to read.
        default: Value used when the variable is unset or blank.

    Returns:
        The parsed override, or ``default`` when no override is present.

    Raises:
        ValueError: The variable is set to something that is not a number, or to
            a value that is not both positive and finite.
    """
    raw = _raw_override(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(
            f"{name} must be a positive, finite number of seconds, got {raw!r}"
        ) from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"{name} must be a positive, finite number of seconds, got {raw!r}"
        )
    return value
