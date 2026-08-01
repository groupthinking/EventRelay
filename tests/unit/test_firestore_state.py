"""Unit tests for FirestoreStateService and VideoProcessingState.

Tests cover:
- VideoProcessingState dataclass (to_dict, from_dict)
- FirestoreStateService lifecycle (init, initialize, close)
- Collection access and cache logic
- CRUD operations (create, get, update, delete)
- list_states and cleanup_old_states
- Module-level singleton helpers (get_firestore_service, cleanup_firestore_service)

Since google-cloud-firestore is NOT installed, all tests that exercise
FirestoreStateService must patch FIRESTORE_AVAILABLE=True and supply a
fake `firestore` module object on the target module.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make sure src/ is on the path (mirrors other unit tests in this project)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# Import the module under test.  FIRESTORE_AVAILABLE will be False because
# google-cloud-firestore is not installed – that is fine; we patch it per test.
# ---------------------------------------------------------------------------
import youtube_extension.services.cloud.firestore_state as _mod

MODULE_PATH = "youtube_extension.services.cloud.firestore_state"


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _make_fake_firestore() -> MagicMock:
    """Return a minimal fake `firestore` module object."""
    fake = MagicMock(name="firestore")
    # AsyncClient constructor returns a mock db
    fake.AsyncClient = MagicMock(return_value=MagicMock(name="AsyncClient_instance"))
    # Query.DESCENDING used in list_states
    fake.Query = MagicMock()
    fake.Query.DESCENDING = "DESCENDING"
    return fake


def _make_mock_db() -> MagicMock:
    """Return a mock Firestore AsyncClient with chainable collection/document mocks."""
    db = MagicMock(name="db")
    db.close = AsyncMock()

    # Build a chainable mock: db.collection(...).document(...).set/get/update/delete
    doc_ref = MagicMock(name="doc_ref")
    doc_ref.set = AsyncMock()
    doc_ref.update = AsyncMock()
    doc_ref.delete = AsyncMock()

    doc_snapshot = MagicMock(name="doc_snapshot")
    doc_snapshot.exists = True
    doc_snapshot.to_dict = MagicMock(return_value={
        "video_id": "vid123",
        "video_url": "https://youtube.com/watch?v=vid123",
        "status": "pending",
        "current_stage": "metadata",
        "metadata": None,
        "transcript": None,
        "ai_analysis": None,
        "error_message": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": None,
        "processing_time": None,
    })
    doc_ref.get = AsyncMock(return_value=doc_snapshot)

    collection_ref = MagicMock(name="collection_ref")
    collection_ref.document = MagicMock(return_value=doc_ref)

    # query chaining: .where(...) → query; .order_by(...) → query; .limit(...) → query
    query = MagicMock(name="query")
    query.where = MagicMock(return_value=query)
    query.order_by = MagicMock(return_value=query)
    query.limit = MagicMock(return_value=query)
    query.get = AsyncMock(return_value=[])

    collection_ref.where = MagicMock(return_value=query)
    collection_ref.order_by = MagicMock(return_value=query)
    # collection_ref itself is returned by db.collection(...)
    db.collection = MagicMock(return_value=collection_ref)

    return db, doc_ref, doc_snapshot, collection_ref, query


def _make_service_with_db(
    enable_cache: bool = True,
    cache_ttl: int = 300,
    project_id: str = "test-project",
) -> tuple:
    """Return (service, fake_firestore, db, doc_ref, doc_snapshot, coll_ref, query)
    with FIRESTORE_AVAILABLE=True and a fully wired mock db."""
    fake_firestore = _make_fake_firestore()
    db, doc_ref, doc_snapshot, coll_ref, query = _make_mock_db()
    fake_firestore.AsyncClient.return_value = db

    with (
        patch.object(_mod, "FIRESTORE_AVAILABLE", True),
        patch.object(_mod, "firestore", fake_firestore),
    ):
        svc = _mod.FirestoreStateService(
            project_id=project_id,
            enable_cache=enable_cache,
            cache_ttl=cache_ttl,
        )
        svc.db = db  # pre-initialise so tests don't need to call initialize()

    return svc, fake_firestore, db, doc_ref, doc_snapshot, coll_ref, query


# ===========================================================================
# VideoProcessingState — dataclass tests
# ===========================================================================


class TestVideoProcessingState:
    """Tests for the VideoProcessingState dataclass."""

    def _make_state(self, **kwargs) -> _mod.VideoProcessingState:
        defaults = dict(
            video_id="vid1",
            video_url="https://youtube.com/watch?v=vid1",
            status="pending",
            current_stage="metadata",
        )
        defaults.update(kwargs)
        return _mod.VideoProcessingState(**defaults)

    # --- to_dict ---

    def test_to_dict_returns_dict(self):
        state = self._make_state()
        result = state.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_updated_at_always_set(self):
        state = self._make_state()
        result = state.to_dict()
        assert result["updated_at"] is not None
        assert "T" in result["updated_at"]  # ISO format sanity

    def test_to_dict_created_at_set_when_missing(self):
        state = self._make_state(created_at=None)
        result = state.to_dict()
        assert result["created_at"] is not None

    def test_to_dict_preserves_existing_created_at(self):
        ts = "2023-06-01T12:00:00+00:00"
        state = self._make_state(created_at=ts)
        result = state.to_dict()
        assert result["created_at"] == ts

    def test_to_dict_contains_all_fields(self):
        state = self._make_state()
        result = state.to_dict()
        expected_keys = {
            "video_id", "video_url", "status", "current_stage",
            "metadata", "transcript", "ai_analysis", "error_message",
            "created_at", "updated_at", "processing_time",
        }
        assert expected_keys.issubset(result.keys())

    def test_to_dict_optional_fields_default_none(self):
        state = self._make_state()
        result = state.to_dict()
        assert result["metadata"] is None
        assert result["transcript"] is None
        assert result["ai_analysis"] is None
        assert result["error_message"] is None
        assert result["processing_time"] is None

    def test_to_dict_optional_fields_preserved(self):
        state = self._make_state(
            metadata={"title": "Test"},
            transcript={"text": "hello"},
            ai_analysis={"summary": "good"},
            error_message="oops",
            processing_time=1.23,
        )
        result = state.to_dict()
        assert result["metadata"] == {"title": "Test"}
        assert result["transcript"] == {"text": "hello"}
        assert result["ai_analysis"] == {"summary": "good"}
        assert result["error_message"] == "oops"
        assert result["processing_time"] == 1.23

    # --- from_dict ---

    def test_from_dict_round_trip(self):
        state = self._make_state(
            metadata={"title": "Test"},
            processing_time=2.5,
        )
        d = state.to_dict()
        restored = _mod.VideoProcessingState.from_dict(d)
        assert restored.video_id == state.video_id
        assert restored.video_url == state.video_url
        assert restored.status == state.status
        assert restored.current_stage == state.current_stage
        assert restored.metadata == state.metadata
        assert restored.processing_time == state.processing_time

    def test_from_dict_returns_instance(self):
        data = {
            "video_id": "v1",
            "video_url": "https://youtube.com/watch?v=v1",
            "status": "completed",
            "current_stage": "complete",
            "metadata": None,
            "transcript": None,
            "ai_analysis": None,
            "error_message": None,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T01:00:00+00:00",
            "processing_time": 10.0,
        }
        state = _mod.VideoProcessingState.from_dict(data)
        assert isinstance(state, _mod.VideoProcessingState)
        assert state.video_id == "v1"
        assert state.status == "completed"
        assert state.processing_time == 10.0


# ===========================================================================
# FirestoreStateService — __init__
# ===========================================================================


class TestFirestoreStateServiceInit:
    """Tests for FirestoreStateService.__init__."""

    def test_raises_import_error_when_unavailable(self):
        with patch.object(_mod, "FIRESTORE_AVAILABLE", False):
            with pytest.raises(ImportError, match="Firestore not available"):
                _mod.FirestoreStateService()

    def test_succeeds_when_available(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService(project_id="proj")
        assert svc.project_id == "proj"

    def test_defaults_project_id_from_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
        assert svc.project_id == "env-project"

    def test_custom_collection_name(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService(collection_name="my_collection")
        assert svc.collection_name == "my_collection"

    def test_cache_enabled_by_default(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
        assert svc.enable_cache is True
        assert svc.cache_ttl == 300

    def test_cache_disabled(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService(enable_cache=False, cache_ttl=60)
        assert svc.enable_cache is False
        assert svc.cache_ttl == 60

    def test_db_is_none_before_initialize(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
        assert svc.db is None

    def test_local_cache_dicts_empty(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
        assert svc._local_cache == {}
        assert svc._cache_timestamps == {}


# ===========================================================================
# FirestoreStateService — initialize / close
# ===========================================================================


class TestFirestoreStateServiceLifecycle:
    """Tests for initialize() and close()."""

    async def test_initialize_creates_async_client(self):
        fake_fs = _make_fake_firestore()
        mock_db = MagicMock(name="db")
        fake_fs.AsyncClient.return_value = mock_db

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService(project_id="p1")
            await svc.initialize()

        fake_fs.AsyncClient.assert_called_once_with(project="p1")
        assert svc.db is mock_db

    async def test_initialize_is_idempotent(self):
        fake_fs = _make_fake_firestore()
        existing_db = MagicMock(name="existing_db")

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService(project_id="p1")
            svc.db = existing_db  # already initialised
            await svc.initialize()

        # AsyncClient should NOT be called a second time
        fake_fs.AsyncClient.assert_not_called()
        assert svc.db is existing_db

    async def test_close_calls_db_close_and_sets_none(self):
        svc, _, db, *_ = _make_service_with_db()
        db.close = AsyncMock()

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", _make_fake_firestore()),
        ):
            await svc.close()

        db.close.assert_awaited_once()
        assert svc.db is None

    async def test_close_is_idempotent_when_db_is_none(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
            svc.db = None
            # Should not raise
            await svc.close()


# ===========================================================================
# FirestoreStateService — _get_collection
# ===========================================================================


class TestGetCollection:
    """Tests for _get_collection()."""

    def test_raises_runtime_error_if_not_initialised(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
            # db is None
            with pytest.raises(RuntimeError, match="not initialized"):
                svc._get_collection()

    def test_returns_collection_reference(self):
        svc, _, db, _, _, coll_ref, _ = _make_service_with_db()
        coll = svc._get_collection()
        db.collection.assert_called_once_with(svc.collection_name)
        assert coll is coll_ref


# ===========================================================================
# FirestoreStateService — _is_cache_valid
# ===========================================================================


class TestIsCacheValid:
    """Tests for _is_cache_valid()."""

    def _svc(self, enable_cache=True, cache_ttl=300):
        svc, *_ = _make_service_with_db(enable_cache=enable_cache, cache_ttl=cache_ttl)
        return svc

    def test_returns_false_when_cache_disabled(self):
        svc = self._svc(enable_cache=False)
        svc._cache_timestamps["vid1"] = datetime.now(timezone.utc)
        assert svc._is_cache_valid("vid1") is False

    def test_returns_false_when_not_in_cache(self):
        svc = self._svc()
        assert svc._is_cache_valid("missing") is False

    def test_returns_false_when_expired(self):
        svc = self._svc(cache_ttl=10)
        # Timestamp older than TTL
        old_ts = datetime.now(timezone.utc) - timedelta(seconds=20)
        svc._cache_timestamps["vid1"] = old_ts
        assert svc._is_cache_valid("vid1") is False

    def test_returns_true_when_valid(self):
        svc = self._svc(cache_ttl=300)
        svc._cache_timestamps["vid1"] = datetime.now(timezone.utc)
        assert svc._is_cache_valid("vid1") is True

    def test_boundary_just_before_expiry(self):
        svc = self._svc(cache_ttl=300)
        # 299 seconds ago — still valid
        ts = datetime.now(timezone.utc) - timedelta(seconds=299)
        svc._cache_timestamps["vid1"] = ts
        assert svc._is_cache_valid("vid1") is True


# ===========================================================================
# FirestoreStateService — create_state
# ===========================================================================


class TestCreateState:
    """Tests for create_state()."""

    async def test_create_state_returns_video_processing_state(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db()
        state = await svc.create_state("vid123", "https://youtube.com/watch?v=vid123")
        assert isinstance(state, _mod.VideoProcessingState)
        assert state.video_id == "vid123"
        assert state.status == "pending"
        assert state.current_stage == "metadata"

    async def test_create_state_calls_firestore_set(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db()
        await svc.create_state("vid123", "https://youtube.com/watch?v=vid123")
        doc_ref.set.assert_awaited_once()

    async def test_create_state_updates_cache(self):
        svc, _, _, _, _, _, _ = _make_service_with_db(enable_cache=True)
        state = await svc.create_state("vid123", "https://youtube.com/watch?v=vid123")
        assert "vid123" in svc._local_cache
        assert svc._local_cache["vid123"] is state
        assert "vid123" in svc._cache_timestamps

    async def test_create_state_skips_cache_when_disabled(self):
        svc, _, _, _, _, _, _ = _make_service_with_db(enable_cache=False)
        await svc.create_state("vid123", "https://youtube.com/watch?v=vid123")
        assert "vid123" not in svc._local_cache

    async def test_create_state_created_at_is_set(self):
        svc, _, _, _, _, _, _ = _make_service_with_db()
        state = await svc.create_state("vid123", "https://youtube.com/watch?v=vid123")
        assert state.created_at is not None


# ===========================================================================
# FirestoreStateService — get_state
# ===========================================================================


class TestGetState:
    """Tests for get_state()."""

    async def test_get_state_returns_from_cache(self):
        svc, _, _, _, _, _, _ = _make_service_with_db(enable_cache=True)
        cached = _mod.VideoProcessingState(
            video_id="vid1",
            video_url="https://youtube.com/watch?v=vid1",
            status="processing",
            current_stage="transcript",
        )
        svc._local_cache["vid1"] = cached
        svc._cache_timestamps["vid1"] = datetime.now(timezone.utc)

        result = await svc.get_state("vid1")
        assert result is cached

    async def test_get_state_fetches_from_firestore_on_cache_miss(self):
        svc, _, db, doc_ref, doc_snapshot, coll_ref, _ = _make_service_with_db(enable_cache=False)
        result = await svc.get_state("vid123")
        doc_ref.get.assert_awaited_once()
        assert isinstance(result, _mod.VideoProcessingState)

    async def test_get_state_returns_none_if_not_found(self):
        svc, _, _, doc_ref, doc_snapshot, _, _ = _make_service_with_db(enable_cache=False)
        doc_snapshot.exists = False
        result = await svc.get_state("missing")
        assert result is None

    async def test_get_state_populates_cache_after_fetch(self):
        svc, _, _, doc_ref, doc_snapshot, _, _ = _make_service_with_db(enable_cache=True)
        doc_snapshot.exists = True
        # Ensure cache is cold
        result = await svc.get_state("vid123")
        assert "vid123" in svc._local_cache
        assert "vid123" in svc._cache_timestamps

    async def test_get_state_skips_cache_population_when_disabled(self):
        svc, _, _, doc_ref, doc_snapshot, _, _ = _make_service_with_db(enable_cache=False)
        doc_snapshot.exists = True
        await svc.get_state("vid123")
        assert "vid123" not in svc._local_cache


# ===========================================================================
# FirestoreStateService — update_state
# ===========================================================================


class TestUpdateState:
    """Tests for update_state()."""

    def _seed_cache(self, svc: _mod.FirestoreStateService, video_id: str) -> _mod.VideoProcessingState:
        state = _mod.VideoProcessingState(
            video_id=video_id,
            video_url="https://youtube.com/watch?v=" + video_id,
            status="pending",
            current_stage="metadata",
        )
        svc._local_cache[video_id] = state
        svc._cache_timestamps[video_id] = datetime.now(timezone.utc)
        return state

    async def test_update_state_raises_value_error_if_not_found(self):
        svc, _, _, doc_ref, doc_snapshot, _, _ = _make_service_with_db(enable_cache=False)
        doc_snapshot.exists = False
        with pytest.raises(ValueError, match="No state found"):
            await svc.update_state("nonexistent")

    async def test_update_state_updates_status(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        self._seed_cache(svc, "vid1")
        result = await svc.update_state("vid1", status="processing")
        assert result.status == "processing"

    async def test_update_state_updates_current_stage(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        self._seed_cache(svc, "vid1")
        result = await svc.update_state("vid1", current_stage="transcript")
        assert result.current_stage == "transcript"

    async def test_update_state_updates_all_optional_fields(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        self._seed_cache(svc, "vid1")
        result = await svc.update_state(
            "vid1",
            status="completed",
            current_stage="complete",
            metadata={"title": "Test"},
            transcript={"text": "hello"},
            ai_analysis={"summary": "ok"},
            error_message="none",
            processing_time=5.0,
        )
        assert result.status == "completed"
        assert result.current_stage == "complete"
        assert result.metadata == {"title": "Test"}
        assert result.transcript == {"text": "hello"}
        assert result.ai_analysis == {"summary": "ok"}
        assert result.error_message == "none"
        assert result.processing_time == 5.0

    async def test_update_state_calls_firestore_update(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        self._seed_cache(svc, "vid1")
        await svc.update_state("vid1", status="completed")
        doc_ref.update.assert_awaited_once()

    async def test_update_state_refreshes_cache(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        self._seed_cache(svc, "vid1")
        old_ts = svc._cache_timestamps["vid1"]
        result = await svc.update_state("vid1", status="processing")
        assert svc._local_cache["vid1"] is result
        # timestamp should be refreshed (equal or newer)
        assert svc._cache_timestamps["vid1"] >= old_ts

    async def test_update_state_none_fields_not_overwritten(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db(enable_cache=True)
        state = self._seed_cache(svc, "vid1")
        state.metadata = {"original": True}
        # Don't pass metadata — it should remain untouched
        result = await svc.update_state("vid1", status="processing")
        assert result.metadata == {"original": True}


# ===========================================================================
# FirestoreStateService — delete_state
# ===========================================================================


class TestDeleteState:
    """Tests for delete_state()."""

    async def test_delete_state_calls_firestore_delete(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db()
        await svc.delete_state("vid1")
        doc_ref.delete.assert_awaited_once()

    async def test_delete_state_removes_from_cache(self):
        svc, _, _, _, _, _, _ = _make_service_with_db(enable_cache=True)
        state = _mod.VideoProcessingState(
            video_id="vid1", video_url="u", status="pending", current_stage="metadata"
        )
        svc._local_cache["vid1"] = state
        svc._cache_timestamps["vid1"] = datetime.now(timezone.utc)

        await svc.delete_state("vid1")

        assert "vid1" not in svc._local_cache
        assert "vid1" not in svc._cache_timestamps

    async def test_delete_state_tolerates_missing_cache_entry(self):
        svc, _, _, doc_ref, _, _, _ = _make_service_with_db()
        # Should not raise even if cache is empty
        await svc.delete_state("not_in_cache")
        doc_ref.delete.assert_awaited_once()


# ===========================================================================
# FirestoreStateService — list_states
# ===========================================================================


class TestListStates:
    """Tests for list_states().

    Note: list_states() accesses the module-level `firestore.Query.DESCENDING`
    attribute at *call time*, so every invocation must happen while
    `patch.object(_mod, "firestore", fake_fs)` is active.
    """

    def _doc(self, video_id: str) -> MagicMock:
        d = MagicMock()
        d.to_dict.return_value = {
            "video_id": video_id,
            "video_url": "https://youtube.com/watch?v=" + video_id,
            "status": "completed",
            "current_stage": "complete",
            "metadata": None,
            "transcript": None,
            "ai_analysis": None,
            "error_message": None,
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T01:00:00+00:00",
            "processing_time": None,
        }
        return d

    async def test_list_states_returns_empty_list(self):
        svc, fake_fs, _, _, _, _, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])
        with patch.object(_mod, "firestore", fake_fs):
            result = await svc.list_states()
        assert result == []

    async def test_list_states_returns_all_states(self):
        svc, fake_fs, _, _, _, coll_ref, query = _make_service_with_db()
        docs = [self._doc("v1"), self._doc("v2")]
        query.get = AsyncMock(return_value=docs)

        with patch.object(_mod, "firestore", fake_fs):
            result = await svc.list_states()
        assert len(result) == 2
        assert all(isinstance(s, _mod.VideoProcessingState) for s in result)

    async def test_list_states_with_status_filter_calls_where(self):
        svc, fake_fs, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])

        with patch.object(_mod, "firestore", fake_fs):
            await svc.list_states(status="completed")
        coll_ref.where.assert_called_once_with("status", "==", "completed")

    async def test_list_states_without_status_filter_skips_where(self):
        svc, fake_fs, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])

        with patch.object(_mod, "firestore", fake_fs):
            await svc.list_states()
        coll_ref.where.assert_not_called()

    async def test_list_states_applies_order_and_limit(self):
        # When no status filter, order_by is called on the collection_ref itself.
        # collection_ref.order_by(...) returns the query mock, then query.limit(50).
        svc, fake_fs, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])
        # order_by on coll_ref should return the query mock so limit() chains correctly
        coll_ref.order_by = MagicMock(return_value=query)

        with patch.object(_mod, "firestore", fake_fs):
            await svc.list_states(limit=50)
        coll_ref.order_by.assert_called_once()
        query.limit.assert_called_once_with(50)


# ===========================================================================
# FirestoreStateService — cleanup_old_states
# ===========================================================================


class TestCleanupOldStates:
    """Tests for cleanup_old_states()."""

    async def test_cleanup_returns_zero_when_no_docs(self):
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])
        count = await svc.cleanup_old_states(days=7)
        assert count == 0

    async def test_cleanup_deletes_docs_and_returns_count(self):
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()

        doc1 = MagicMock()
        doc1.reference = MagicMock()
        doc1.reference.delete = AsyncMock()
        doc2 = MagicMock()
        doc2.reference = MagicMock()
        doc2.reference.delete = AsyncMock()

        query.get = AsyncMock(return_value=[doc1, doc2])

        count = await svc.cleanup_old_states(days=7)

        assert count == 2
        doc1.reference.delete.assert_awaited_once()
        doc2.reference.delete.assert_awaited_once()

    async def test_cleanup_queries_with_where_clause(self):
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])

        await svc.cleanup_old_states(days=3)
        coll_ref.where.assert_called_once()
        call_args = coll_ref.where.call_args
        assert call_args[0][0] == "created_at"
        assert call_args[0][1] == "<"

    async def test_cleanup_custom_days_parameter(self):
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        query.get = AsyncMock(return_value=[])

        # Call with custom days — just ensure it runs without error
        count = await svc.cleanup_old_states(days=30)
        assert count == 0

    @staticmethod
    def _tracking_docs(n: int) -> tuple[list, dict]:
        """Build n mock docs whose deletes record peak overlap."""
        stats = {"in_flight": 0, "peak": 0, "peak_tasks": 0}

        async def _tracked() -> None:
            stats["in_flight"] += 1
            stats["peak"] = max(stats["peak"], stats["in_flight"])
            # Task count reflects how many coroutines were *allocated*, which is
            # a stricter bound than how many RPCs are in flight.
            stats["peak_tasks"] = max(stats["peak_tasks"], len(asyncio.all_tasks()))
            # Yield so sibling deletes get a chance to start. Under the previous
            # sequential loop nothing else could be running here.
            await asyncio.sleep(0)
            stats["in_flight"] -= 1

        docs = []
        for _ in range(n):
            doc = MagicMock()
            doc.reference = MagicMock()
            doc.reference.delete = AsyncMock(side_effect=_tracked)
            docs.append(doc)
        return docs, stats

    async def test_cleanup_deletes_overlap_instead_of_running_sequentially(self):
        """Deletes must overlap. The sequential loop this replaced had peak overlap 1."""
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        docs, stats = self._tracking_docs(8)
        query.get = AsyncMock(return_value=docs)

        count = await svc.cleanup_old_states(days=7)

        assert count == 8
        assert stats["peak"] > 1, (
            f"deletes never overlapped (peak={stats['peak']}); "
            "cleanup is still issuing one round-trip at a time"
        )

    async def test_cleanup_bounds_in_flight_deletes(self):
        """A large backlog must not fan out unbounded concurrent RPCs."""
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        limit = _mod.CLEANUP_DELETE_CONCURRENCY
        docs, stats = self._tracking_docs(limit * 3)
        query.get = AsyncMock(return_value=docs)

        count = await svc.cleanup_old_states(days=7)

        assert count == limit * 3
        assert stats["peak"] <= limit, (
            f"peak in-flight deletes {stats['peak']} exceeded the "
            f"CLEANUP_DELETE_CONCURRENCY bound of {limit}"
        )

    async def test_cleanup_bounds_allocated_delete_tasks_not_just_rpcs(self):
        """A worker pool must not allocate one task per document.

        Gathering over every document would schedule len(docs) tasks up front,
        so a large backlog would cost unbounded task/event-loop memory even
        though only CLEANUP_DELETE_CONCURRENCY RPCs are in flight. The query
        driving this has no limit, so that allocation must stay bounded too.
        """
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()
        limit = _mod.CLEANUP_DELETE_CONCURRENCY
        docs, stats = self._tracking_docs(limit * 3)
        query.get = AsyncMock(return_value=docs)

        count = await svc.cleanup_old_states(days=7)

        assert count == limit * 3
        # Allow a small margin for the enclosing test task and gather bookkeeping.
        assert stats["peak_tasks"] <= limit + 3, (
            f"cleanup allocated {stats['peak_tasks']} concurrent tasks for "
            f"{limit * 3} documents; delete tasks are not bounded by the "
            f"CLEANUP_DELETE_CONCURRENCY worker pool of {limit}"
        )

    async def test_cleanup_failure_does_not_abandon_remaining_deletes(self):
        """One failing delete must not strand the rest, and must not be counted.

        The pool is deliberately narrowed to a single worker while the backlog is
        larger, so the *same* worker whose delete raises has to keep pulling from
        the shared iterator. With a pool wider than the backlog every worker
        handles exactly one document and the continuation path is never taken --
        the assertions below would then hold even for a worker that returned on
        its first exception.
        """
        svc, _, _, _, _, coll_ref, query = _make_service_with_db()

        pool_size = 1
        doc_count = 5

        docs = []
        for i in range(doc_count):
            doc = MagicMock(name=f"doc{i}")
            doc.reference = MagicMock()
            # Fail on the very first document the lone worker touches.
            doc.reference.delete = AsyncMock(
                side_effect=RuntimeError("firestore boom") if i == 0 else None
            )
            docs.append(doc)

        query.get = AsyncMock(return_value=docs)

        with patch.object(_mod, "CLEANUP_DELETE_CONCURRENCY", pool_size):
            count = await svc.cleanup_old_states(days=7)

        # Only the successful deletes are reported.
        assert count == doc_count - 1
        # Every document was attempted exactly once. The four after the failure
        # were reachable only because the worker continued draining the queue;
        # the original sequential loop propagated the error and skipped them.
        for doc in docs:
            doc.reference.delete.assert_awaited_once()


# ===========================================================================
# Module-level singleton helpers
# ===========================================================================


class TestSingletonHelpers:
    """Tests for get_firestore_service() and cleanup_firestore_service()."""

    async def test_get_firestore_service_creates_singleton(self):
        fake_fs = _make_fake_firestore()
        mock_db = MagicMock(name="db")
        mock_db.close = AsyncMock()
        fake_fs.AsyncClient.return_value = mock_db

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
            patch.object(_mod, "_firestore_service", None),
        ):
            svc = await _mod.get_firestore_service()
            assert svc is not None
            assert isinstance(svc, _mod.FirestoreStateService)

    async def test_get_firestore_service_returns_same_instance(self):
        fake_fs = _make_fake_firestore()
        mock_db = MagicMock(name="db")
        mock_db.close = AsyncMock()
        fake_fs.AsyncClient.return_value = mock_db

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
            patch.object(_mod, "_firestore_service", None),
        ):
            svc1 = await _mod.get_firestore_service()
            svc2 = await _mod.get_firestore_service()
            assert svc1 is svc2

    async def test_cleanup_firestore_service_closes_and_clears_singleton(self):
        fake_fs = _make_fake_firestore()
        mock_db = MagicMock(name="db")
        mock_db.close = AsyncMock()
        fake_fs.AsyncClient.return_value = mock_db

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
            patch.object(_mod, "_firestore_service", None),
        ):
            await _mod.get_firestore_service()
            await _mod.cleanup_firestore_service()
            assert _mod._firestore_service is None

    async def test_cleanup_firestore_service_is_idempotent(self):
        with patch.object(_mod, "_firestore_service", None):
            # Should not raise even when singleton is already None
            await _mod.cleanup_firestore_service()

    async def test_get_firestore_service_after_cleanup_creates_new_instance(self):
        fake_fs = _make_fake_firestore()
        mock_db = MagicMock(name="db")
        mock_db.close = AsyncMock()
        fake_fs.AsyncClient.return_value = mock_db

        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
            patch.object(_mod, "_firestore_service", None),
        ):
            svc1 = await _mod.get_firestore_service()
            await _mod.cleanup_firestore_service()
            svc2 = await _mod.get_firestore_service()
            assert svc1 is not svc2


# ===========================================================================
# FIRESTORE_AVAILABLE flag — module-level behaviour
# ===========================================================================


class TestFirestoreAvailableFlag:
    """Tests that FIRESTORE_AVAILABLE=False blocks service construction."""

    def test_firestore_available_is_bool(self):
        assert isinstance(_mod.FIRESTORE_AVAILABLE, bool)

    def test_firestore_unavailable_blocks_init(self):
        with patch.object(_mod, "FIRESTORE_AVAILABLE", False):
            with pytest.raises(ImportError):
                _mod.FirestoreStateService()

    def test_firestore_available_true_allows_init(self):
        fake_fs = _make_fake_firestore()
        with (
            patch.object(_mod, "FIRESTORE_AVAILABLE", True),
            patch.object(_mod, "firestore", fake_fs),
        ):
            svc = _mod.FirestoreStateService()
            assert svc is not None
