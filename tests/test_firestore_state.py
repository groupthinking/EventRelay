#!/usr/bin/env python3
"""
Tests for Firestore State Service
==================================

Tests for cloud-native state management using Firestore.
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Skip tests if Firestore not available
pytest.importorskip("google.cloud.firestore")

from src.youtube_extension.services.cloud.firestore_state import (
    FirestoreStateService,
    VideoProcessingState,
)


class TestVideoProcessingState:
    """Test VideoProcessingState dataclass"""

    def test_create_state(self):
        """Test creating a processing state"""
        state = VideoProcessingState(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            status="pending",
            current_stage="metadata"
        )

        assert state.video_id == "test123"
        assert state.status == "pending"
        assert state.current_stage == "metadata"

    def test_to_dict(self):
        """Test converting state to dictionary"""
        state = VideoProcessingState(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            status="pending",
            current_stage="metadata"
        )

        data = state.to_dict()

        assert data["video_id"] == "test123"
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """Test creating state from dictionary"""
        data = {
            "video_id": "test123",
            "video_url": "https://youtube.com/watch?v=test123",
            "status": "completed",
            "current_stage": "complete",
            "metadata": {"title": "Test Video"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:10:00Z",
        }

        state = VideoProcessingState.from_dict(data)

        assert state.video_id == "test123"
        assert state.status == "completed"
        assert state.metadata == {"title": "Test Video"}


@pytest.mark.asyncio
class TestFirestoreStateService:
    """Test FirestoreStateService"""

    @pytest.fixture
    async def mock_firestore_client(self):
        """Mock Firestore client"""
        with patch("src.youtube_extension.services.cloud.firestore_state.firestore") as mock_firestore:
            mock_client = AsyncMock()
            mock_firestore.AsyncClient.return_value = mock_client
            yield mock_client

    @pytest.fixture
    async def service(self, mock_firestore_client):
        """Create service instance with mocked client"""
        service = FirestoreStateService(
            project_id="test-project",
            collection_name="test_collection"
        )
        await service.initialize()
        return service

    async def test_initialize(self, service):
        """Test service initialization"""
        assert service.db is not None
        assert service.project_id == "test-project"
        assert service.collection_name == "test_collection"

    async def test_create_state(self, service, mock_firestore_client):
        """Test creating a new state"""
        # Mock collection and document
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc.set = AsyncMock()
        mock_collection.document.return_value = mock_doc
        mock_firestore_client.collection.return_value = mock_collection

        # Create state
        state = await service.create_state(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123"
        )

        assert state.video_id == "test123"
        assert state.status == "pending"
        assert state.current_stage == "metadata"
        mock_doc.set.assert_called_once()

    async def test_get_state_cache_hit(self, service):
        """Test getting state from cache"""
        # Add to cache
        state = VideoProcessingState(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            status="processing",
            current_stage="analysis"
        )
        service._local_cache["test123"] = state
        service._cache_timestamps["test123"] = datetime.now(timezone.utc)

        # Get from cache
        result = await service.get_state("test123")

        assert result == state
        assert result.video_id == "test123"

    async def test_get_state_from_firestore(self, service, mock_firestore_client):
        """Test getting state from Firestore when not in cache"""
        # Mock Firestore response
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = AsyncMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "video_id": "test123",
            "video_url": "https://youtube.com/watch?v=test123",
            "status": "completed",
            "current_stage": "complete",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:10:00Z",
        }
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore_client.collection.return_value = mock_collection

        # Get state
        state = await service.get_state("test123")

        assert state.video_id == "test123"
        assert state.status == "completed"

    async def test_update_state(self, service, mock_firestore_client):
        """Test updating state"""
        # Create initial state in cache
        initial_state = VideoProcessingState(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            status="pending",
            current_stage="metadata"
        )
        service._local_cache["test123"] = initial_state
        service._cache_timestamps["test123"] = datetime.now(timezone.utc)

        # Mock Firestore update
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc.update = AsyncMock()
        mock_collection.document.return_value = mock_doc
        mock_firestore_client.collection.return_value = mock_collection

        # Update state
        updated_state = await service.update_state(
            video_id="test123",
            status="processing",
            current_stage="analysis",
            metadata={"title": "Test Video"}
        )

        assert updated_state.status == "processing"
        assert updated_state.current_stage == "analysis"
        assert updated_state.metadata == {"title": "Test Video"}
        mock_doc.update.assert_called_once()

    async def test_delete_state(self, service, mock_firestore_client):
        """Test deleting state"""
        # Add to cache
        service._local_cache["test123"] = VideoProcessingState(
            video_id="test123",
            video_url="https://youtube.com/watch?v=test123",
            status="completed",
            current_stage="complete"
        )

        # Mock Firestore delete
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc.delete = AsyncMock()
        mock_collection.document.return_value = mock_doc
        mock_firestore_client.collection.return_value = mock_collection

        # Delete state
        await service.delete_state("test123")

        assert "test123" not in service._local_cache
        mock_doc.delete.assert_called_once()

    async def test_list_states(self, service, mock_firestore_client):
        """Test listing states"""
        # Mock Firestore query
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.where = Mock(return_value=mock_query)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)

        # Mock query results
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {
            "video_id": "test1",
            "video_url": "https://youtube.com/watch?v=test1",
            "status": "pending",
            "current_stage": "metadata",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {
            "video_id": "test2",
            "video_url": "https://youtube.com/watch?v=test2",
            "status": "pending",
            "current_stage": "metadata",
            "created_at": "2024-01-01T00:01:00Z",
            "updated_at": "2024-01-01T00:01:00Z",
        }

        mock_query.get = AsyncMock(return_value=[mock_doc1, mock_doc2])
        mock_collection.where = Mock(return_value=mock_query)
        mock_firestore_client.collection.return_value = mock_collection

        # List states
        states = await service.list_states(status="pending", limit=10)

        assert len(states) == 2
        assert states[0].video_id == "test1"
        assert states[1].video_id == "test2"

    async def test_close(self, service):
        """Test closing the service"""
        await service.close()
        assert service.db is None


@pytest.mark.asyncio
async def test_get_firestore_service():
    """Test getting singleton service instance"""
    from src.youtube_extension.services.cloud.firestore_state import (
        get_firestore_service,
        cleanup_firestore_service,
    )

    with patch("src.youtube_extension.services.cloud.firestore_state.firestore"):
        service1 = await get_firestore_service()
        service2 = await get_firestore_service()

        # Should be the same instance
        assert service1 is service2

        # Cleanup
        await cleanup_firestore_service()
