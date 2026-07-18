"""Lifecycle coverage for the production FastAPI entrypoint."""

from unittest.mock import AsyncMock

import pytest

from youtube_extension import main as main_module


@pytest.fixture
def monitor(monkeypatch):
    """Replace the process-global monitor without constructing another database."""
    fake = AsyncMock()
    monkeypatch.setattr(main_module, "cost_monitor", fake, raising=False)
    return fake


async def test_app_lifespan_starts_and_closes_cost_monitor(monitor) -> None:
    async with main_module.app.router.lifespan_context(main_module.app):
        monitor.start.assert_awaited_once_with()
        monitor.close.assert_not_awaited()

    monitor.close.assert_awaited_once_with()


async def test_app_lifespan_closes_monitor_when_startup_fails(monitor) -> None:
    startup_error = RuntimeError("monitor startup failed")
    monitor.start.side_effect = startup_error

    with pytest.raises(RuntimeError, match="monitor startup failed") as raised:
        async with main_module.app.router.lifespan_context(main_module.app):
            pytest.fail("the application must not serve after failed startup")

    assert raised.value is startup_error
    monitor.close.assert_awaited_once_with()


async def test_startup_error_is_not_masked_when_cleanup_also_fails(monitor) -> None:
    startup_error = RuntimeError("monitor startup failed")
    monitor.start.side_effect = startup_error
    monitor.close.side_effect = RuntimeError("monitor cleanup failed")

    with pytest.raises(RuntimeError, match="monitor startup failed") as raised:
        async with main_module.app.router.lifespan_context(main_module.app):
            pytest.fail("the application must not serve after failed startup")

    assert raised.value is startup_error
    monitor.close.assert_awaited_once_with()


async def test_application_error_is_not_masked_when_shutdown_cleanup_fails(
    monitor,
) -> None:
    application_error = RuntimeError("application failed")
    monitor.close.side_effect = RuntimeError("monitor cleanup failed")

    with pytest.raises(RuntimeError, match="application failed") as raised:
        async with main_module.app.router.lifespan_context(main_module.app):
            raise application_error

    assert raised.value is application_error
    monitor.close.assert_awaited_once_with()
