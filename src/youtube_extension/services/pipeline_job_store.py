"""File-backed persistence for async video / pipeline jobs."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path(os.getenv("UVAI_JOB_STORE_DIR", "data/jobs"))


class PipelineJobStore:
    """JSON file store for VideoJobStatusResponse-shaped records."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root or _DEFAULT_ROOT)
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


_job_store: Optional[PipelineJobStore] = None


def get_job_store() -> PipelineJobStore:
    global _job_store
    if _job_store is None:
        _job_store = PipelineJobStore()
    return _job_store
