"""Unit tests for youtube_extension/orchestrator/main.py.

Covers the hardened Redis Streams consumer-group bootstrap (the paths this PR is
meant to harden) plus the credential-redaction and stub-handler contracts. The
Redis client is mocked, so these run without a live Redis or the redis-py package.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from youtube_extension.orchestrator.main import (
    ensure_consumer_group,
    process,
    redact_url,
)

# ---------------------------------------------------------------------------
# ensure_consumer_group — the core of the hardening fix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_consumer_group_creates_when_absent() -> None:
    client = AsyncMock()
    await ensure_consumer_group(client, "stream", "group")
    client.xgroup_create.assert_awaited_once_with(
        "stream", "group", id="0", mkstream=True
    )


@pytest.mark.asyncio
async def test_ensure_consumer_group_tolerates_busygroup() -> None:
    client = AsyncMock()
    client.xgroup_create.side_effect = Exception(
        "BUSYGROUP Consumer Group name already exists"
    )
    # Must NOT raise: an existing group is the expected idempotent case.
    await ensure_consumer_group(client, "stream", "group")


@pytest.mark.asyncio
async def test_ensure_consumer_group_reraises_transient_errors() -> None:
    client = AsyncMock()
    client.xgroup_create.side_effect = Exception(
        "Error 111 connecting to localhost:6379. Connection refused."
    )
    # A transient ConnectionError must propagate so the caller retries instead of
    # silently proceeding without a group (which would stall on NOGROUP forever).
    with pytest.raises(Exception, match="Connection refused"):
        await ensure_consumer_group(client, "stream", "group")


# ---------------------------------------------------------------------------
# redact_url — credentials must never reach logs
# ---------------------------------------------------------------------------

def test_redact_url_strips_credentials() -> None:
    redacted = redact_url("redis://admin:supersecret@redis.internal:6379/1")
    assert "supersecret" not in redacted
    assert "redis.internal" in redacted


def test_redact_url_passthrough_without_credentials() -> None:
    assert redact_url("redis://localhost:6379") == "redis://localhost:6379"


def test_redact_url_never_raises_on_garbage() -> None:
    # Malformed input must degrade to a safe placeholder, never throw.
    assert redact_url("::not a url::") is not None


# ---------------------------------------------------------------------------
# process — REAL_MODE_ONLY: no silent fake success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_fails_loudly_until_implemented() -> None:
    # The stub must raise so the consumer never xack's unprocessed work.
    with pytest.raises(NotImplementedError):
        await process({"field": "value"})


@pytest.mark.asyncio
async def test_main_loop_with_redis(monkeypatch) -> None:
    from unittest.mock import MagicMock, patch
    import youtube_extension.orchestrator.main as orch_main
    
    mock_stop_event = MagicMock()
    mock_stop_event.is_set.side_effect = [False, True]
    
    mock_redis_client = AsyncMock()
    mock_redis = MagicMock()
    mock_redis.from_url.return_value = mock_redis_client
    
    mock_loop = MagicMock()
    
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("ORCHESTRATOR_QUEUE_NAME", "test_stream")
    monkeypatch.setenv("ORCHESTRATOR_CONSUMER_GROUP", "test_group")
    
    with patch("asyncio.get_running_loop", return_value=mock_loop), \
         patch("asyncio.Event", return_value=mock_stop_event), \
         patch("youtube_extension.orchestrator.main.redis", mock_redis), \
         patch("youtube_extension.orchestrator.main.ensure_consumer_group", new_callable=AsyncMock) as mock_ensure:
         
        mock_redis_client.xreadgroup.return_value = [
            ("test_stream", [("msg_id", {"data": "val"})])
        ]
        
        await orch_main.main()
        
        mock_redis.from_url.assert_called_once()
        mock_ensure.assert_called_once_with(mock_redis_client, "test_stream", "test_group")
        mock_redis_client.xreadgroup.assert_called_once()
        mock_redis_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_main_loop_standby() -> None:
    from unittest.mock import MagicMock, patch
    import youtube_extension.orchestrator.main as orch_main
    
    mock_stop_event = MagicMock()
    mock_stop_event.is_set.side_effect = [False, True]
    mock_loop = MagicMock()
    
    with patch("asyncio.get_running_loop", return_value=mock_loop), \
         patch("asyncio.Event", return_value=mock_stop_event), \
         patch("youtube_extension.orchestrator.main.redis", None), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
         
        await orch_main.main()
        mock_sleep.assert_called_once_with(60)

