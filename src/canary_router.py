from __future__ import annotations

import hashlib
from typing import Any

from .feature_flags import get_flag, is_enabled


def _hash_to_percentage(key: str) -> int:
    hash_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(hash_digest[:8], 16) % 100


def route_user(user_id: str, namespace: str, flag: str) -> str:
    """Return 'canary' or 'stable' for a given user and flag.

    Rules:
      - if disabled -> stable
      - if in blocklist -> stable
      - if in allowlist -> canary
      - else -> percentage rollout using sha256(user_id)
    """
    if not is_enabled(namespace, flag):
        return "stable"

    cfg = get_flag(namespace, flag)
    allow = set(cfg.get("allowlist", []))
    block = set(cfg.get("blocklist", []))
    pct = int(cfg.get("percentage", 0))

    key = user_id.lower()
    if key in block:
        return "stable"
    if key in allow:
        return "canary"

    bucket = _hash_to_percentage(key)
    return "canary" if bucket < pct else "stable"
