"""Unit tests for QueryStats, IndexRecommendation, DatabaseConnectionPool,
QueryOptimizer, and DatabaseHealthMonitor."""

from __future__ import annotations

import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

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
