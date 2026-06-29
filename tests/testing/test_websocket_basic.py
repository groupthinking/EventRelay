import json
from starlette.testclient import TestClient

from src.youtube_extension.processors.video_processor import default_processor as video_processor


def test_websocket_chat_flow():
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Receive welcome message
        welcome_raw = websocket.receive_text()
        welcome = json.loads(welcome_raw)
        assert welcome["type"] == "connection"
        assert welcome["status"] == "connected"

        # Send chat message
        websocket.send_text(
            json.dumps({
                "type": "chat",
                "message": "Hello there!",
                "session_id": "test-session-1"
            })
        )

        # Receive chat response
        response_raw = websocket.receive_text()
        response = json.loads(response_raw)
        assert response["type"] == "chat_response"
        assert response["status"] == "success"
        assert "response" in response


def test_websocket_missing_video_url():
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Drain welcome
        _ = json.loads(websocket.receive_text())

        websocket.send_text(
            json.dumps({
                "type": "video_processing",
                "video_url": "",
                "options": {}
            })
        )

        reply = json.loads(websocket.receive_text())
        # Should be standardized error due to missing URL
        assert reply["type"] == "error"
        assert reply["error_type"] == "missing_video_url"
        assert "Video URL required" in reply["message"]
