"""Unit tests for youtube_extension/backend/worker.py."""

from __future__ import annotations

import asyncio
import json
import sys
from http.server import HTTPServer
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

<<<<<<< HEAD
=======
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

>>>>>>> origin/main
# Ensure the google.cloud stub is available before importing worker
_google_cloud_mock = MagicMock()
_pubsub_mock = MagicMock()
sys.modules.setdefault("google", _google_cloud_mock)
sys.modules.setdefault("google.cloud", _google_cloud_mock)
sys.modules.setdefault("google.cloud.pubsub_v1", _pubsub_mock)

# Stub out heavy service container imports
_container_stub = MagicMock()
sys.modules.setdefault(
    "youtube_extension.backend.containers.service_container", _container_stub
)

import importlib

# We need to import worker *after* stubs are in place
_worker_mod = importlib.import_module("youtube_extension.backend.worker")

process_message = _worker_mod.process_message
run_processing = _worker_mod.run_processing
HealthCheckHandler = _worker_mod.HealthCheckHandler
start_health_check_server = _worker_mod.start_health_check_server
main = _worker_mod.main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(data: dict, message_id: str = "msg-001") -> MagicMock:
    """Return a fake Pub/Sub message object."""
    msg = MagicMock()
    msg.message_id = message_id
    msg.data = json.dumps(data).encode("utf-8")
    return msg


# ===========================================================================
# process_message
# ===========================================================================


class TestProcessMessage:
    def test_ack_when_video_url_missing(self):
        msg = _make_message({"options": {}})
        process_message(msg)
        msg.ack.assert_called_once()
        msg.nack.assert_not_called()

    def test_ack_on_success(self):
        msg = _make_message({"video_url": "https://youtu.be/auJzb1D-fag"})
        with patch.object(_worker_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            process_message(msg)
        msg.ack.assert_called_once()
        msg.nack.assert_not_called()

    def test_nack_on_exception(self):
        msg = _make_message({"video_url": "https://youtu.be/auJzb1D-fag"})
        with patch.object(_worker_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock(side_effect=RuntimeError("boom"))
            process_message(msg)
        msg.nack.assert_called_once()
        msg.ack.assert_not_called()

    def test_ack_when_no_video_url_key(self):
        # data has no 'video_url' key at all
        msg = _make_message({"something": "else"})
        process_message(msg)
        msg.ack.assert_called_once()

    def test_asyncio_run_called_with_coroutine(self):
        """asyncio.run should be invoked when video_url is present."""
        msg = _make_message({"video_url": "https://youtu.be/auJzb1D-fag", "options": {"quality": "hd"}})
        calls = []
        with patch.object(_worker_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock(side_effect=lambda coro: calls.append(coro))
            process_message(msg)
        assert len(calls) == 1

    def test_options_default_to_empty_dict(self):
        """When 'options' key is missing, processing should still proceed."""
        msg = _make_message({"video_url": "https://youtu.be/auJzb1D-fag"})
        with patch.object(_worker_mod, "asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            process_message(msg)
        mock_asyncio.run.assert_called_once()

    def test_nack_when_data_is_invalid_json(self):
        msg = MagicMock()
        msg.message_id = "bad-json"
        msg.data = b"NOT VALID JSON{"
        process_message(msg)
        msg.nack.assert_called_once()


# ===========================================================================
# run_processing
# ===========================================================================


class TestRunProcessing:
    async def test_calls_process_video_basic(self):
        mock_service = AsyncMock()
        mock_service.process_video_basic.return_value = {"status": "ok", "result": {}}

        mock_container = MagicMock()
        mock_container.get_service.return_value = mock_service

        with patch.object(_worker_mod, "get_service_container", return_value=mock_container):
            await run_processing("https://youtu.be/auJzb1D-fag", {})

        mock_service.process_video_basic.assert_awaited_once_with(
            "https://youtu.be/auJzb1D-fag", {}
        )

    async def test_raises_on_service_error(self):
        mock_service = AsyncMock()
        mock_service.process_video_basic.side_effect = ValueError("service down")

        mock_container = MagicMock()
        mock_container.get_service.return_value = mock_service

        with patch.object(_worker_mod, "get_service_container", return_value=mock_container):
            with pytest.raises(ValueError, match="service down"):
                await run_processing("https://youtu.be/auJzb1D-fag", {})

    async def test_logs_status_from_result(self, caplog):
        import logging

        mock_service = AsyncMock()
        mock_service.process_video_basic.return_value = {"status": "complete", "result": {}}

        mock_container = MagicMock()
        mock_container.get_service.return_value = mock_service

        with caplog.at_level(logging.INFO, logger="worker"):
            with patch.object(_worker_mod, "get_service_container", return_value=mock_container):
                await run_processing("https://youtu.be/auJzb1D-fag", {})

        assert any("complete" in r.message for r in caplog.records)

    async def test_passes_options_to_service(self):
        mock_service = AsyncMock()
        mock_service.process_video_basic.return_value = {"status": "ok", "result": {}}

        mock_container = MagicMock()
        mock_container.get_service.return_value = mock_service

        options = {"quality": "hd", "extract_events": True}
        with patch.object(_worker_mod, "get_service_container", return_value=mock_container):
            await run_processing("https://youtu.be/auJzb1D-fag", options)

        mock_service.process_video_basic.assert_awaited_once_with(
            "https://youtu.be/auJzb1D-fag", options
        )


# ===========================================================================
# HealthCheckHandler
# ===========================================================================


class TestHealthCheckHandler:
    def _make_handler(self) -> HealthCheckHandler:
        """Create a HealthCheckHandler without binding to a real server."""
        handler = HealthCheckHandler.__new__(HealthCheckHandler)
        handler.wfile = BytesIO()
        # Patch send_response and end_headers so they don't error
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    def test_do_get_sends_200(self):
        handler = self._make_handler()
        handler.do_GET()
        handler.send_response.assert_called_once_with(200)

    def test_do_get_writes_ok(self):
        handler = self._make_handler()
        handler.do_GET()
        handler.wfile.seek(0)
        assert handler.wfile.read() == b"OK"

    def test_do_get_calls_end_headers(self):
        handler = self._make_handler()
        handler.do_GET()
        handler.end_headers.assert_called_once()

    def test_log_message_suppressed(self):
        """log_message should be a no-op to keep logs clean."""
        handler = self._make_handler()
        # Should not raise
        handler.log_message("%s", "200")


# ===========================================================================
# start_health_check_server
# ===========================================================================


class TestStartHealthCheckServer:
    def test_starts_server_on_default_port(self):
        mock_server = MagicMock()
        mock_server.serve_forever = MagicMock(side_effect=KeyboardInterrupt)

        with patch("youtube_extension.backend.worker.HTTPServer", return_value=mock_server) as MockHTTP:
            with patch.dict("os.environ", {}, clear=False):
                # serve_forever raises to stop immediately
                try:
                    start_health_check_server()
                except KeyboardInterrupt:
                    pass
            MockHTTP.assert_called_once()
            args = MockHTTP.call_args[0]
            assert args[0] == ("0.0.0.0", 8080)

    def test_starts_server_on_env_port(self):
        mock_server = MagicMock()
        mock_server.serve_forever = MagicMock(side_effect=KeyboardInterrupt)

        with patch("youtube_extension.backend.worker.HTTPServer", return_value=mock_server) as MockHTTP:
            with patch.dict("os.environ", {"PORT": "9090"}):
                try:
                    start_health_check_server()
                except KeyboardInterrupt:
                    pass
            args = MockHTTP.call_args[0]
            assert args[0] == ("0.0.0.0", 9090)

    def test_logs_error_on_exception(self, caplog):
        import logging

        with patch(
            "youtube_extension.backend.worker.HTTPServer",
            side_effect=OSError("port in use"),
        ):
            with caplog.at_level(logging.ERROR, logger="worker"):
                start_health_check_server()
        assert any("Failed to start" in r.message for r in caplog.records)


# ===========================================================================
# main
# ===========================================================================


class TestMain:
    def test_main_starts_thread_and_subscriber(self):
        mock_subscriber = MagicMock()
        mock_subscriber.subscription_path.return_value = "projects/proj/subscriptions/sub"
        mock_future = MagicMock()
        mock_future.result.side_effect = KeyboardInterrupt  # stop immediately
        mock_subscriber.subscribe.return_value = mock_future
        mock_subscriber.__enter__ = MagicMock(return_value=mock_subscriber)
        mock_subscriber.__exit__ = MagicMock(return_value=False)

        mock_pubsub = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber

        mock_thread = MagicMock()

        with patch.object(_worker_mod, "pubsub_v1", mock_pubsub):
            with patch("youtube_extension.backend.worker.threading") as mock_threading:
                mock_threading.Thread.return_value = mock_thread
                try:
                    main()
                except KeyboardInterrupt:
                    pass

        mock_threading.Thread.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_main_handles_timeout_error(self):
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        mock_subscriber = MagicMock()
        mock_subscriber.subscription_path.return_value = "projects/proj/subscriptions/sub"
        mock_future = MagicMock()
        # First result() raises TimeoutError, second result() returns normally
        mock_future.result.side_effect = [FuturesTimeoutError(), None]
        mock_subscriber.subscribe.return_value = mock_future
        mock_subscriber.__enter__ = MagicMock(return_value=mock_subscriber)
        mock_subscriber.__exit__ = MagicMock(return_value=False)

        mock_pubsub = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber

        with patch.object(_worker_mod, "pubsub_v1", mock_pubsub):
            with patch("youtube_extension.backend.worker.threading") as mock_threading:
                mock_threading.Thread.return_value = MagicMock()
                main()  # should not raise

        mock_future.cancel.assert_called_once()

    def test_main_handles_general_exception(self):
        mock_subscriber = MagicMock()
        mock_subscriber.subscription_path.return_value = "projects/proj/subscriptions/sub"
        mock_future = MagicMock()
        mock_future.result.side_effect = [RuntimeError("connection lost"), None]
        mock_subscriber.subscribe.return_value = mock_future
        mock_subscriber.__enter__ = MagicMock(return_value=mock_subscriber)
        mock_subscriber.__exit__ = MagicMock(return_value=False)

        mock_pubsub = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber

        with patch.object(_worker_mod, "pubsub_v1", mock_pubsub):
            with patch("youtube_extension.backend.worker.threading") as mock_threading:
                mock_threading.Thread.return_value = MagicMock()
                main()  # should not raise

        mock_future.cancel.assert_called_once()
