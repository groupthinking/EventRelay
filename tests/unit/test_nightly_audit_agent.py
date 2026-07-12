from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _load_audit_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "nightly_audit_agent.py"
    spec = importlib.util.spec_from_file_location("nightly_audit_agent", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_scan_logs_uses_extended_72_hour_timeframe(tmp_path, monkeypatch):
    module = _load_audit_module()
    monkeypatch.chdir(tmp_path)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    timestamp = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    (log_dir / "structured_logs.jsonl").write_text(
        f'{{"timestamp": "{timestamp}", "status_code": 503, "message": "stale outage"}}\n'
    )

    agent = module.AuditAgent(dry_run=True)
    agent.health_service = None
    await agent._scan_logs()

    assert agent.lookback_hours == 72
    assert any("stale outage" in issue["description"] for issue in agent.issues)


class _RecordingMetricsService:
    def __init__(self):
        self.started = False
        self.stopped = False
        self.persisted = False
        self.samples = 0

    async def start_collection(self):
        self.started = True

    async def stop_collection(self):
        self.stopped = True

    async def get_system_metrics(self):
        self.samples += 1
        return {"timestamp": datetime.now(timezone.utc).isoformat()}

    async def persist_metrics(self):
        self.persisted = True


@pytest.mark.asyncio
async def test_run_audit_collects_active_measurements_before_analysis(tmp_path, monkeypatch):
    module = _load_audit_module()
    monkeypatch.chdir(tmp_path)

    metrics_service = _RecordingMetricsService()
    agent = module.AuditAgent(
        dry_run=True,
        active_measurement=True,
        measurement_samples=2,
        measurement_interval=0,
    )
    agent.health_service = None
    agent.metrics_service = metrics_service

    await agent.run_audit()

    assert metrics_service.started is True
    assert metrics_service.samples == 2
    assert metrics_service.persisted is True
    assert metrics_service.stopped is True


@pytest.mark.asyncio
async def test_active_measurement_uses_fallback_when_metrics_service_unavailable(
    tmp_path, monkeypatch
):
    module = _load_audit_module()
    monkeypatch.chdir(tmp_path)

    agent = module.AuditAgent(
        dry_run=True,
        active_measurement=True,
        measurement_samples=2,
        measurement_interval=0,
    )
    agent.metrics_service = None

    await agent._collect_active_measurements()

    metrics_file = tmp_path / "logs" / "active_measurements.jsonl"
    lines = metrics_file.read_text().strip().splitlines()
    assert len(lines) == 2
    assert any("ACTIVE MEASUREMENT" in line for line in agent.report)
