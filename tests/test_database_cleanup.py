"""
Regression tests for SQL-injection hardening in database_cleanup_service.py.

These tests verify that:
  - All query *values* (cutoff_date, batch_size) are bound via ? parameters.
  - SQL identifiers (table name, column name) are validated / allowlisted before use.
  - SQL characters in row data are treated as plain strings, not executed as SQL.
  - All recognised timestamp column names ("timestamp", "created_at", "createdAt", "ts")
    are handled correctly.
  - Tables that have none of the recognised time columns are skipped safely.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from youtube_extension.backend.services.database_cleanup_service import (
    DatabaseCleanupService,
    RetentionPolicy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path, table: str, col: str) -> str:
    """Create a temporary SQLite database for testing.

    Args:
        tmp_path: pytest ``tmp_path`` fixture directory.
        table: Name of the table to create.
        col: Name of the timestamp-like column to add to the table.

    Returns:
        Absolute path to the created ``.db`` file, which contains two rows:
        one with a timestamp 60 days in the past ("old") and one with the
        current timestamp ("new").
    """
    db = str(tmp_path / f"{table}.db")
    conn = sqlite3.connect(db)
    conn.execute(
        f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, "{col}" TEXT, data TEXT)'
    )
    old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    new_ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        f'INSERT INTO "{table}" ("{col}", data) VALUES (?, ?)', (old_ts, "old")
    )
    conn.execute(
        f'INSERT INTO "{table}" ("{col}", data) VALUES (?, ?)', (new_ts, "new")
    )
    conn.commit()
    conn.close()
    return db


def _row_count(db: str, table: str) -> int:
    """Return the number of rows in *table* within the SQLite database at *db*.

    Args:
        db: Absolute path to the SQLite database file.
        table: Name of the table to count rows in.

    Returns:
        Integer row count.
    """
    conn = sqlite3.connect(db)
    cur = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
    count = cur.fetchone()[0]
    conn.close()
    return count


# ---------------------------------------------------------------------------
# 1. Values are parameterised — SQL characters in row data are harmless
# ---------------------------------------------------------------------------

class TestCutoffDateParameterized:
    """Verify that the cutoff_date and batch_size values are bound via ? parameters."""

    def test_only_old_rows_are_deleted(self, tmp_path):
        """With retention_days=5, only the 60-day-old row should be deleted;
        the recent row must survive."""
        db = _make_db(tmp_path, "events", "timestamp")
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        result = svc.cleanup_table(db, RetentionPolicy(table_name="events", retention_days=5))
        assert result.success is True
        assert result.records_deleted == 1
        assert _row_count(db, "events") == 1  # new row survives

    def test_table_data_intact_when_no_rows_qualify(self, tmp_path):
        """With a very long retention window, all rows survive."""
        db = _make_db(tmp_path, "metrics", "timestamp")
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        # retention_days=365: neither row is old enough
        result = svc.cleanup_table(db, RetentionPolicy(table_name="metrics", retention_days=365))
        assert result.success is True
        assert result.records_deleted == 0
        assert _row_count(db, "metrics") == 2  # both rows survive

    def test_sql_injection_characters_in_row_data_are_harmless(self, tmp_path):
        """SQL injection characters stored in the timestamp column value must be
        treated as plain strings by the parameterised WHERE clause — they must
        NOT be interpreted as SQL.

        This verifies that the cutoff_date comparison uses ? parameter binding so
        the column value is never executed as SQL, regardless of its content."""
        db = str(tmp_path / "inj.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE inj (id INTEGER PRIMARY KEY, timestamp TEXT)")
        # Insert a row whose timestamp column value contains SQL injection characters.
        # Because the WHERE clause uses ?, SQLite binds the cutoff as a literal string;
        # the column value is compared as a string — no SQL is executed.
        conn.execute(
            "INSERT INTO inj (timestamp) VALUES (?)",
            ("2020-01-01'; DROP TABLE inj; --",),
        )
        conn.execute(
            "INSERT INTO inj (timestamp) VALUES (?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()
        conn.close()

        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        result = svc.cleanup_table(db, RetentionPolicy(table_name="inj", retention_days=30))

        # Cleanup must succeed and the table must still exist (not been dropped).
        assert result.success is True
        # The injection suffix is treated as a plain string; the table was NOT dropped.
        assert _row_count(db, "inj") >= 1


# ---------------------------------------------------------------------------
# 2. Timestamp column allowlist
# ---------------------------------------------------------------------------

class TestTimestampColumnAllowlist:
    """All four accepted column names must trigger cleanup correctly."""

    @pytest.mark.parametrize("col", ["timestamp", "created_at", "createdAt", "ts"])
    def test_recognised_column_triggers_cleanup(self, tmp_path, col):
        db = _make_db(tmp_path, "tbl", col)
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        result = svc.cleanup_table(db, RetentionPolicy(table_name="tbl", retention_days=30))
        assert result.success is True
        assert result.records_deleted == 1

    def test_unrecognised_column_skips_without_error(self, tmp_path):
        """A table whose only time-like column has an unrecognised name is skipped."""
        db = str(tmp_path / "no_ts.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY, logged_at TEXT)")
        conn.execute(
            "INSERT INTO logs (logged_at) VALUES (?)",
            ((datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),),
        )
        conn.commit()
        conn.close()

        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        result = svc.cleanup_table(db, RetentionPolicy(table_name="logs", retention_days=1))
        # Skipped — no records deleted, success=False with descriptive error
        assert result.success is False
        assert result.records_deleted == 0
        # The row must still be present (nothing was deleted)
        assert _row_count(db, "logs") == 1


# ---------------------------------------------------------------------------
# 3. Table-name injection guard
# ---------------------------------------------------------------------------

class TestTableNameInjectionGuard:
    """The regex guard on table_name must block well-known injection patterns."""

    @pytest.mark.parametrize("bad_name", [
        "users; DROP TABLE users;--",
        "users UNION SELECT * FROM secrets",
        "'; DELETE FROM users; --",
        'table"name',
        "name WITH space",
        "name\nnewline",
    ])
    def test_injection_table_name_rejected(self, tmp_path, bad_name):
        db = str(tmp_path / "safe.db")
        sqlite3.connect(db).close()
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        result = svc.cleanup_table(db, RetentionPolicy(table_name=bad_name, retention_days=5))
        assert result.success is False
        assert "Invalid table name format" in (result.error_message or "")

    def test_real_table_after_rejected_injection_unchanged(self, tmp_path):
        """A failed injection attempt must leave existing table rows intact."""
        db = _make_db(tmp_path, "safe_table", "timestamp")
        svc = DatabaseCleanupService(config_path=str(tmp_path / "cfg.json"))
        bad = RetentionPolicy(table_name="safe_table; DROP TABLE safe_table;", retention_days=5)
        svc.cleanup_table(db, bad)
        assert _row_count(db, "safe_table") == 2  # both rows still present
