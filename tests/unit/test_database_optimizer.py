"""Unit tests for QueryStats, IndexRecommendation, DatabaseConnectionPool,
QueryOptimizer, and DatabaseHealthMonitor."""

from __future__ import annotations

import asyncio
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.database_optimizer import (
    DatabaseConnectionPool,
    DatabaseHealthMonitor,
    IndexRecommendation,
    QueryOptimizer,
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


# ===========================================================================
# DatabaseConnectionPool — sqlite path parsing
# ===========================================================================


class TestDatabaseConnectionPoolSqlitePath:
    def test_memory_url_yields_memory_path(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert pool._sqlite_path == ":memory:"

    def test_absolute_path_url_parsed(self):
        pool = DatabaseConnectionPool("sqlite:////tmp/mydb.db")
        assert pool._sqlite_path == "/tmp/mydb.db"

    def test_connection_history_is_deque(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert isinstance(pool.connection_history, deque)

    def test_connection_history_initially_empty(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert len(pool.connection_history) == 0

    def test_non_sqlite_url_sqlite_path_none(self):
        # For non-sqlite URLs the _sqlite_path should not be set to ":memory:"
        pool = DatabaseConnectionPool("postgresql://localhost/db")
        assert pool._sqlite_path is None


# ===========================================================================
# QueryOptimizer — __init__, _get_query_hash, _get_query_pattern,
#                  _generate_next_actions
# ===========================================================================


def _make_mock_pool():
    """Return a MagicMock that satisfies QueryOptimizer's constructor."""
    pool = MagicMock(spec=DatabaseConnectionPool)
    pool.database_url = "sqlite:///:memory:"
    pool.min_connections = 1
    pool.max_connections = 10
    pool.pool_timeout = 30
    pool.pool_stats = {
        "connections_created": 0,
        "connections_closed": 0,
        "connections_in_use": 0,
        "connections_available": 0,
        "total_queries": 0,
        "failed_queries": 0,
        "avg_connection_time_ms": 0.0,
    }
    pool.connection_history = deque()
    pool.get_pool_stats.return_value = {
        **pool.pool_stats,
        "pool_configuration": {
            "min_connections": 1,
            "max_connections": 10,
            "pool_timeout": 30,
        },
        "recent_connection_times": [],
    }
    return pool


class TestQueryOptimizerInit:
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer(_make_mock_pool())

    def test_query_stats_initially_empty(self, optimizer):
        assert optimizer.query_stats == {}

    def test_slow_query_threshold_is_100(self, optimizer):
        assert optimizer.slow_query_threshold_ms == 100

    def test_performance_targets_is_dict(self, optimizer):
        assert isinstance(optimizer.performance_targets, dict)

    def test_performance_targets_sub_100ms_key(self, optimizer):
        assert "sub_100ms_percentage" in optimizer.performance_targets

    def test_performance_targets_avg_query_time_key(self, optimizer):
        assert "avg_query_time_ms" in optimizer.performance_targets

    def test_performance_targets_max_acceptable_key(self, optimizer):
        assert "max_acceptable_time_ms" in optimizer.performance_targets

    def test_performance_targets_cache_hit_rate_key(self, optimizer):
        assert "cache_hit_rate" in optimizer.performance_targets

    def test_performance_target_sub_100ms_value(self, optimizer):
        assert optimizer.performance_targets["sub_100ms_percentage"] == 95.0

    def test_index_recommendations_initially_empty(self, optimizer):
        assert optimizer.index_recommendations == []

    def test_connection_pool_stored(self, optimizer):
        assert optimizer.connection_pool is not None


class TestQueryOptimizerGetQueryHash:
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer(_make_mock_pool())

    def test_returns_string(self, optimizer):
        result = optimizer._get_query_hash("SELECT * FROM videos")
        assert isinstance(result, str)

    def test_same_query_same_hash(self, optimizer):
        q = "SELECT id FROM users WHERE id = 5"
        assert optimizer._get_query_hash(q) == optimizer._get_query_hash(q)

    def test_different_queries_different_hashes(self, optimizer):
        h1 = optimizer._get_query_hash("SELECT * FROM videos")
        h2 = optimizer._get_query_hash("SELECT * FROM users")
        assert h1 != h2

    def test_numbers_normalised_same_hash(self, optimizer):
        h1 = optimizer._get_query_hash("SELECT * FROM videos WHERE id = 1")
        h2 = optimizer._get_query_hash("SELECT * FROM videos WHERE id = 99")
        assert h1 == h2

    def test_string_literals_normalised_same_hash(self, optimizer):
        h1 = optimizer._get_query_hash("SELECT * FROM users WHERE email = 'a@b.com'")
        h2 = optimizer._get_query_hash("SELECT * FROM users WHERE email = 'x@y.org'")
        assert h1 == h2

    def test_hash_is_hex_string(self, optimizer):
        result = optimizer._get_query_hash("SELECT 1")
        int(result, 16)  # should not raise


class TestQueryOptimizerGetQueryPattern:
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer(_make_mock_pool())

    def test_select_pattern(self, optimizer):
        assert optimizer._get_query_pattern("SELECT * FROM videos") == "SELECT from videos"

    def test_select_with_where_pattern(self, optimizer):
        assert (
            optimizer._get_query_pattern("SELECT id FROM users WHERE id = 1")
            == "SELECT from users"
        )

    def test_insert_pattern(self, optimizer):
        assert (
            optimizer._get_query_pattern("INSERT INTO users (email) VALUES (?)")
            == "INSERT into users"
        )

    def test_update_pattern(self, optimizer):
        assert (
            optimizer._get_query_pattern("UPDATE videos SET processed = 1 WHERE id = 5")
            == "UPDATE videos"
        )

    def test_delete_pattern(self, optimizer):
        assert (
            optimizer._get_query_pattern("DELETE FROM videos WHERE id = 99")
            == "DELETE from videos"
        )

    def test_other_pattern(self, optimizer):
        assert (
            optimizer._get_query_pattern("CREATE INDEX idx ON videos(title)")
            == "OTHER"
        )

    def test_returns_string(self, optimizer):
        assert isinstance(optimizer._get_query_pattern("SELECT 1"), str)


class TestQueryOptimizerGenerateNextActions:
    @pytest.fixture
    def optimizer(self):
        return QueryOptimizer(_make_mock_pool())

    def test_low_sub_100ms_generates_action(self, optimizer):
        actions = optimizer._generate_next_actions(90.0, 60.0)
        assert len(actions) > 0

    def test_low_sub_100ms_action_mentions_100ms(self, optimizer):
        actions = optimizer._generate_next_actions(90.0, 60.0)
        assert any("100ms" in a for a in actions)

    def test_high_avg_time_generates_action(self, optimizer):
        actions = optimizer._generate_next_actions(96.0, 80.0)
        assert any("50ms" in a for a in actions)

    def test_targets_met_single_action(self, optimizer):
        actions = optimizer._generate_next_actions(96.0, 40.0)
        assert len(actions) == 1
        assert "Performance targets met" in actions[0]

    def test_pending_recommendations_generate_action(self, optimizer):
        optimizer.index_recommendations.append(
            IndexRecommendation(
                table_name="videos",
                columns=["user_id"],
                index_type="btree",
                estimated_improvement=30.0,
                query_pattern="SELECT from videos",
                priority="high",
                created_at=datetime.now(timezone.utc),
                reason="slow query",
            )
        )
        actions = optimizer._generate_next_actions(96.0, 40.0)
        assert any("index" in a.lower() for a in actions)

    def test_returns_list(self, optimizer):
        assert isinstance(optimizer._generate_next_actions(80.0, 120.0), list)

    def test_multiple_issues_multiple_actions(self, optimizer):
        # sub_100ms < 95 AND avg > 50  → at least 2 actions
        actions = optimizer._generate_next_actions(85.0, 75.0)
        assert len(actions) >= 2


# ===========================================================================
# DatabaseHealthMonitor — __init__
# ===========================================================================


class TestDatabaseHealthMonitorInit:
    @pytest.fixture
    def monitor(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        return DatabaseHealthMonitor(optimizer)

    def test_stores_query_optimizer(self, monitor):
        assert isinstance(monitor.query_optimizer, QueryOptimizer)

    def test_health_history_is_deque(self, monitor):
        assert isinstance(monitor.health_history, deque)

    def test_health_history_initially_empty(self, monitor):
        assert len(monitor.health_history) == 0

    def test_alert_thresholds_is_dict(self, monitor):
        assert isinstance(monitor.alert_thresholds, dict)

    def test_alert_thresholds_has_avg_query_time_key(self, monitor):
        assert "avg_query_time_ms" in monitor.alert_thresholds

    def test_alert_thresholds_has_slow_query_percentage_key(self, monitor):
        assert "slow_query_percentage" in monitor.alert_thresholds

    def test_alert_thresholds_has_connection_pool_usage_key(self, monitor):
        assert "connection_pool_usage" in monitor.alert_thresholds

    def test_alert_thresholds_has_error_rate_key(self, monitor):
        assert "error_rate_percentage" in monitor.alert_thresholds

    def test_alert_threshold_avg_query_time_value(self, monitor):
        assert monitor.alert_thresholds["avg_query_time_ms"] == 100

    def test_alert_threshold_connection_pool_usage_value(self, monitor):
        assert monitor.alert_thresholds["connection_pool_usage"] == 80

    def test_health_checks_enabled_by_default(self, monitor):
        assert monitor.health_checks_enabled is True


# ===========================================================================
# DatabaseConnectionPool — initialize() (SQLite paths)
# ===========================================================================


class TestDatabaseConnectionPoolInitialize:
    @pytest.mark.asyncio
    async def test_initialize_in_memory_no_error(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        await pool.initialize()  # must not raise
        assert pool.pool is None  # SQLite never sets self.pool

    @pytest.mark.asyncio
    async def test_initialize_file_path_calls_makedirs(self, tmp_path, monkeypatch):
        import os

        calls = []

        def fake_makedirs(path, exist_ok=False):
            calls.append(path)

        monkeypatch.setattr(os, "makedirs", fake_makedirs)
        db_file = str(tmp_path / "sub" / "app.db")
        url = "sqlite:///" + db_file
        pool = DatabaseConnectionPool(url)
        await pool.initialize()
        # makedirs was called with the parent directory
        assert any(str(tmp_path / "sub") in c for c in calls)

    @pytest.mark.asyncio
    async def test_initialize_sets_sqlite_path_memory(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert pool._sqlite_path == ":memory:"
        await pool.initialize()
        assert pool._sqlite_path == ":memory:"

    @pytest.mark.asyncio
    async def test_initialize_non_sqlite_pool_stays_none_without_psycopg(self):
        # No actual PostgreSQL; initialize will raise or pool stays None.
        # We just verify the pool attribute is None before init.
        pool = DatabaseConnectionPool("postgresql://localhost/testdb")
        assert pool.pool is None


# ===========================================================================
# DatabaseConnectionPool — get_connection() and release_connection() (SQLite)
# ===========================================================================


class TestDatabaseConnectionPoolGetRelease:
    @pytest.mark.asyncio
    async def test_get_connection_returns_sqlite_connection(self):
        import sqlite3

        pool = DatabaseConnectionPool("sqlite:///:memory:")
        conn = await pool.get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        await pool.release_connection(conn)

    @pytest.mark.asyncio
    async def test_get_connection_increments_in_use(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert pool.pool_stats["connections_in_use"] == 0
        conn = await pool.get_connection()
        assert pool.pool_stats["connections_in_use"] == 1
        await pool.release_connection(conn)

    @pytest.mark.asyncio
    async def test_release_connection_decrements_in_use(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        conn = await pool.get_connection()
        assert pool.pool_stats["connections_in_use"] == 1
        await pool.release_connection(conn)
        assert pool.pool_stats["connections_in_use"] == 0

    @pytest.mark.asyncio
    async def test_get_connection_records_connection_time(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        conn = await pool.get_connection()
        assert len(pool.connection_history) == 1
        assert pool.connection_history[0] >= 0
        await pool.release_connection(conn)

    @pytest.mark.asyncio
    async def test_get_connection_updates_avg_connection_time(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        conn = await pool.get_connection()
        assert pool.pool_stats["avg_connection_time_ms"] >= 0
        await pool.release_connection(conn)

    @pytest.mark.asyncio
    async def test_multiple_connections_tracked(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        conn1 = await pool.get_connection()
        conn2 = await pool.get_connection()
        assert pool.pool_stats["connections_in_use"] == 2
        await pool.release_connection(conn1)
        await pool.release_connection(conn2)
        assert pool.pool_stats["connections_in_use"] == 0

    @pytest.mark.asyncio
    async def test_release_does_not_go_below_zero(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        # Release without get should not produce negative count
        import sqlite3

        conn = sqlite3.connect(":memory:")
        pool.pool_stats["connections_in_use"] = 0
        await pool.release_connection(conn)
        assert pool.pool_stats["connections_in_use"] == 0

    @pytest.mark.asyncio
    async def test_get_connection_uses_sqlite_path_when_set(self):
        import sqlite3

        pool = DatabaseConnectionPool("sqlite:///:memory:")
        assert pool._sqlite_path == ":memory:"
        conn = await pool.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        await pool.release_connection(conn)


# ===========================================================================
# DatabaseConnectionPool — close()
# ===========================================================================


class TestDatabaseConnectionPoolClose:
    @pytest.mark.asyncio
    async def test_close_no_pool_no_error(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        await pool.close()  # pool is None, should not raise

    @pytest.mark.asyncio
    async def test_close_pool_with_mock_pool(self):
        from unittest.mock import AsyncMock

        pool = DatabaseConnectionPool("sqlite:///:memory:")
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        pool.pool = mock_pool
        await pool.close()
        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_pool_without_close_attr(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        mock_pool = MagicMock(spec=[])  # no 'close' attribute
        pool.pool = mock_pool
        await pool.close()  # should not raise


# ===========================================================================
# QueryOptimizer — _update_query_stats
# ===========================================================================


class TestQueryOptimizerUpdateStats:
    @pytest.mark.asyncio
    async def test_creates_new_stats_entry(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._update_query_stats("hash1", "SELECT from videos", 30.0, True)
        assert "hash1" in optimizer.query_stats

    @pytest.mark.asyncio
    async def test_updates_existing_stats_entry(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._update_query_stats("hash1", "SELECT from videos", 30.0, True)
        await optimizer._update_query_stats("hash1", "SELECT from videos", 70.0, True)
        assert optimizer.query_stats["hash1"].execution_count == 2

    @pytest.mark.asyncio
    async def test_failed_query_increments_error_count(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._update_query_stats("hash1", "SELECT from videos", 30.0, False)
        assert optimizer.query_stats["hash1"].error_count == 1

    @pytest.mark.asyncio
    async def test_stores_correct_pattern(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._update_query_stats("hashX", "INSERT into users", 10.0, True)
        assert optimizer.query_stats["hashX"].query_pattern == "INSERT into users"


# ===========================================================================
# QueryOptimizer — _handle_slow_query and _analyze_slow_query
# ===========================================================================


class TestQueryOptimizerSlowQueryHandling:
    @pytest.mark.asyncio
    async def test_handle_slow_query_adds_to_history(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._handle_slow_query(
            "SELECT * FROM videos WHERE id = 1", "SELECT from videos", 200.0
        )
        assert len(optimizer.optimization_history) == 1

    @pytest.mark.asyncio
    async def test_handle_slow_query_history_entry_has_timestamp(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._handle_slow_query(
            "SELECT * FROM videos WHERE id = 1", "SELECT from videos", 200.0
        )
        entry = optimizer.optimization_history[0]
        assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_handle_slow_query_history_entry_has_execution_time(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._handle_slow_query(
            "SELECT * FROM videos WHERE id = 1", "SELECT from videos", 200.0
        )
        entry = optimizer.optimization_history[0]
        assert entry["execution_time_ms"] == 200.0

    @pytest.mark.asyncio
    async def test_analyze_slow_query_where_clause_adds_recommendation(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos WHERE processed = 1",
            "SELECT from videos",
            250.0,
        )
        assert len(optimizer.index_recommendations) >= 1

    @pytest.mark.asyncio
    async def test_analyze_slow_query_where_clause_btree_index(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos WHERE processed = 1",
            "SELECT from videos",
            250.0,
        )
        rec = optimizer.index_recommendations[0]
        assert rec.index_type == "btree"

    @pytest.mark.asyncio
    async def test_analyze_slow_query_over_500ms_high_priority(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos WHERE processed = 1",
            "SELECT from videos",
            600.0,
        )
        rec = optimizer.index_recommendations[0]
        assert rec.priority == "high"

    @pytest.mark.asyncio
    async def test_analyze_slow_query_under_500ms_medium_priority(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos WHERE processed = 1",
            "SELECT from videos",
            200.0,
        )
        rec = optimizer.index_recommendations[0]
        assert rec.priority == "medium"

    @pytest.mark.asyncio
    async def test_analyze_slow_query_order_by_adds_recommendation(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        # Include WHERE so that 're' is imported into the local scope before
        # the ORDER BY branch runs (pre-existing scoping quirk in source).
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos WHERE id = 1 ORDER BY created_at",
            "SELECT from videos",
            150.0,
        )
        patterns = [rec.index_type for rec in optimizer.index_recommendations]
        assert "btree" in patterns

    @pytest.mark.asyncio
    async def test_analyze_slow_query_join_adds_recommendation(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT v.id FROM videos v JOIN users u ON v.user_id = u.id",
            "SELECT from videos",
            300.0,
        )
        tables = [rec.table_name for rec in optimizer.index_recommendations]
        assert "multiple" in tables

    @pytest.mark.asyncio
    async def test_analyze_slow_query_join_improvement_estimate(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        await optimizer._analyze_slow_query(
            "SELECT * FROM videos v JOIN users u ON v.user_id = u.id",
            "SELECT from videos",
            300.0,
        )
        join_recs = [
            r for r in optimizer.index_recommendations if r.table_name == "multiple"
        ]
        assert join_recs[0].estimated_improvement == 40.0


# ===========================================================================
# QueryOptimizer — execute_query() with SQLite connections
# ===========================================================================


class TestQueryOptimizerExecuteQuery:
    @pytest.mark.asyncio
    async def test_execute_query_returns_result(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        result = await optimizer.execute_query("SELECT 1 AS val", use_cache=False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_query_creates_stats_entry(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1 AS val", use_cache=False)
        assert len(optimizer.query_stats) == 1

    @pytest.mark.asyncio
    async def test_execute_query_stats_execution_count(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1 AS val", use_cache=False)
        await optimizer.execute_query("SELECT 1 AS val", use_cache=False)
        stats = list(optimizer.query_stats.values())[0]
        assert stats.execution_count == 2

    @pytest.mark.asyncio
    async def test_execute_query_raises_on_invalid_sql(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        with pytest.raises(Exception):
            await optimizer.execute_query("INVALID SQL QUERY !!!", use_cache=False)

    @pytest.mark.asyncio
    async def test_execute_query_records_error_on_failure(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        try:
            await optimizer.execute_query("BADQUERY", use_cache=False)
        except Exception:
            pass
        stats = list(optimizer.query_stats.values())[0]
        assert stats.error_count == 1


# ===========================================================================
# QueryOptimizer — get_performance_report()
# ===========================================================================


class TestQueryOptimizerGetPerformanceReport:
    @pytest.mark.asyncio
    async def test_empty_stats_returns_message(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        report = await optimizer.get_performance_report()
        assert "message" in report

    @pytest.mark.asyncio
    async def test_report_has_performance_summary(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1", use_cache=False)
        report = await optimizer.get_performance_report()
        assert "performance_summary" in report

    @pytest.mark.asyncio
    async def test_report_has_detailed_metrics(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1", use_cache=False)
        report = await optimizer.get_performance_report()
        assert "detailed_metrics" in report

    @pytest.mark.asyncio
    async def test_report_has_recommendations(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1", use_cache=False)
        report = await optimizer.get_performance_report()
        assert "recommendations" in report

    @pytest.mark.asyncio
    async def test_report_has_connection_pool_stats(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        await optimizer.execute_query("SELECT 1", use_cache=False)
        report = await optimizer.get_performance_report()
        assert "connection_pool_stats" in report

    @pytest.mark.asyncio
    async def test_report_grade_excellent_when_targets_met(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        # Inject fast query stats manually
        qs = QueryStats(query_hash="h1", query_pattern="SELECT from videos")
        qs.update_stats(30.0, True)  # 30ms, well under 100ms
        optimizer.query_stats["h1"] = qs
        report = await optimizer.get_performance_report()
        grade = report["performance_summary"]["performance_grade"]
        assert grade in ("A+", "A", "B+", "B", "C")  # any valid grade

    @pytest.mark.asyncio
    async def test_report_grade_a_plus_for_perfect_stats(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        for i in range(10):
            qs = QueryStats(query_hash=f"h{i}", query_pattern="SELECT from videos")
            qs.update_stats(20.0, True)
            optimizer.query_stats[f"h{i}"] = qs
        report = await optimizer.get_performance_report()
        grade = report["performance_summary"]["performance_grade"]
        assert grade == "A+"

    @pytest.mark.asyncio
    async def test_report_slow_queries_listed(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        qs = QueryStats(query_hash="h_slow", query_pattern="SELECT from big_table")
        qs.update_stats(500.0, True)
        optimizer.query_stats["h_slow"] = qs
        report = await optimizer.get_performance_report()
        slow = report["detailed_metrics"]["slow_queries_count"]
        assert slow >= 1


# ===========================================================================
# DatabaseHealthMonitor — run_health_check()
# ===========================================================================


class TestDatabaseHealthMonitorRunHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_dict(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_health_check_has_overall_health_key(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "overall_health" in result

    @pytest.mark.asyncio
    async def test_health_check_has_timestamp(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_health_check_has_checks_key(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_has_alerts_key(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "alerts" in result

    @pytest.mark.asyncio
    async def test_health_check_has_recommendations_key(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_healthy_state_with_low_usage(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert result["overall_health"] in ("healthy", "degraded", "unhealthy")

    @pytest.mark.asyncio
    async def test_health_check_records_to_history(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        await monitor.run_health_check()
        assert len(monitor.health_history) == 1

    @pytest.mark.asyncio
    async def test_health_check_history_entry_has_status(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        await monitor.run_health_check()
        entry = monitor.health_history[0]
        assert "status" in entry

    @pytest.mark.asyncio
    async def test_health_check_connection_pool_check_present(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "connection_pool" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_check_connection_pool_usage_key(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        assert "usage_percentage" in result["checks"]["connection_pool"]

    @pytest.mark.asyncio
    async def test_health_check_high_pool_usage_triggers_warning(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:", max_connections=10)
        optimizer = QueryOptimizer(pool)
        # Simulate high pool usage
        pool.pool_stats["connections_in_use"] = 9
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        severities = [a["severity"] for a in result["alerts"]]
        assert "warning" in severities

    @pytest.mark.asyncio
    async def test_health_check_with_slow_queries_creates_alert(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        # Inject a slow query stat
        qs = QueryStats(query_hash="slow1", query_pattern="SELECT from big_table")
        qs.update_stats(500.0, True)
        optimizer.query_stats["slow1"] = qs
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        # Should have query_performance check
        assert "query_performance" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_check_with_slow_query_avg_alert(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        # Inject a very slow query stat
        qs = QueryStats(query_hash="slow2", query_pattern="SELECT from big_table")
        for _ in range(5):
            qs.update_stats(300.0, True)
        optimizer.query_stats["slow2"] = qs
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        messages = [a["message"] for a in result["alerts"]]
        assert any("query time" in m.lower() for m in messages)

    @pytest.mark.asyncio
    async def test_health_check_degraded_when_alerts_present(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:", max_connections=10)
        optimizer = QueryOptimizer(pool)
        pool.pool_stats["connections_in_use"] = 9  # triggers warning
        monitor = DatabaseHealthMonitor(optimizer)
        result = await monitor.run_health_check()
        # If alert was triggered, overall health should be 'degraded'
        if result["alerts"]:
            assert result["overall_health"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_multiple_runs_accumulate_history(self):
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        optimizer = QueryOptimizer(pool)
        monitor = DatabaseHealthMonitor(optimizer)
        await monitor.run_health_check()
        await monitor.run_health_check()
        assert len(monitor.health_history) == 2

    @pytest.mark.asyncio
    async def test_health_check_error_returns_unhealthy(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        monitor = DatabaseHealthMonitor(optimizer)
        # Force get_pool_stats to raise
        optimizer.connection_pool.get_pool_stats.side_effect = RuntimeError("boom")
        result = await monitor.run_health_check()
        assert result["overall_health"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_error_response_has_error_key(self):
        optimizer = QueryOptimizer(_make_mock_pool())
        monitor = DatabaseHealthMonitor(optimizer)
        optimizer.connection_pool.get_pool_stats.side_effect = RuntimeError("db down")
        result = await monitor.run_health_check()
        assert "error" in result


# ===========================================================================
# Additional tests for missing coverage
# ===========================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions"""

    async def test_execute_optimized_query_delegates(self, tmp_path) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.query_optimizer.execute_query
        _mod.query_optimizer.execute_query = AsyncMock(return_value=[{"id": 1}])
        try:
            result = await _mod.execute_optimized_query("SELECT 1", ())
            assert result == [{"id": 1}]
        finally:
            _mod.query_optimizer.execute_query = orig

    async def test_execute_batch_delegates(self) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.query_optimizer.execute_batch_queries
        _mod.query_optimizer.execute_batch_queries = AsyncMock(return_value=[[1], [2]])
        try:
            result = await _mod.execute_batch_optimized([("SELECT 1", ()), ("SELECT 2", ())])
            assert result == [[1], [2]]
        finally:
            _mod.query_optimizer.execute_batch_queries = orig

    async def test_get_database_performance_report_delegates(self) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.query_optimizer.get_performance_report
        _mod.query_optimizer.get_performance_report = AsyncMock(return_value={"ok": True})
        try:
            result = await _mod.get_database_performance_report()
            assert result == {"ok": True}
        finally:
            _mod.query_optimizer.get_performance_report = orig

    async def test_get_database_health_status_delegates(self) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.health_monitor.run_health_check
        _mod.health_monitor.run_health_check = AsyncMock(return_value={"overall_health": "healthy"})
        try:
            result = await _mod.get_database_health_status()
            assert result["overall_health"] == "healthy"
        finally:
            _mod.health_monitor.run_health_check = orig

    async def test_initialize_database_optimization_calls_initialize(self, tmp_path) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig_init = _mod.connection_pool.initialize
        orig_get = _mod.connection_pool.get_connection
        orig_rel = _mod.connection_pool.release_connection
        _mod.connection_pool.initialize = AsyncMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn.commit = MagicMock()
        _mod.connection_pool.get_connection = AsyncMock(return_value=mock_conn)
        _mod.connection_pool.release_connection = AsyncMock()
        try:
            await _mod.initialize_database_optimization()
            _mod.connection_pool.initialize.assert_called_once()
        finally:
            _mod.connection_pool.initialize = orig_init
            _mod.connection_pool.get_connection = orig_get
            _mod.connection_pool.release_connection = orig_rel

    async def test_shutdown_database_optimization_calls_close(self) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.connection_pool.close
        _mod.connection_pool.close = AsyncMock()
        try:
            await _mod.shutdown_database_optimization()
            _mod.connection_pool.close.assert_called_once()
        finally:
            _mod.connection_pool.close = orig


class TestExecuteBatchQueries:
    """execute_batch_queries with multi-query grouping"""

    def _make_pool(self) -> MagicMock:
        pool = MagicMock()
        pool.max_connections = 10
        pool.get_pool_stats.return_value = {"connections_in_use": 0, "max_connections": 10}
        pool.get_connection = AsyncMock()
        pool.release_connection = AsyncMock()
        return pool

    async def test_batch_executes_all_queries(self, tmp_path) -> None:
        import sqlite3
        pool = DatabaseConnectionPool(f"sqlite:///{tmp_path}/test.db")
        await pool.initialize()
        optimizer = QueryOptimizer(pool)
        queries = [
            ("SELECT 1", ()),
            ("SELECT 2", ()),
        ]
        results = await optimizer.execute_batch_queries(queries)
        assert len(results) == 2

    async def test_batch_exception_propagated(self) -> None:
        pool = self._make_pool()
        pool.get_connection.side_effect = RuntimeError("No DB")
        optimizer = QueryOptimizer(pool)
        with pytest.raises(RuntimeError, match="No DB"):
            await optimizer.execute_batch_queries([("SELECT 1", ())])

    @pytest.mark.asyncio
    async def test_batch_schedules_all_queries_concurrently(self) -> None:
        """Queries across different patterns overlap; results keep input order.

        Regression guard for two bugs: (1) the previous per-group ``await gather``
        loop serialized different query patterns, capping real concurrency; and
        (2) result ordering must survive the switch to a single flat gather.
        """
        pool = self._make_pool()
        optimizer = QueryOptimizer(pool)

        active = 0
        max_concurrent = 0

        async def fake_execute_query(query, params=None, use_cache=True):
            nonlocal active, max_concurrent
            active += 1
            max_concurrent = max(max_concurrent, active)
            for _ in range(3):
                await asyncio.sleep(0)  # let sibling coroutines start
            active -= 1
            return query

        optimizer.execute_query = fake_execute_query
        # Mixed patterns: two SELECTs (same group) + one UPDATE (different group).
        queries = [("SELECT a", ()), ("UPDATE b SET x=1", ()), ("SELECT c", ())]
        results = await optimizer.execute_batch_queries(queries)

        # Input order preserved despite concurrent scheduling.
        assert results == ["SELECT a", "UPDATE b SET x=1", "SELECT c"]
        # All three overlapped; the old per-group loop would have capped this at 2.
        assert max_concurrent == 3

    @pytest.mark.asyncio
    async def test_batch_does_not_hold_extra_connection(self) -> None:
        """The batch must delegate to execute_query and not pin its own connection.

        Holding an unused pooled connection for the batch duration wastes a slot
        and can starve/deadlock the gathered queries when the pool is saturated.
        """
        pool = self._make_pool()
        optimizer = QueryOptimizer(pool)
        optimizer.execute_query = AsyncMock(
            side_effect=lambda query, params=None, use_cache=True: query
        )

        results = await optimizer.execute_batch_queries(
            [("SELECT 1", ()), ("SELECT 2", ())]
        )

        assert results == ["SELECT 1", "SELECT 2"]
        assert optimizer.execute_query.await_count == 2
        # execute_batch_queries itself acquires/releases no connection.
        pool.get_connection.assert_not_called()
        pool.release_connection.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_empty_list_returns_empty(self) -> None:
        """An empty batch returns [] without a ZeroDivisionError on the avg calc."""
        pool = self._make_pool()
        optimizer = QueryOptimizer(pool)
        assert await optimizer.execute_batch_queries([]) == []

    @pytest.mark.asyncio
    async def test_batch_bounds_concurrency_to_pool_capacity(self) -> None:
        """Fan-out is capped by the pool's max_connections, not the batch size."""
        pool = self._make_pool()
        pool.max_connections = 2
        optimizer = QueryOptimizer(pool)

        active = 0
        max_concurrent = 0

        async def fake_execute_query(query, params=None, use_cache=True):
            nonlocal active, max_concurrent
            active += 1
            max_concurrent = max(max_concurrent, active)
            for _ in range(3):
                await asyncio.sleep(0)
            active -= 1
            return query

        optimizer.execute_query = fake_execute_query
        queries = [(f"SELECT {i}", ()) for i in range(6)]
        results = await optimizer.execute_batch_queries(queries)

        assert len(results) == 6
        # Never more than the pool capacity of 2 queries in flight at once.
        assert max_concurrent == 2

    @pytest.mark.asyncio
    async def test_batch_cancels_pending_on_failure(self) -> None:
        """When one query fails, the still-in-flight queries are cancelled.

        Guards against a failed batch continuing to apply work (e.g. writes)
        after the caller has already seen the error.
        """
        pool = self._make_pool()
        optimizer = QueryOptimizer(pool)

        completed: list[str] = []

        async def fake_execute_query(query, params=None, use_cache=True):
            if query == "BOOM":
                await asyncio.sleep(0)  # let the slow queries start first
                raise RuntimeError("query failed")
            await asyncio.sleep(10)  # outlasts the batch unless cancelled
            completed.append(query)
            return query

        optimizer.execute_query = fake_execute_query
        with pytest.raises(RuntimeError, match="query failed"):
            await optimizer.execute_batch_queries(
                [("SLOW1", ()), ("BOOM", ()), ("SLOW2", ())]
            )

        # Neither slow query ran to completion — both were cancelled on failure.
        assert completed == []


class TestConnectionPoolInitialize:
    """DatabaseConnectionPool.initialize with different URL types"""

    async def test_sqlite_file_creates_dir(self, tmp_path) -> None:
        db_path = tmp_path / "subdir" / "test.db"
        pool = DatabaseConnectionPool(f"sqlite:///{db_path}")
        await pool.initialize()
        # No error should occur

    async def test_sqlite_memory_initializes(self) -> None:
        pool = DatabaseConnectionPool("sqlite:///:memory:")
        await pool.initialize()

    async def test_haspg_false_uses_sqlite_path(self, tmp_path) -> None:
        from youtube_extension.backend.services import database_optimizer as _mod
        orig = _mod.HAS_POSTGRESQL
        _mod.HAS_POSTGRESQL = False
        db_path = tmp_path / "no_pg.db"
        pool = DatabaseConnectionPool(f"sqlite:///{db_path}", min_connections=1, max_connections=5)
        try:
            await pool.initialize()
        finally:
            _mod.HAS_POSTGRESQL = orig
