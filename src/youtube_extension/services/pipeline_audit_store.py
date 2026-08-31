"""In-memory + file audit trail for pipeline agent stages."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = Path(os.getenv("UVAI_AUDIT_STORE_DIR", "data/audit"))


class PipelineAuditStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or _DEFAULT_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)
        self._buffer: dict[str, list[dict[str, Any]]] = {}

    def append(
        self,
        run_id: str,
        *,
        agent_id: str,
        action: str,
        success: bool,
        duration_ms: float,
        details: dict[str, Any] | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "agent_id": agent_id,
            "action": action,
            "success": success,
            "duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "details": details or {},
        }
        self._buffer.setdefault(run_id, []).append(entry)
        path = self.root / f"{run_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_run(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self._buffer:
            return list(self._buffer[run_id])
        path = self.root / f"{run_id}.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def list_runs(self, limit: int = 20) -> list[str]:
        files = sorted(self.root.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.stem for p in files[:limit]]


_audit_store: PipelineAuditStore | None = None


def get_audit_store() -> PipelineAuditStore:
    global _audit_store
    if _audit_store is None:
        _audit_store = PipelineAuditStore()
    return _audit_store
