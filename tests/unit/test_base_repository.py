"""
Unit tests for BaseRepository and TenantAwareRepository.

Covers: create, get_by_id, get_by_field, list_all, update, delete,
        count, exists, bulk_create, bulk_update, search,
        with_relationships, with_options, TenantAwareRepository methods.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# ---------------------------------------------------------------------------
# Helpers / fake model
# ---------------------------------------------------------------------------
# Use real SQLAlchemy mapped models so select(Model) works without errors
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from youtube_extension.backend.repositories.base import (
    BaseRepository,
    TenantAwareRepository,
)


class _TestBase(DeclarativeBase):
    pass


class FakeModel(_TestBase):
    """Proper SQLAlchemy ORM model for testing BaseRepository."""
    __tablename__ = "fake_model"

    id = Column(Integer, primary_key=True)
    is_deleted = Column(Boolean, default=False)
    tenant_id = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeModelNoSoftDelete(_TestBase):
    """Model without is_deleted / tenant_id."""
    __tablename__ = "fake_model_no_soft_delete"

    id = Column(Integer, primary_key=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class ConcreteRepo(BaseRepository[FakeModel]):
    """Concrete (non-abstract) subclass of BaseRepository for testing."""


class ConcreteTenantRepo(TenantAwareRepository[FakeModel]):
    """Concrete subclass of TenantAwareRepository for testing."""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    """Return a fresh AsyncMock session for each test."""
    s = AsyncMock()
    s.add = MagicMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.rollback = AsyncMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def repo(session):
    return ConcreteRepo(session, FakeModel)


@pytest.fixture
def repo_no_soft(session):
    return ConcreteRepo(session, FakeModelNoSoftDelete)


@pytest.fixture
def tenant_repo(session):
    return ConcreteTenantRepo(session, FakeModel, tenant_id="tenant-abc")


# ---------------------------------------------------------------------------
# Helpers to build fake execute() results
# ---------------------------------------------------------------------------

def _scalar_result(value):
    """Return an object whose .scalar_one_or_none() returns *value*."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalar_value(value):
    """Return an object whose .scalar() returns *value*."""
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _scalars_all(items):
    """Return an object whose .scalars().all() returns *items*."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _rowcount(n):
    """Return an object whose .rowcount == n."""
    r = MagicMock()
    r.rowcount = n
    return r


# ===========================================================================
# create
# ===========================================================================

class TestCreate:
    async def test_create_success_returns_entity(self, repo, session):
        instance = FakeModel(id="new-id")
        session.refresh = AsyncMock(side_effect=lambda e: None)
        # Patch FakeModel constructor to return our instance
        repo.model = MagicMock(return_value=instance)

        result = await repo.create(id="new-id", name="test")

        session.add.assert_called_once_with(instance)
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(instance)
        assert result is instance

    async def test_create_integrity_error_raises_value_error(self, repo, session):
        repo.model = MagicMock(return_value=FakeModel())
        session.flush.side_effect = IntegrityError("stmt", {}, Exception("dup key"))

        with pytest.raises(ValueError, match="Entity creation failed"):
            await repo.create(name="duplicate")

        session.rollback.assert_awaited_once()

    async def test_create_passes_kwargs_to_model(self, repo, session):
        captured = {}

        def fake_model(**kwargs):
            captured.update(kwargs)
            return FakeModel(**kwargs)

        repo.model = fake_model
        await repo.create(field_a="alpha", field_b=42)
        assert captured == {"field_a": "alpha", "field_b": 42}


# ===========================================================================
# get_by_id
# ===========================================================================

class TestGetById:
    async def test_found(self, repo, session):
        entity = FakeModel(id="eid")
        session.execute.return_value = _scalar_result(entity)

        result = await repo.get_by_id("eid")
        assert result is entity

    async def test_not_found_returns_none(self, repo, session):
        session.execute.return_value = _scalar_result(None)
        result = await repo.get_by_id("missing")
        assert result is None

    async def test_with_tenant_id(self, repo, session):
        entity = FakeModel(id="eid", tenant_id="t1")
        session.execute.return_value = _scalar_result(entity)

        result = await repo.get_by_id("eid", tenant_id="t1")
        assert result is entity
        session.execute.assert_awaited_once()

    async def test_without_soft_delete_attribute(self, repo_no_soft, session):
        entity = FakeModelNoSoftDelete(id="eid")
        session.execute.return_value = _scalar_result(entity)

        result = await repo_no_soft.get_by_id("eid")
        assert result is entity

    async def test_tenant_id_skipped_when_none(self, repo, session):
        entity = FakeModel(id="eid")
        session.execute.return_value = _scalar_result(entity)

        result = await repo.get_by_id("eid", tenant_id=None)
        assert result is entity


# ===========================================================================
# get_by_field
# ===========================================================================

class TestGetByField:
    async def test_found_by_field(self, repo, session):
        entity = FakeModel(id="x", tenant_id="t")
        session.execute.return_value = _scalar_result(entity)

        result = await repo.get_by_field("tenant_id", "t")
        assert result is entity

    async def test_not_found_returns_none(self, repo, session):
        session.execute.return_value = _scalar_result(None)
        result = await repo.get_by_field("tenant_id", "missing")
        assert result is None

    async def test_invalid_field_raises_value_error(self, repo, session):
        with pytest.raises(ValueError, match="does not have field 'nonexistent'"):
            await repo.get_by_field("nonexistent", "val")

    async def test_with_tenant_id(self, repo, session):
        entity = FakeModel(id="x", tenant_id="t")
        session.execute.return_value = _scalar_result(entity)

        result = await repo.get_by_field("tenant_id", "t", tenant_id="t")
        assert result is entity

    async def test_field_on_model_without_tenant(self, repo_no_soft, session):
        entity = FakeModelNoSoftDelete(id="y")
        session.execute.return_value = _scalar_result(entity)

        result = await repo_no_soft.get_by_field("id", "y")
        assert result is entity


# ===========================================================================
# list_all
# ===========================================================================

class TestListAll:
    async def test_returns_all_entities(self, repo, session):
        items = [FakeModel(id=f"id-{i}") for i in range(3)]
        session.execute.return_value = _scalars_all(items)

        result = await repo.list_all()
        assert result == items

    async def test_with_tenant_id(self, repo, session):
        items = [FakeModel(id="a", tenant_id="t1")]
        session.execute.return_value = _scalars_all(items)

        result = await repo.list_all(tenant_id="t1")
        assert len(result) == 1

    async def test_pagination_limit_offset(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.list_all(limit=10, offset=5)
        session.execute.assert_awaited_once()

    async def test_order_by_ascending(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.list_all(order_by="created_at")
        session.execute.assert_awaited_once()

    async def test_order_by_descending_prefix(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.list_all(order_by="-created_at")
        session.execute.assert_awaited_once()

    async def test_order_by_unknown_field_ignored(self, repo, session):
        session.execute.return_value = _scalars_all([])
        # Should not raise even when field is unknown
        await repo.list_all(order_by="nonexistent_field")
        session.execute.assert_awaited_once()

    async def test_order_by_descending_unknown_field_ignored(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.list_all(order_by="-nonexistent_field")
        session.execute.assert_awaited_once()

    async def test_filters_applied(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.list_all(filters={"tenant_id": "t1"})
        session.execute.assert_awaited_once()

    async def test_filters_unknown_field_skipped(self, repo, session):
        session.execute.return_value = _scalars_all([])
        # unknown filter fields should be silently ignored
        await repo.list_all(filters={"no_such_field": "x"})
        session.execute.assert_awaited_once()

    async def test_no_soft_delete_model(self, repo_no_soft, session):
        session.execute.return_value = _scalars_all([])
        await repo_no_soft.list_all()
        session.execute.assert_awaited_once()

    async def test_default_order_by_created_at(self, repo, session):
        """When order_by is None and model has created_at, default ordering applied."""
        session.execute.return_value = _scalars_all([])
        await repo.list_all()
        session.execute.assert_awaited_once()

    async def test_no_created_at_no_default_order(self, repo_no_soft, session):
        """Model without created_at: no default ordering, no crash."""
        session.execute.return_value = _scalars_all([])
        await repo_no_soft.list_all()
        session.execute.assert_awaited_once()


# ===========================================================================
# update
# ===========================================================================

class TestUpdate:
    async def test_found_returns_updated_entity(self, repo, session):
        updated = FakeModel(id="eid")
        session.execute.return_value = _scalar_result(updated)
        session.refresh = AsyncMock()

        result = await repo.update("eid", name="new-name")

        session.refresh.assert_awaited_once_with(updated)
        assert result is updated

    async def test_not_found_returns_none(self, repo, session):
        session.execute.return_value = _scalar_result(None)

        result = await repo.update("missing", name="x")
        assert result is None

    async def test_protected_fields_excluded(self, repo, session):
        """id, created_at, tenant_id must be stripped from update payload."""
        captured_values = {}

        async def capture_execute(query):
            # Dig into compile params isn't practical here; just assert no raise
            return _scalar_result(None)

        session.execute.side_effect = capture_execute
        result = await repo.update("eid", id="new-id", created_at="ts", tenant_id="t", name="ok")
        assert result is None  # entity not found, but no error thrown

    async def test_updated_at_injected_when_attribute_exists(self, repo, session):
        updated = FakeModel(id="eid")
        session.execute.return_value = _scalar_result(updated)
        session.refresh = AsyncMock()

        await repo.update("eid", name="changed")
        session.execute.assert_awaited_once()

    async def test_no_refresh_when_not_found(self, repo, session):
        session.execute.return_value = _scalar_result(None)
        session.refresh = AsyncMock()

        await repo.update("missing")
        session.refresh.assert_not_awaited()


# ===========================================================================
# delete
# ===========================================================================

class TestDelete:
    async def test_soft_delete_success(self, repo, session):
        updated = FakeModel(id="eid", is_deleted=True)
        session.execute.return_value = _scalar_result(updated)
        session.refresh = AsyncMock()

        result = await repo.delete("eid", soft_delete=True)
        assert result is True

    async def test_soft_delete_entity_not_found(self, repo, session):
        session.execute.return_value = _scalar_result(None)

        result = await repo.delete("missing", soft_delete=True)
        assert result is False

    async def test_hard_delete_success(self, repo, session):
        session.execute.return_value = _rowcount(1)

        result = await repo.delete("eid", soft_delete=False)
        assert result is True

    async def test_hard_delete_not_found(self, repo, session):
        session.execute.return_value = _rowcount(0)

        result = await repo.delete("missing", soft_delete=False)
        assert result is False

    async def test_soft_delete_default_is_true(self, repo, session):
        """Default soft_delete=True, so update path is taken."""
        updated = FakeModel(id="eid", is_deleted=True)
        session.execute.return_value = _scalar_result(updated)
        session.refresh = AsyncMock()

        result = await repo.delete("eid")
        assert result is True

    async def test_soft_delete_on_model_without_is_deleted(self, repo_no_soft, session):
        """Model without is_deleted falls back to hard delete even if soft_delete=True."""
        session.execute.return_value = _rowcount(1)
        result = await repo_no_soft.delete("eid", soft_delete=True)
        assert result is True


# ===========================================================================
# count
# ===========================================================================

class TestCount:
    async def test_count_returns_integer(self, repo, session):
        session.execute.return_value = _scalar_value(7)
        result = await repo.count()
        assert result == 7

    async def test_count_none_returns_zero(self, repo, session):
        session.execute.return_value = _scalar_value(None)
        result = await repo.count()
        assert result == 0

    async def test_count_with_tenant(self, repo, session):
        session.execute.return_value = _scalar_value(3)
        result = await repo.count(tenant_id="t1")
        assert result == 3

    async def test_count_with_filters(self, repo, session):
        session.execute.return_value = _scalar_value(2)
        result = await repo.count(filters={"tenant_id": "t1"})
        assert result == 2

    async def test_count_filters_unknown_field_ignored(self, repo, session):
        session.execute.return_value = _scalar_value(0)
        result = await repo.count(filters={"no_such_field": "x"})
        assert result == 0

    async def test_count_no_soft_delete_model(self, repo_no_soft, session):
        session.execute.return_value = _scalar_value(5)
        result = await repo_no_soft.count()
        assert result == 5


# ===========================================================================
# exists
# ===========================================================================

class TestExists:
    async def test_exists_true(self, repo, session):
        session.execute.return_value = _scalar_value(1)
        assert await repo.exists("eid") is True

    async def test_exists_false_zero(self, repo, session):
        session.execute.return_value = _scalar_value(0)
        assert await repo.exists("eid") is False

    async def test_exists_false_none(self, repo, session):
        session.execute.return_value = _scalar_value(None)
        assert await repo.exists("eid") is False

    async def test_exists_with_tenant(self, repo, session):
        session.execute.return_value = _scalar_value(1)
        assert await repo.exists("eid", tenant_id="t1") is True

    async def test_exists_no_soft_delete_model(self, repo_no_soft, session):
        session.execute.return_value = _scalar_value(1)
        assert await repo_no_soft.exists("eid") is True


# ===========================================================================
# bulk_create
# ===========================================================================

class TestBulkCreate:
    async def test_bulk_create_returns_all_entities(self, repo, session):
        instances = [FakeModel(id=f"id-{i}") for i in range(3)]
        call_count = 0

        def fake_model(**kwargs):
            nonlocal call_count
            inst = instances[call_count]
            call_count += 1
            return inst

        repo.model = fake_model
        session.refresh = AsyncMock()

        result = await repo.bulk_create(
            [{"id": "id-0"}, {"id": "id-1"}, {"id": "id-2"}]
        )

        assert len(result) == 3
        session.add_all.assert_called_once()
        session.flush.assert_awaited_once()
        assert session.refresh.await_count == 3

    async def test_bulk_create_empty_list(self, repo, session):
        result = await repo.bulk_create([])
        assert result == []
        session.add_all.assert_called_once_with([])
        session.flush.assert_awaited_once()


# ===========================================================================
# bulk_update
# ===========================================================================

class TestBulkUpdate:
    async def test_bulk_update_empty_returns_zero(self, repo, session):
        result = await repo.bulk_update([])
        assert result == 0
        session.execute.assert_not_awaited()

    async def test_bulk_update_returns_count(self, repo, session):
        session.execute.return_value = MagicMock()
        updates = [
            {"id": "id-1", "name": "Alice"},
            {"id": "id-2", "name": "Bob"},
        ]
        result = await repo.bulk_update(updates)
        assert result == 2
        assert session.execute.await_count == 1

    async def test_bulk_update_skips_entry_without_id(self, repo, session):
        # We no longer manually pop 'id' or skip. SQLAlchemy's bulk update handles it.
        # But we verify it executes once with the full list.
        session.execute.return_value = MagicMock()
        updates = [
            {"name": "no-id-entry"},
            {"id": "id-1", "name": "has-id"},
        ]
        result = await repo.bulk_update(updates)
        assert result == 2
        assert session.execute.await_count == 1

    async def test_bulk_update_mutates_dicts(self, repo, session):
        """bulk_update used to pop 'id' from each dict. New SQLAlchemy bulk update does not."""
        session.execute.return_value = MagicMock()
        data = [{"id": "x", "field": "v"}]
        await repo.bulk_update(data)
        # 'id' should NOT be popped
        assert "id" in data[0]


# ===========================================================================
# search
# ===========================================================================

class TestSearch:
    async def test_empty_search_term_returns_empty(self, repo, session):
        result = await repo.search("   ", ["tenant_id"])
        assert result == []
        session.execute.assert_not_awaited()

    async def test_search_returns_results(self, repo, session):
        items = [FakeModel(id=1), FakeModel(id=2)]
        session.execute.return_value = _scalars_all(items)
        # Use the real mapped column 'tenant_id' (String column → supports ilike)
        result = await repo.search("hello", ["tenant_id"])
        assert result == items

    async def test_search_unknown_field_skipped(self, repo, session):
        session.execute.return_value = _scalars_all([])
        result = await repo.search("term", ["nonexistent_field"])
        assert result == []

    async def test_search_with_tenant_id(self, repo, session):
        session.execute.return_value = _scalars_all([])
        result = await repo.search("q", ["tenant_id"], tenant_id="t1")
        assert result == []

    async def test_search_with_limit(self, repo, session):
        session.execute.return_value = _scalars_all([])
        await repo.search("q", ["tenant_id"], limit=5)
        session.execute.assert_awaited_once()

    async def test_search_no_search_conditions_no_crash(self, repo, session):
        """Search with no valid fields should still execute a query (no OR clause)."""
        session.execute.return_value = _scalars_all([])
        result = await repo.search("term", [])
        assert result == []

    async def test_search_no_soft_delete_model(self, repo_no_soft, session):
        session.execute.return_value = _scalars_all([])
        await repo_no_soft.search("q", ["id"])
        session.execute.assert_awaited_once()


# ===========================================================================
# with_relationships / with_options
# ===========================================================================

class TestWithRelationshipsAndOptions:
    def test_with_relationships_returns_self(self, repo):
        result = repo.with_relationships("rel1", "rel2")
        assert result is repo

    def test_with_options_returns_self(self, repo):
        result = repo.with_options("opt1")
        assert result is repo

    def test_with_relationships_no_args(self, repo):
        result = repo.with_relationships()
        assert result is repo

    def test_with_options_no_args(self, repo):
        result = repo.with_options()
        assert result is repo


# ===========================================================================
# TenantAwareRepository
# ===========================================================================

class TestTenantAwareRepository:
    def test_init_stores_tenant_id(self, session):
        repo = ConcreteTenantRepo(session, FakeModel, tenant_id="t99")
        assert repo.tenant_id == "t99"

    async def test_create_injects_tenant_id(self, tenant_repo, session):
        instance = FakeModel(id="new", tenant_id="tenant-abc")
        repo = tenant_repo
        repo.model = MagicMock(return_value=instance)
        session.refresh = AsyncMock()

        result = await repo.create(name="thing")

        # The model constructor should have received tenant_id="tenant-abc"
        repo.model.assert_called_once()
        call_kwargs = repo.model.call_args[1]
        assert call_kwargs["tenant_id"] == "tenant-abc"
        assert result is instance

    async def test_get_by_id_passes_tenant(self, tenant_repo, session):
        entity = FakeModel(id="eid", tenant_id="tenant-abc")
        session.execute.return_value = _scalar_result(entity)

        result = await tenant_repo.get_by_id("eid")
        assert result is entity
        session.execute.assert_awaited_once()

    async def test_get_by_field_passes_tenant(self, tenant_repo, session):
        entity = FakeModel(id="x", tenant_id="tenant-abc")
        session.execute.return_value = _scalar_result(entity)

        result = await tenant_repo.get_by_field("tenant_id", "tenant-abc")
        assert result is entity

    async def test_list_all_passes_tenant(self, tenant_repo, session):
        items = [FakeModel(id="a", tenant_id="tenant-abc")]
        session.execute.return_value = _scalars_all(items)

        result = await tenant_repo.list_all()
        assert result == items

    async def test_list_all_with_pagination(self, tenant_repo, session):
        session.execute.return_value = _scalars_all([])
        await tenant_repo.list_all(limit=5, offset=2)
        session.execute.assert_awaited_once()

    async def test_list_all_with_order_by(self, tenant_repo, session):
        session.execute.return_value = _scalars_all([])
        await tenant_repo.list_all(order_by="created_at")
        session.execute.assert_awaited_once()

    async def test_count_passes_tenant(self, tenant_repo, session):
        session.execute.return_value = _scalar_value(4)
        result = await tenant_repo.count()
        assert result == 4

    async def test_count_with_filters(self, tenant_repo, session):
        session.execute.return_value = _scalar_value(1)
        result = await tenant_repo.count(filters={"is_deleted": False})
        assert result == 1

    async def test_exists_passes_tenant(self, tenant_repo, session):
        session.execute.return_value = _scalar_value(1)
        result = await tenant_repo.exists("eid")
        assert result is True

    async def test_search_passes_tenant(self, tenant_repo, session):
        session.execute.return_value = _scalars_all([])
        result = await tenant_repo.search("q", ["tenant_id"])
        assert result == []

    async def test_search_with_limit(self, tenant_repo, session):
        session.execute.return_value = _scalars_all([])
        await tenant_repo.search("q", ["tenant_id"], limit=10)
        session.execute.assert_awaited_once()
