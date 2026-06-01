"""Unit tests for QueryStats, IndexRecommendation, and DatabaseConnectionPool."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.database_optimizer import (
    DatabaseConnectionPool,
    IndexRecommendation,
    QueryStats,
)


# ===========================================================================
# QueryStats — defaults and update_stats
# ===========================================================================


class TestQueryStatsDefaults:
    @pytest.fixture
    def qs(self):
        return QueryStats(query_hash="abc123", query_pattern="SELECT * FROM videos")

    def test_execution_count_default_zero(self, qs):
        assert qs.execution_count == 0

    def test_total_time_default_zero(self, qs):
        assert qs.total_execution_time_ms == 0.0

    def test_avg_time_default_zero(self, qs):
        assert qs.avg_execution_time_ms == 0.0

    def test_min_time_default_inf(self, qs):
        assert qs.min_execution_time_ms == float("inf")

    def test_max_time_default_zero(self, qs):
        assert qs.max_execution_time_ms == 0.0

    def test_last_executed_default_none(self, qs):
        assert qs.last_executed is None

    def test_error_count_default_zero(self, qs):
        assert qs.error_count == 0


class TestQueryStatsUpdateStats:
    @pytest.fixture
    def qs(self):
        return QueryStats(query_hash="h1", query_pattern="SELECT 1")

    def test_execution_count_increments(self, qs):
        qs.update_stats(50.0)
        assert qs.execution_count == 1

    def test_total_time_accumulates(self, qs):
        qs.update_stats(30.0)
        qs.update_stats(70.0)
        assert abs(qs.total_execution_time_ms - 100.0) < 1e-9

    def test_avg_time_calculated(self, qs):
        qs.update_stats(40.0)
        qs.update_stats(60.0)
        assert abs(qs.avg_execution_time_ms - 50.0) < 1e-9

    def test_min_time_tracked(self, qs):
        qs.update_stats(80.0)
        qs.update_stats(20.0)
        assert abs(qs.min_execution_time_ms - 20.0) < 1e-9

    def test_max_time_tracked(self, qs):
        qs.update_stats(10.0)
        qs.update_stats(90.0)
        assert abs(qs.max_execution_time_ms - 90.0) < 1e-9

    def test_last_executed_set(self, qs):
        before = datetime.now(timezone.utc)
        qs.update_stats(50.0)
        assert qs.last_executed >= before

    def test_error_count_not_incremented_on_success(self, qs):
        qs.update_stats(50.0, success=True)
        assert qs.error_count == 0

    def test_error_count_incremented_on_failure(self, qs):
        qs.update_stats(50.0, success=False)
        assert qs.error_count == 1

    def test_multiple_errors_accumulate(self, qs):
        qs.update_stats(10.0, success=False)
        qs.update_stats(20.0, success=False)
        assert qs.error_count == 2


# ===========================================================================
# IndexRecommendation dataclass
# ===========================================================================


class TestIndexRecommendation:
    @pytest.fixture
    def rec(self):
        return IndexRecommendation(
            table_name="videos",
            columns=["processed", "created_at"],
            index_type="btree",
            estimated_improvement=30.0,
            query_pattern="SELECT * FROM videos WHERE processed = ?",
            priority="high",
            created_at=datetime.now(timezone.utc),
            reason="Frequent filter on processed column",
        )

    def test_table_name_stored(self, rec):
        assert rec.table_name == "videos"

    def test_columns_stored(self, rec):
        assert rec.columns == ["processed", "created_at"]

    def test_index_type_stored(self, rec):
        assert rec.index_type == "btree"

    def test_estimated_improvement_stored(self, rec):
        assert rec.estimated_improvement == 30.0

    def test_priority_stored(self, rec):
        assert rec.priority == "high"

    def test_reason_stored(self, rec):
        assert "processed" in rec.reason


# ===========================================================================
# DatabaseConnectionPool defaults
# ===========================================================================


class TestDatabaseConnectionPoolInit:
    @pytest.fixture
    def pool(self):
        return DatabaseConnectionPool(database_url="sqlite:///:memory:")

    def test_database_url_stored(self, pool):
        assert pool.database_url == "sqlite:///:memory:"

    def test_min_connections_default(self, pool):
        assert pool.min_connections == 5

    def test_max_connections_default(self, pool):
        assert pool.max_connections == 20

    def test_pool_timeout_default(self, pool):
        assert pool.pool_timeout == 30

    def test_pool_starts_none(self, pool):
        assert pool.pool is None

    def test_pool_stats_has_connections_created(self, pool):
        assert "connections_created" in pool.pool_stats

    def test_pool_stats_has_connections_in_use(self, pool):
        assert "connections_in_use" in pool.pool_stats

    def test_pool_stats_has_total_queries(self, pool):
        assert "total_queries" in pool.pool_stats

    def test_pool_stats_has_failed_queries(self, pool):
        assert "failed_queries" in pool.pool_stats

    def test_pool_stats_has_avg_connection_time(self, pool):
        assert "avg_connection_time_ms" in pool.pool_stats

    def test_custom_params_stored(self):
        pool = DatabaseConnectionPool(
            database_url="sqlite:///:memory:",
            min_connections=2,
            max_connections=10,
            pool_timeout=60,
        )
        assert pool.min_connections == 2
        assert pool.max_connections == 10
        assert pool.pool_timeout == 60


class TestDatabaseConnectionPoolGetStats:
    def test_get_pool_stats_returns_dict(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:")
        stats = pool.get_pool_stats()
        assert isinstance(stats, dict)

    def test_get_pool_stats_has_pool_configuration(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:")
        stats = pool.get_pool_stats()
        assert "pool_configuration" in stats

    def test_pool_configuration_has_min_connections(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:", min_connections=3)
        stats = pool.get_pool_stats()
        assert stats["pool_configuration"]["min_connections"] == 3

    def test_pool_configuration_has_max_connections(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:", max_connections=15)
        stats = pool.get_pool_stats()
        assert stats["pool_configuration"]["max_connections"] == 15

    def test_pool_configuration_has_pool_timeout(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:", pool_timeout=45)
        stats = pool.get_pool_stats()
        assert stats["pool_configuration"]["pool_timeout"] == 45

    def test_recent_connection_times_present(self):
        pool = DatabaseConnectionPool(database_url="sqlite:///:memory:")
        stats = pool.get_pool_stats()
        assert "recent_connection_times" in stats
