"""API readiness must include the API-cost database substrate."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from youtube_extension import main


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
