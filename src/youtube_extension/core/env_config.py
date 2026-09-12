"""Safe parsing for operator-tunable environment values.

Runtime tuning must not make a service unimportable. Unset or invalid overrides
therefore use the shipped default and emit a warning that names the variable.
Integer settings may also declare a hard maximum when an unbounded value would
create unsafe resource fan-out.
"""

from __future__ import annotations

import logging
import math
import os

__all__ = ["positive_int_env", "positive_finite_float_env"]

logger = logging.getLogger(__name__)


def _raw_override(name: str) -> str | None:
    """Return the stripped override, or ``None`` when it is unset."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


def _fallback(
    name: str, raw: str, default: int | float, requirement: str
) -> int | float:
    logger.warning(
        "Ignoring invalid %s=%r; expected %s. Using default %r.",
        name,
        raw,
        requirement,
        default,
    )
    return default


def positive_int_env(
    name: str,
    default: int,
    *,
    maximum: int | None = None,
) -> int:
    """Read a positive integer override, falling back safely when invalid."""
    raw = _raw_override(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return int(_fallback(name, raw, default, "an integer >= 1"))
    if value < 1:
        return int(_fallback(name, raw, default, "an integer >= 1"))
    if maximum is not None and value > maximum:
        return int(_fallback(name, raw, default, f"an integer between 1 and {maximum}"))
    return value


def positive_finite_float_env(name: str, default: float) -> float:
    """Read a positive finite float override, falling back safely when invalid."""
    raw = _raw_override(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return float(_fallback(name, raw, default, "a positive, finite number"))
    if not math.isfinite(value) or value <= 0:
        return float(_fallback(name, raw, default, "a positive, finite number"))
    return value
