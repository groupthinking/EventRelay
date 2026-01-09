from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CACHE: dict[str, Any] | None = None


def _flags_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "config" / "feature_flags.json"


def _load_flags() -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = _flags_path()
    with path.open("r", encoding="utf-8") as f:
        _CACHE = json.load(f)
    return _CACHE


def is_enabled(namespace: str, flag: str) -> bool:
    flags = _load_flags()
    cfg = flags.get(namespace, {}).get(flag, {})
    return bool(cfg.get("enabled", False))


def get_flag(namespace: str, flag: str) -> dict[str, Any]:
    flags = _load_flags()
    return flags.get(namespace, {}).get(flag, {})


