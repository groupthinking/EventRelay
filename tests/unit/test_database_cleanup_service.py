"""Unit tests for RetentionPolicy, CleanupResult, and DatabaseCleanupService."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.database_cleanup_service import (
    CleanupResult,
    DatabaseCleanupService,
    RetentionPolicy,
)

# ===========================================================================
# RetentionPolicy dataclass
# ===========================================================================


class TestRetentionPolicy:
    def test_required_fields_stored(self):
        p = RetentionPolicy(table_name="api_usage", retention_days=90)
        assert p.table_name == "api_usage"
        assert p.retention_days == 90

    def test_batch_size_default(self):
        p = RetentionPolicy(table_name="t", retention_days=30)
        assert p.batch_size == 1000

    def test_enabled_default_true(self):
        p = RetentionPolicy(table_name="t", retention_days=30)
        assert p.enabled is True

    def test_description_default_empty(self):
        p = RetentionPolicy(table_name="t", retention_days=30)
        assert p.description == ""

    def test_custom_batch_size(self):
        p = RetentionPolicy(table_name="t", retention_days=30, batch_size=5000)
        assert p.batch_size == 5000

    def test_disabled_policy(self):
        p = RetentionPolicy(table_name="t", retention_days=30, enabled=False)
        assert p.enabled is False

    def test_custom_description(self):
        p = RetentionPolicy(table_name="t", retention_days=30, description="Keep 30 days")
        assert p.description == "Keep 30 days"


# ===========================================================================
# CleanupResult dataclass
# ===========================================================================


class TestCleanupResult:
    def _make(self, **kw) -> CleanupResult:
        defaults = dict(
            database_path="/tmp/test.db",
            table_name="api_usage",
            records_deleted=100,
            space_freed_mb=0.5,
            execution_time_ms=250.0,
            timestamp=datetime.now(timezone.utc),
            success=True,
        )
        return CleanupResult(**{**defaults, **kw})

    def test_required_fields_stored(self):
        r = self._make()
        assert r.database_path == "/tmp/test.db"
        assert r.table_name == "api_usage"
        assert r.records_deleted == 100

    def test_success_stored(self):
        assert self._make(success=True).success is True
        assert self._make(success=False).success is False

    def test_error_message_default_none(self):
        assert self._make().error_message is None

    def test_error_message_stored(self):
        r = self._make(success=False, error_message="Table not found")
        assert r.error_message == "Table not found"

    def test_space_freed_stored(self):
        r = self._make(space_freed_mb=1.25)
        assert r.space_freed_mb == 1.25

    def test_execution_time_stored(self):
        r = self._make(execution_time_ms=42.5)
        assert r.execution_time_ms == 42.5


# ===========================================================================
# DatabaseCleanupService._load_default_policies
# ===========================================================================


class TestLoadDefaultPolicies:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "no_config.json"))

    def test_returns_dict(self, svc):
        policies = svc._load_default_policies()
        assert isinstance(policies, dict)

    def test_performance_monitoring_db_present(self, svc):
        policies = svc._load_default_policies()
        assert "performance_monitoring.db" in policies

    def test_performance_db_has_multiple_tables(self, svc):
        policies = svc._load_default_policies()
        tables = [p.table_name for p in policies["performance_monitoring.db"]]
        assert "performance_metrics" in tables
        assert "performance_alerts" in tables
        assert "benchmark_results" in tables

    def test_performance_metrics_retention_30_days(self, svc):
        policies = svc._load_default_policies()
        pm_policy = next(
            p for p in policies["performance_monitoring.db"]
            if p.table_name == "performance_metrics"
        )
        assert pm_policy.retention_days == 30

    def test_all_default_policies_enabled(self, svc):
        policies = svc._load_default_policies()
        for db_policies in policies.values():
            for p in db_policies:
                assert p.enabled is True


# ===========================================================================
# DatabaseCleanupService.get_database_size_mb
# ===========================================================================


class TestGetDatabaseSizeMb:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_nonexistent_file_returns_zero(self, svc, tmp_path):
        result = svc.get_database_size_mb(str(tmp_path / "missing.db"))
        assert result == 0.0

    def test_existing_file_returns_positive(self, svc, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
        conn.close()
        size = svc.get_database_size_mb(db_path)
        assert size > 0.0

    def test_returns_float(self, svc, tmp_path):
        db_path = str(tmp_path / "test2.db")
        conn = sqlite3.connect(db_path)
        conn.close()
        assert isinstance(svc.get_database_size_mb(db_path), float)


# ===========================================================================
# DatabaseCleanupService.add_retention_policy
# ===========================================================================


class TestAddRetentionPolicy:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_adds_policy_for_new_db(self, svc):
        policy = RetentionPolicy(table_name="events", retention_days=60)
        svc.add_retention_policy("custom.db", policy)
        assert "custom.db" in svc.retention_policies
        tables = [p.table_name for p in svc.retention_policies["custom.db"]]
        assert "events" in tables

    def test_replaces_existing_policy_same_table(self, svc):
        p1 = RetentionPolicy(table_name="logs", retention_days=30)
        p2 = RetentionPolicy(table_name="logs", retention_days=90)
        svc.add_retention_policy("app.db", p1)
        svc.add_retention_policy("app.db", p2)
        matching = [p for p in svc.retention_policies["app.db"] if p.table_name == "logs"]
        assert len(matching) == 1
        assert matching[0].retention_days == 90

    def test_appends_different_table_policies(self, svc):
        svc.add_retention_policy("app.db", RetentionPolicy("table_a", 30))
        svc.add_retention_policy("app.db", RetentionPolicy("table_b", 60))
        tables = [p.table_name for p in svc.retention_policies["app.db"]]
        assert "table_a" in tables
        assert "table_b" in tables


# ===========================================================================
# DatabaseCleanupService.cleanup_table — edge cases
# ===========================================================================


class TestCleanupTable:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_missing_db_returns_failure(self, svc, tmp_path):
        policy = RetentionPolicy("t", retention_days=30)
        result = svc.cleanup_table(str(tmp_path / "nonexistent.db"), policy)
        assert result.success is False
        assert "not found" in (result.error_message or "")

    def test_invalid_table_name_returns_failure(self, svc, tmp_path):
        db = str(tmp_path / "test.db")
        sqlite3.connect(db).close()
        policy = RetentionPolicy("drop table users--", retention_days=30)
        result = svc.cleanup_table(db, policy)
        assert result.success is False
        assert "Invalid table name" in (result.error_message or "")

    def test_missing_table_returns_failure(self, svc, tmp_path):
        db = str(tmp_path / "empty.db")
        sqlite3.connect(db).close()
        policy = RetentionPolicy("nonexistent_table", retention_days=30)
        result = svc.cleanup_table(db, policy)
        assert result.success is False

    def test_cleanup_removes_old_records(self, svc, tmp_path):
        db = str(tmp_path / "data.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY, value REAL, timestamp TEXT)")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        recent_ts = datetime.now(timezone.utc).isoformat()
        conn.execute("INSERT INTO metrics (value, timestamp) VALUES (1.0, ?)", (old_ts,))
        conn.execute("INSERT INTO metrics (value, timestamp) VALUES (2.0, ?)", (recent_ts,))
        conn.commit()
        conn.close()

        policy = RetentionPolicy("metrics", retention_days=30)
        result = svc.cleanup_table(db, policy)

        assert result.success is True
        assert result.records_deleted == 1
        assert result.table_name == "metrics"

    def test_cleanup_preserves_recent_records(self, svc, tmp_path):
        db = str(tmp_path / "data2.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, name TEXT, timestamp TEXT)")
        recent_ts = datetime.now(timezone.utc).isoformat()
        conn.execute("INSERT INTO events (name, timestamp) VALUES ('evt', ?)", (recent_ts,))
        conn.commit()
        conn.close()

        policy = RetentionPolicy("events", retention_days=30)
        result = svc.cleanup_table(db, policy)

        assert result.success is True
        assert result.records_deleted == 0

    def test_cleanup_result_has_timestamp(self, svc, tmp_path):
        db = str(tmp_path / "ts_test.db")
        sqlite3.connect(db).close()
        policy = RetentionPolicy("ghost_table", retention_days=30)
        result = svc.cleanup_table(db, policy)
        assert isinstance(result.timestamp, datetime)


# ===========================================================================
# DatabaseCleanupService.get_cleanup_report
# ===========================================================================


class TestGetCleanupReport:
    @pytest.fixture
    def svc(self, tmp_path):
        return DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))

    def test_report_has_expected_keys(self, svc):
        report = svc.get_cleanup_report()
        assert "cleanup_stats" in report
        assert "retention_policies" in report
        assert "generated_at" in report

    def test_initial_stats_all_zero(self, svc):
        stats = svc.get_cleanup_report()["cleanup_stats"]
        assert stats["total_cleanups"] == 0
        assert stats["total_records_deleted"] == 0
        assert stats["errors"] == 0

    def test_retention_policies_in_report(self, svc):
        policies = svc.get_cleanup_report()["retention_policies"]
        assert isinstance(policies, dict)
        assert "performance_monitoring.db" in policies
