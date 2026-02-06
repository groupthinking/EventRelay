"""
Tests for CloudEvents Publisher
-------------------------------
Tests CloudEvents v1.0 compliance and multi-backend publishing.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integration.cloudevents_publisher import (
    CloudEvent,
    CloudEventsPublisher,
    create_publisher,
)


class TestCloudEvent:
    """Test CloudEvent structure and serialization."""
    
    def test_cloudevent_creation(self):
        """Test basic CloudEvent creation."""
        event = CloudEvent(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"}
        )
        
        assert event.source == "/test/source"
        assert event.type == "com.example.test"
        assert event.specversion == "1.0"
        assert event.data == {"key": "value"}
        assert isinstance(event.id, str)
        assert isinstance(event.time, datetime)
    
    def test_cloudevent_to_dict(self):
        """Test CloudEvent serialization to dict."""
        event = CloudEvent(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"},
            subject="test-subject"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["id"] == event.id
        assert event_dict["source"] == "/test/source"
        assert event_dict["specversion"] == "1.0"
        assert event_dict["type"] == "com.example.test"
        assert event_dict["subject"] == "test-subject"
        assert event_dict["data"] == {"key": "value"}
        assert "time" in event_dict
    
    def test_cloudevent_to_json(self):
        """Test CloudEvent JSON serialization."""
        event = CloudEvent(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"}
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["source"] == "/test/source"
        assert parsed["type"] == "com.example.test"
        assert parsed["data"]["key"] == "value"
    
    def test_cloudevent_extensions(self):
        """Test CloudEvent with extension attributes."""
        event = CloudEvent(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"},
            custom_extension="extension_value",
            another_field=123
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["custom_extension"] == "extension_value"
        assert event_dict["another_field"] == 123


class TestCloudEventsPublisher:
    """Test CloudEvents publisher with different backends."""
    
    @pytest.mark.asyncio
    async def test_file_backend(self, tmp_path):
        """Test publishing to file backend."""
        file_path = tmp_path / "events.jsonl"
        
        publisher = CloudEventsPublisher(
            backend="file",
            file_path=str(file_path)
        )
        
        event_id = await publisher.publish(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"}
        )
        
        assert event_id is not None
        assert file_path.exists()
        
        # Verify file content
        content = file_path.read_text()
        event_data = json.loads(content.strip())
        
        assert event_data["source"] == "/test/source"
        assert event_data["type"] == "com.example.test"
        assert event_data["data"]["key"] == "value"
        
        await publisher.close()
    
    @pytest.mark.asyncio
    @patch("src.integration.cloudevents_publisher.pubsub_v1.PublisherClient")
    async def test_pubsub_backend(self, mock_publisher_class):
        """Test publishing to Pub/Sub backend."""
        # Mock Pub/Sub client
        mock_client = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "message-123"
        mock_client.publish.return_value = mock_future
        mock_publisher_class.return_value = mock_client
        
        publisher = CloudEventsPublisher(
            backend="pubsub",
            project_id="test-project",
            topic_name="test-topic"
        )
        
        event_id = await publisher.publish(
            source="/test/source",
            type="com.example.test",
            data={"key": "value"}
        )
        
        assert event_id is not None
        mock_client.publish.assert_called_once()
        
        await publisher.close()
    
    @pytest.mark.asyncio
    async def test_http_backend(self):
        """Test publishing to HTTP webhook backend."""
        with patch("src.integration.cloudevents_publisher.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            publisher = CloudEventsPublisher(
                backend="http",
                webhook_url="https://example.com/webhook"
            )
            
            event_id = await publisher.publish(
                source="/test/source",
                type="com.example.test",
                data={"key": "value"}
            )
            
            assert event_id is not None
            mock_client.post.assert_called_once()
            
            # Verify CloudEvents HTTP binding
            call_args = mock_client.post.call_args
            assert "application/cloudevents+json" in str(call_args)
            
            await publisher.close()
    
    @pytest.mark.asyncio
    async def test_openwhisk_backend(self):
        """Test publishing to OpenWhisk backend."""
        with patch("src.integration.cloudevents_publisher.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            publisher = CloudEventsPublisher(
                backend="openwhisk",
                openwhisk_api_host="https://openwhisk.example.com",
                openwhisk_auth="user:pass",
                openwhisk_namespace="test-namespace"
            )
            
            event_id = await publisher.publish(
                source="/test/source",
                type="com.example.video.analyzed",
                data={"key": "value"}
            )
            
            assert event_id is not None
            mock_client.post.assert_called_once()
            
            # Verify OpenWhisk trigger URL
            call_args = mock_client.post.call_args
            assert "triggers" in str(call_args)
            assert "test-namespace" in str(call_args)
            
            await publisher.close()
    
    def test_create_publisher_from_env(self):
        """Test factory function with environment variables."""
        with patch.dict(os.environ, {
            "CLOUDEVENTS_BACKEND": "file",
            "EVENTS_FILE_PATH": "/tmp/test-events.jsonl"
        }):
            publisher = create_publisher()
            
            assert publisher.backend == "file"
            assert publisher.file_path == "/tmp/test-events.jsonl"


class TestCloudEventsIntegration:
    """Integration tests for CloudEvents publishing."""
    
    @pytest.mark.asyncio
    async def test_video_event_publishing(self, tmp_path):
        """Test publishing video analysis event."""
        file_path = tmp_path / "video_events.jsonl"
        
        publisher = CloudEventsPublisher(
            backend="file",
            file_path=str(file_path)
        )
        
        # Simulate video analysis event
        event_id = await publisher.publish(
            source="/video-analyzer/gemini",
            type="com.eventrelay.video.analyzed",
            data={
                "video_url": "https://youtube.com/watch?v=example",
                "summary": "Test video analysis",
                "events": [
                    {"timestamp": "1:30", "type": "code_change"}
                ]
            },
            subject="https://youtube.com/watch?v=example",
            dataschema="https://eventrelay.com/schemas/video-analysis/v1"
        )
        
        assert event_id is not None
        
        # Verify event
        content = file_path.read_text()
        event_data = json.loads(content.strip())
        
        assert event_data["type"] == "com.eventrelay.video.analyzed"
        assert event_data["source"] == "/video-analyzer/gemini"
        assert event_data["subject"] == "https://youtube.com/watch?v=example"
        assert "video_url" in event_data["data"]
        
        await publisher.close()
    
    @pytest.mark.asyncio
    async def test_multiple_events(self, tmp_path):
        """Test publishing multiple events."""
        file_path = tmp_path / "multi_events.jsonl"
        
        publisher = CloudEventsPublisher(
            backend="file",
            file_path=str(file_path)
        )
        
        # Publish multiple events
        for i in range(3):
            await publisher.publish(
                source="/test/source",
                type=f"com.example.test.{i}",
                data={"index": i}
            )
        
        # Verify all events written
        content = file_path.read_text()
        events = [json.loads(line) for line in content.strip().split("\n")]
        
        assert len(events) == 3
        assert events[0]["type"] == "com.example.test.0"
        assert events[1]["type"] == "com.example.test.1"
        assert events[2]["type"] == "com.example.test.2"
        
        await publisher.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
