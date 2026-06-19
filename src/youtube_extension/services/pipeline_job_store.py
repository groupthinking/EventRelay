"""Durable persistence for async video / pipeline jobs.

Supports two backends:
- File-based JSON store (default, suitable for single-instance dev)
- Redis store (production, survives restarts and scales across instances)

Backend is selected via UVAI_JOB_STORE_BACKEND env var ('file' | 'redis').
"""

from __future__ import annotations

import abc
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class JobStore(abc.ABC):
    """Abstract interface for job persistence."""

    @abc.abstractmethod
    def save(self, job_id: str, payload: dict[str, Any]) -> None: ...

    @abc.abstractmethod
    def load(self, job_id: str) -> Optional[dict[str, Any]]: ...

    @abc.abstractmethod
    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]: ...

    @abc.abstractmethod
    def delete(self, job_id: str) -> None: ...


class FileJobStore(JobStore):
    """JSON file store for VideoJobStatusResponse-shaped records."""

    def __init__(self, root: Optional[Path] = None) -> None:
        _default_root = Path(os.getenv("UVAI_JOB_STORE_DIR", "data/jobs"))
        self.root = Path(root or _default_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe = job_id.replace("/", "_")
        return self.root / f"{safe}.json"

    def save(self, job_id: str, payload: dict[str, Any]) -> None:
        path = self._path(job_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, job_id: str) -> Optional[dict[str, Any]]:
        path = self._path(job_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Corrupt job record %s", job_id)
            return None

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        records: list[dict[str, Any]] = []
        for path in files[:limit]:
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return records

    def delete(self, job_id: str) -> None:
        path = self._path(job_id)
        if path.exists():
            path.unlink()


class RedisJobStore(JobStore):
    """Redis-backed job store for production multi-instance deployments."""

    _KEY_PREFIX = "uvai:job:"
    _INDEX_KEY = "uvai:jobs:recent"
    _DEFAULT_TTL = 60 * 60 * 24 * 7  # 7 days

    def __init__(self) -> None:
        try:
            import redis
        except ImportError:
            raise ImportError("redis package required: pip install redis")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._ttl = int(os.getenv("UVAI_JOB_TTL_SECONDS", str(self._DEFAULT_TTL)))

    def save(self, job_id: str, payload: dict[str, Any]) -> None:
        key = f"{self._KEY_PREFIX}{job_id}"
        self._client.setex(key, self._ttl, json.dumps(payload, ensure_ascii=False))
        # Maintain a sorted set of recent jobs by timestamp
        self._client.zadd(self._INDEX_KEY, {job_id: time.time()})
        # Trim index to latest 500 entries
        self._client.zremrangebyrank(self._INDEX_KEY, 0, -501)

    def load(self, job_id: str) -> Optional[dict[str, Any]]:
        key = f"{self._KEY_PREFIX}{job_id}"
        raw = self._client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Corrupt Redis job record %s", job_id)
            return None

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        job_ids = self._client.zrevrange(self._INDEX_KEY, 0, limit - 1)
        if not job_ids:
            return []
        keys = [f"{self._KEY_PREFIX}{jid}" for jid in job_ids]
        raw_values = self._client.mget(keys)
        records: list[dict[str, Any]] = []
        for raw in raw_values:
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return records

    def delete(self, job_id: str) -> None:
        key = f"{self._KEY_PREFIX}{job_id}"
        self._client.delete(key)
        self._client.zrem(self._INDEX_KEY, job_id)


# Backward-compatible aliases
PipelineJobStore = FileJobStore

_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get the configured job store singleton.

    Backend is selected via UVAI_JOB_STORE_BACKEND env var:
    - 'file' (default): File-based JSON store
    - 'redis': Redis-backed store (requires REDIS_URL)
    """
    global _job_store
    if _job_store is None:
        backend = os.getenv("UVAI_JOB_STORE_BACKEND", "file").lower()
        if backend == "redis":
            try:
                _job_store = RedisJobStore()
                logger.info("Using Redis job store")
            except ImportError as exc:
                logger.warning("Redis package not installed (%s), falling back to file store", exc)
                _job_store = FileJobStore()
            except Exception as exc:
                logger.error("Redis connection failed (%s), falling back to file store", exc)
                _job_store = FileJobStore()
        else:
            _job_store = FileJobStore()
    return _job_store
