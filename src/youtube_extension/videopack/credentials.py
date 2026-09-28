"""Resolve Upstash REST credentials (mirrors apps/web billing redis-credentials)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UpstashRestCredentials:
    url: str
    token: str


def resolve_upstash_redis_credentials() -> Optional[UpstashRestCredentials]:
    url = (
        (os.getenv("UPSTASH_REDIS_REST_URL") or "").strip()
        or (os.getenv("KV_REST_API_URL") or "").strip()
    )
    token = (
        (os.getenv("UPSTASH_REDIS_REST_TOKEN") or "").strip()
        or (os.getenv("KV_REST_API_TOKEN") or "").strip()
    )
    if url and token:
        return UpstashRestCredentials(url=url.rstrip("/"), token=token)
    return None


def is_production_runtime() -> bool:
    for name in ("ENVIRONMENT", "VERCEL_ENV", "NODE_ENV"):
        if (os.getenv(name) or "").strip().lower() == "production":
            return True
    return False


def filesystem_store_explicitly_allowed() -> bool:
    return (os.getenv("VIDEO_PACK_FILESYSTEM_STORE") or "").strip() == "1"
