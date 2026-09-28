"""API readiness must include the API-cost database substrate."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from youtube_extension import main


def test_bootstrap_dev_database_creates_sqlite_parent_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./.runtime/app.db")
    monkeypatch.delenv("API_COST_DATABASE_URL", raising=False)

    runtime_dir = tmp_path / ".runtime"
    assert not runtime_dir.exists()

    main._bootstrap_dev_database()

    assert runtime_dir.exists()
    assert runtime_dir.is_dir()


def test_bootstrap_dev_database_ignores_non_sqlite_urls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/eventrelay")
    monkeypatch.delenv("API_COST_DATABASE_URL", raising=False)

    runtime_dir = tmp_path / ".runtime"
    main._bootstrap_dev_database()

    assert not runtime_dir.exists()


@pytest.mark.asyncio
async def test_readyz_succeeds_when_api_cost_database_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = AsyncMock()
    monkeypatch.setattr(main, "ensure_api_cost_ready", check)
    monkeypatch.setattr(main, "_API_V1_ROUTER_LOADED", True)

    response = await main.readiness_check()

    assert response == {"status": "ready", "service": "uvai-backend"}
    check.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_ensure_api_cost_ready_bootstraps_dev_database_before_readiness_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    def _bootstrap() -> None:
        call_order.append("bootstrap")

    async def _ensure() -> None:
        call_order.append("ensure")

    monkeypatch.setattr(main, "_bootstrap_dev_database", _bootstrap)
    monkeypatch.setattr(
        "youtube_extension.backend.services.api_cost_monitor.ensure_api_cost_database_ready",
        _ensure,
    )

    await main.ensure_api_cost_ready()

    assert call_order == ["bootstrap", "ensure"]


@pytest.mark.asyncio
async def test_readyz_returns_503_when_api_cost_database_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "ensure_api_cost_ready",
        AsyncMock(side_effect=RuntimeError("missing runtime DML grant")),
    )
    monkeypatch.setattr(main, "_API_V1_ROUTER_LOADED", True)

    with pytest.raises(HTTPException) as error:
        await main.readiness_check()

    assert error.value.status_code == 503
    assert error.value.detail == "API cost database is not ready"


@pytest.mark.asyncio
async def test_readyz_returns_503_when_api_v1_router_failed_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = AsyncMock()
    monkeypatch.setattr(main, "ensure_api_cost_ready", check)
    monkeypatch.setattr(main, "_API_V1_ROUTER_LOADED", False)

    with pytest.raises(HTTPException) as error:
        await main.readiness_check()

    assert error.value.status_code == 503
    assert error.value.detail == "API v1 router is not ready"
    check.assert_not_awaited()
