"""Unit tests for youtube_extension/backend/services/websocket_service.py."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from youtube_extension.backend.services.websocket_service import (
    WebSocketConnectionManager,
    WebSocketService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ws(accept=None, send_text=None, receive_text=None) -> MagicMock:
    """Return a mock WebSocket with async send/receive."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock() if send_text is None else send_text
    ws.receive_text = AsyncMock() if receive_text is None else receive_text
    return ws


def _make_service(chat_service=None, video_result=None) -> tuple[WebSocketService, MagicMock]:
    """Return a (WebSocketService, connection_manager mock) tuple."""
    manager = MagicMock(spec=WebSocketConnectionManager)
    manager.connect = AsyncMock()
    manager.disconnect = MagicMock()
    manager.send_personal_message = AsyncMock()
    manager.broadcast = AsyncMock()
    manager.active_connections = []

    vps = AsyncMock()
    if video_result is None:
        video_result = {"status": "ok", "result": {"summary": "done"}, "progress": 100.0}
    vps.process_video_basic.return_value = video_result

    svc = WebSocketService(
        connection_manager=manager,
        video_processing_service=vps,
        chat_service=chat_service,
    )
    return svc, manager


# ===========================================================================
# WebSocketConnectionManager
# ===========================================================================


class TestWebSocketConnectionManager:
    async def test_connect_accepts_and_tracks(self):
        mgr = WebSocketConnectionManager()
        ws = _make_ws()
        await mgr.connect(ws)
        ws.accept.assert_awaited_once()
        assert ws in mgr.active_connections

    async def test_connect_increments_connection_count(self):
        mgr = WebSocketConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        assert len(mgr.active_connections) == 2

    def test_disconnect_removes_connection(self):
        mgr = WebSocketConnectionManager()
        ws = _make_ws()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        assert ws not in mgr.active_connections

    def test_disconnect_ignores_unknown_connection(self):
        mgr = WebSocketConnectionManager()
        ws = _make_ws()
        # Should not raise
        mgr.disconnect(ws)

    async def test_send_personal_message_delivers(self):
        mgr = WebSocketConnectionManager()
        ws = _make_ws()
        mgr.active_connections.append(ws)
        await mgr.send_personal_message("hello", ws)
        ws.send_text.assert_awaited_once_with("hello")

    async def test_send_personal_message_disconnects_on_error(self):
        mgr = WebSocketConnectionManager()
        ws = _make_ws()
        ws.send_text = AsyncMock(side_effect=RuntimeError("closed"))
        mgr.active_connections.append(ws)
        await mgr.send_personal_message("hello", ws)
        assert ws not in mgr.active_connections

    async def test_broadcast_sends_to_all(self):
        mgr = WebSocketConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        mgr.active_connections.extend([ws1, ws2])
        await mgr.broadcast("event")
        ws1.send_text.assert_awaited_once_with("event")
        ws2.send_text.assert_awaited_once_with("event")

    async def test_broadcast_removes_failed_connections(self):
        mgr = WebSocketConnectionManager()
        ws_ok = _make_ws()
        ws_bad = _make_ws()
        ws_bad.send_text = AsyncMock(side_effect=RuntimeError("dead"))
        mgr.active_connections.extend([ws_ok, ws_bad])
        await mgr.broadcast("event")
        assert ws_bad not in mgr.active_connections
        assert ws_ok in mgr.active_connections

    async def test_broadcast_empty_connections_no_error(self):
        mgr = WebSocketConnectionManager()
        # no connections – should not raise
        await mgr.broadcast("hello")


# ===========================================================================
# WebSocketService – handle_websocket_connection
# ===========================================================================


class TestHandleWebsocketConnection:
    async def test_sends_welcome_message_on_connect(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        # disconnect immediately after welcome
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        await svc.handle_websocket_connection(ws)

        # First send_personal_message call is the welcome message
        first_call = mgr.send_personal_message.call_args_list[0]
        payload = json.loads(first_call[0][0])
        assert payload["type"] == "connection"
        assert payload["status"] == "connected"

    async def test_connect_called_on_manager(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        await svc.handle_websocket_connection(ws)
        mgr.connect.assert_awaited_once_with(ws)

    async def test_disconnect_called_on_websocket_disconnect(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        await svc.handle_websocket_connection(ws)
        mgr.disconnect.assert_called_with(ws)

    async def test_outer_disconnect_handled_gracefully(self):
        """WebSocketDisconnect raised during welcome-send phase is caught by outer except."""
        svc, mgr = _make_service()
        ws = _make_ws()
        # Raising WebSocketDisconnect from send_personal_message (welcome) triggers outer catch
        mgr.send_personal_message = AsyncMock(side_effect=WebSocketDisconnect())
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        # Should not raise
        await svc.handle_websocket_connection(ws)

    async def test_routes_ping_message(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        ping_msg = json.dumps({"type": "ping", "data": {"id": 1}})
        ws.receive_text = AsyncMock(side_effect=[ping_msg, WebSocketDisconnect()])

        await svc.handle_websocket_connection(ws)

        # Second call (after welcome) should be pong
        second_call = mgr.send_personal_message.call_args_list[1]
        payload = json.loads(second_call[0][0])
        assert payload["type"] == "pong"

    async def test_invalid_json_sends_error_response(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        ws.receive_text = AsyncMock(side_effect=["NOT JSON{{{", WebSocketDisconnect()])

        await svc.handle_websocket_connection(ws)

        second_call = mgr.send_personal_message.call_args_list[1]
        payload = json.loads(second_call[0][0])
        assert payload["type"] == "error"
        assert payload["error_type"] == "json_decode_error"

    async def test_generic_exception_sends_error_response(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        # Force a generic exception during routing
        good_msg = json.dumps({"type": "ping"})
        ws.receive_text = AsyncMock(side_effect=[good_msg, WebSocketDisconnect()])

        with patch.object(svc, "_route_message", side_effect=RuntimeError("unexpected")):
            await svc.handle_websocket_connection(ws)

        second_call = mgr.send_personal_message.call_args_list[1]
        payload = json.loads(second_call[0][0])
        assert payload["type"] == "error"
        assert payload["error_type"] == "internal_error"


# ===========================================================================
# WebSocketService – _route_message
# ===========================================================================


class TestRouteMessage:
    async def test_routes_chat_type(self):
        svc, _ = _make_service()
        result = await svc._route_message({"type": "chat", "message": "hello"})
        assert result["type"] == "chat_response"

    async def test_routes_video_processing_type(self):
        svc, _ = _make_service()
        result = await svc._route_message(
            {"type": "video_processing", "video_url": "https://youtu.be/auJzb1D-fag"}
        )
        assert result["type"] == "video_processing_response"

    async def test_routes_ping_type(self):
        svc, _ = _make_service()
        result = await svc._route_message({"type": "ping"})
        assert result["type"] == "pong"

    async def test_unknown_type_returns_error(self):
        svc, _ = _make_service()
        result = await svc._route_message({"type": "not_a_real_type"})
        assert result["type"] == "error"
        assert result["error_type"] == "unknown_message_type"

    async def test_missing_type_defaults_unknown(self):
        svc, _ = _make_service()
        result = await svc._route_message({})
        assert result["type"] == "error"


# ===========================================================================
# WebSocketService – _handle_chat_message
# ===========================================================================


class TestHandleChatMessage:
    async def test_returns_chat_response_type(self):
        svc, _ = _make_service()
        result = await svc._handle_chat_message({"message": "hi", "session_id": "s1"})
        assert result["type"] == "chat_response"

    async def test_fallback_when_no_chat_service(self):
        svc, _ = _make_service(chat_service=None)
        result = await svc._handle_chat_message({"message": "hello"})
        assert "hello" in result["response"]

    async def test_uses_chat_service_when_available(self):
        chat_svc = AsyncMock()
        chat_svc.process_chat_message.return_value = "AI says hello"
        svc, _ = _make_service(chat_service=chat_svc)
        result = await svc._handle_chat_message({"message": "hi", "session_id": "sess"})
        assert result["response"] == "AI says hello"
        chat_svc.process_chat_message.assert_awaited_once_with("hi", "sess")

    async def test_chat_service_error_returns_fallback_message(self):
        chat_svc = AsyncMock()
        chat_svc.process_chat_message.side_effect = RuntimeError("timeout")
        svc, _ = _make_service(chat_service=chat_svc)
        result = await svc._handle_chat_message({"message": "help"})
        assert result["type"] == "chat_response"
        assert "timeout" in result["response"]

    async def test_session_id_defaults_to_default(self):
        svc, _ = _make_service()
        result = await svc._handle_chat_message({"message": "test"})
        assert result["session_id"] == "default"

    async def test_returns_success_status(self):
        svc, _ = _make_service()
        result = await svc._handle_chat_message({"message": "hi"})
        assert result["status"] == "success"

    async def test_outer_exception_returns_error_response(self):
        svc, _ = _make_service()
        # Force an outer exception by patching the inner logic
        with patch.object(svc, "chat_service", new=None):
            # Make the "else" branch raise by patching str.__format__
            result = await svc._handle_chat_message(None)  # type: ignore[arg-type]
        # Should gracefully return error dict
        assert result["type"] == "error"


# ===========================================================================
# WebSocketService – _handle_video_processing_message
# ===========================================================================


class TestHandleVideoProcessingMessage:
    async def test_returns_error_when_video_url_missing(self):
        svc, _ = _make_service()
        result = await svc._handle_video_processing_message({})
        assert result["type"] == "error"
        assert result["error_type"] == "missing_video_url"

    async def test_returns_video_processing_response_on_success(self):
        svc, _ = _make_service(
            video_result={"status": "ok", "result": {"summary": "done"}, "progress": 75.0}
        )
        result = await svc._handle_video_processing_message(
            {"video_url": "https://youtu.be/auJzb1D-fag"}
        )
        assert result["type"] == "video_processing_response"
        assert result["status"] == "ok"

    async def test_passes_options_to_processing_service(self):
        svc, _ = _make_service(
            video_result={"status": "ok", "result": {}, "progress": 100.0}
        )
        await svc._handle_video_processing_message(
            {"video_url": "https://youtu.be/auJzb1D-fag", "options": {"hd": True}}
        )
        svc.video_processing_service.process_video_basic.assert_awaited_once_with(
            "https://youtu.be/auJzb1D-fag", {"hd": True}
        )

    async def test_returns_error_response_when_processing_fails(self):
        svc, _ = _make_service()
        svc.video_processing_service.process_video_basic.side_effect = RuntimeError("fail")
        result = await svc._handle_video_processing_message(
            {"video_url": "https://youtu.be/auJzb1D-fag"}
        )
        assert result["type"] == "video_processing_response"
        assert result["status"] == "error"
        assert "fail" in result["result"]["error"]

    async def test_progress_defaults_to_100(self):
        svc, _ = _make_service(
            video_result={"status": "ok", "result": {}}
        )
        result = await svc._handle_video_processing_message(
            {"video_url": "https://youtu.be/auJzb1D-fag"}
        )
        assert result["progress"] == 100.0

    async def test_inner_processing_exception_returns_video_response_with_error_status(self):
        """Inner exceptions from the processing service result in a video_processing_response with error status."""
        svc, _ = _make_service()
        svc.video_processing_service.process_video_basic.side_effect = ValueError("inner fail")
        result = await svc._handle_video_processing_message(
            {"video_url": "https://youtu.be/auJzb1D-fag"}
        )
        assert result["type"] == "video_processing_response"
        assert result["status"] == "error"
        assert "inner fail" in result["result"]["error"]


# ===========================================================================
# WebSocketService – _handle_ping_message
# ===========================================================================


class TestHandlePingMessage:
    def test_returns_pong_type(self):
        svc, _ = _make_service()
        result = svc._handle_ping_message({"type": "ping", "data": {}})
        assert result["type"] == "pong"

    def test_includes_original_message_data(self):
        svc, _ = _make_service()
        result = svc._handle_ping_message({"type": "ping", "data": {"seq": 42}})
        assert result["original_message"] == {"seq": 42}

    def test_has_timestamp(self):
        svc, _ = _make_service()
        result = svc._handle_ping_message({})
        assert "timestamp" in result

    def test_missing_data_key_defaults_to_empty_dict(self):
        svc, _ = _make_service()
        result = svc._handle_ping_message({"type": "ping"})
        assert result["original_message"] == {}


# ===========================================================================
# WebSocketService – _create_error_response
# ===========================================================================


class TestCreateErrorResponse:
    def test_type_is_error(self):
        svc, _ = _make_service()
        resp = svc._create_error_response("oops")
        assert resp["type"] == "error"

    def test_message_preserved(self):
        svc, _ = _make_service()
        resp = svc._create_error_response("something broke")
        assert resp["message"] == "something broke"

    def test_default_error_type(self):
        svc, _ = _make_service()
        resp = svc._create_error_response("oops")
        assert resp["error_type"] == "error"

    def test_custom_error_type(self):
        svc, _ = _make_service()
        resp = svc._create_error_response("bad request", "validation_error")
        assert resp["error_type"] == "validation_error"

    def test_has_timestamp(self):
        svc, _ = _make_service()
        resp = svc._create_error_response("oops")
        assert "timestamp" in resp


# ===========================================================================
# WebSocketService – broadcast_system_message
# ===========================================================================


class TestBroadcastSystemMessage:
    async def test_broadcasts_to_manager(self):
        svc, mgr = _make_service()
        await svc.broadcast_system_message("server restart")
        mgr.broadcast.assert_awaited_once()
        call_args = mgr.broadcast.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["message"] == "server restart"

    async def test_default_message_type_is_system(self):
        svc, mgr = _make_service()
        await svc.broadcast_system_message("update")
        call_args = mgr.broadcast.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["type"] == "system"

    async def test_custom_message_type(self):
        svc, mgr = _make_service()
        await svc.broadcast_system_message("alert!", "alert")
        call_args = mgr.broadcast.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["type"] == "alert"

    async def test_error_during_broadcast_does_not_raise(self):
        svc, mgr = _make_service()
        mgr.broadcast = AsyncMock(side_effect=RuntimeError("network error"))
        # Should not raise
        await svc.broadcast_system_message("hello")


# ===========================================================================
# WebSocketService – send_progress_update
# ===========================================================================


class TestSendProgressUpdate:
    async def test_sends_progress_message(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        await svc.send_progress_update(ws, 50.0, "halfway there")
        mgr.send_personal_message.assert_awaited_once()
        call_args = mgr.send_personal_message.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["type"] == "progress"
        assert payload["progress"] == 50.0
        assert payload["message"] == "halfway there"

    async def test_data_defaults_to_empty_dict(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        await svc.send_progress_update(ws, 0.0)
        call_args = mgr.send_personal_message.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["data"] == {}

    async def test_custom_data_included(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        await svc.send_progress_update(ws, 80.0, "almost", {"frames": 240})
        call_args = mgr.send_personal_message.call_args[0][0]
        payload = json.loads(call_args)
        assert payload["data"] == {"frames": 240}

    async def test_error_does_not_raise(self):
        svc, mgr = _make_service()
        ws = _make_ws()
        mgr.send_personal_message = AsyncMock(side_effect=RuntimeError("dead"))
        # Should not propagate
        await svc.send_progress_update(ws, 50.0)


# ===========================================================================
# WebSocketService – get_connection_stats
# ===========================================================================


class TestGetConnectionStats:
    def test_returns_active_connection_count(self):
        svc, mgr = _make_service()
        mgr.active_connections = [_make_ws(), _make_ws(), _make_ws()]
        stats = svc.get_connection_stats()
        assert stats["active_connections"] == 3

    def test_has_timestamp_key(self):
        svc, _ = _make_service()
        stats = svc.get_connection_stats()
        assert "timestamp" in stats

    def test_returns_zero_when_no_connections(self):
        svc, mgr = _make_service()
        mgr.active_connections = []
        stats = svc.get_connection_stats()
        assert stats["active_connections"] == 0


# ===========================================================================
# WebSocketConnectionManager.broadcast – fan-out concurrency
# ===========================================================================


class TestBroadcastFanOut:
    """broadcast() must issue sends in parallel, not one connection at a time.

    A sequential loop makes every client wait for the ones ahead of it, so a
    single slow peer delays delivery to the entire fleet (head-of-line
    blocking). These tests fail against a serialised implementation.
    """

    @staticmethod
    def _tracking_ws(state, delay=0.01):
        """A mock WebSocket that records peak concurrent send_text() calls."""
        ws = _make_ws()

        async def _send(_message):
            state["inflight"] += 1
            state["peak"] = max(state["peak"], state["inflight"])
            await asyncio.sleep(delay)
            state["inflight"] -= 1

        ws.send_text = AsyncMock(side_effect=_send)
        return ws

    async def test_sends_are_concurrent_not_serialised(self):
        mgr = WebSocketConnectionManager()
        state = {"inflight": 0, "peak": 0}
        n = 5
        mgr.active_connections.extend(self._tracking_ws(state) for _ in range(n))

        await mgr.broadcast("event")

        assert state["peak"] == n, (
            f"broadcast() peaked at {state['peak']} concurrent send(s) for {n} "
            "connections - sends are serialised (head-of-line blocking)"
        )

    async def test_slow_peer_does_not_delay_other_peers(self):
        mgr = WebSocketConnectionManager()
        completed: list[str] = []

        def _ws(name, delay):
            ws = _make_ws()

            async def _send(_message):
                await asyncio.sleep(delay)
                completed.append(name)

            ws.send_text = AsyncMock(side_effect=_send)
            return ws

        # The slow peer is first in the list: under a sequential loop it blocks
        # both fast peers behind it and therefore completes first.
        mgr.active_connections.extend(
            [_ws("slow", 0.05), _ws("fast-1", 0.0), _ws("fast-2", 0.0)]
        )

        await mgr.broadcast("event")

        assert completed == ["fast-1", "fast-2", "slow"], (
            f"completion order was {completed}; a slow peer at the head of the "
            "connection list delayed delivery to the fast peers behind it"
        )

    async def test_all_peers_still_receive_the_message(self):
        mgr = WebSocketConnectionManager()
        conns = [_make_ws() for _ in range(4)]
        mgr.active_connections.extend(conns)

        await mgr.broadcast("payload")

        for ws in conns:
            ws.send_text.assert_awaited_once_with("payload")

    async def test_failures_are_isolated_and_only_bad_peers_removed(self):
        mgr = WebSocketConnectionManager()
        ok_1, ok_2 = _make_ws(), _make_ws()
        bad_1, bad_2 = _make_ws(), _make_ws()
        bad_1.send_text = AsyncMock(side_effect=RuntimeError("peer gone"))
        bad_2.send_text = AsyncMock(side_effect=ConnectionResetError("reset"))
        # Failing peers first: a raising send must not abort the whole fan-out.
        mgr.active_connections.extend([bad_1, ok_1, bad_2, ok_2])

        await mgr.broadcast("event")

        ok_1.send_text.assert_awaited_once_with("event")
        ok_2.send_text.assert_awaited_once_with("event")
        assert mgr.active_connections == [ok_1, ok_2], (
            "expected only the failing peers to be dropped, got "
            f"{len(mgr.active_connections)} surviving connection(s)"
        )

    async def test_empty_connection_list_issues_no_sends(self):
        mgr = WebSocketConnectionManager()
        # Must not raise and must not construct an empty gather.
        await mgr.broadcast("event")
        assert mgr.active_connections == []

    async def test_cancelled_send_is_re_raised_not_swallowed(self):
        """gather(return_exceptions=True) captures CancelledError; broadcast must not eat it.

        The pre-fan-out implementation used `except Exception`, so a
        CancelledError raised by send_text escaped broadcast(). Collecting it
        into `results` and filtering on `Exception` would silently drop it.
        """
        mgr = WebSocketConnectionManager()
        ok = _make_ws()
        cancelled = _make_ws()
        cancelled.send_text = AsyncMock(side_effect=asyncio.CancelledError())
        mgr.active_connections.extend([ok, cancelled])

        with pytest.raises(asyncio.CancelledError):
            await mgr.broadcast("event")

    async def test_cancellation_does_not_leak_dead_peers(self):
        """Ordinary failures are still cleaned up before the cancellation propagates."""
        mgr = WebSocketConnectionManager()
        ok = _make_ws()
        dead = _make_ws()
        dead.send_text = AsyncMock(side_effect=RuntimeError("peer gone"))
        cancelled = _make_ws()
        cancelled.send_text = AsyncMock(side_effect=asyncio.CancelledError())
        mgr.active_connections.extend([ok, dead, cancelled])

        with pytest.raises(asyncio.CancelledError):
            await mgr.broadcast("event")

        assert mgr.active_connections == [ok, cancelled], (
            "the failed peer must still be dropped even though the broadcast "
            f"was cancelled, got {mgr.active_connections}"
        )
