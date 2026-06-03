import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from youtube_extension.backend.services.database_cleanup_service import (
    CleanupResult,
    DatabaseCleanupService,
    RetentionPolicy,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE my_table (id INTEGER PRIMARY KEY, timestamp TEXT, data TEXT)"
    )
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    cursor.execute(
        "INSERT INTO my_table (timestamp, data) VALUES (?, ?)", (old_date, "old data")
    )
    new_date = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO my_table (timestamp, data) VALUES (?, ?)", (new_date, "new data")
    )
    conn.commit()
    conn.close()

    yield path

    os.unlink(path)


def test_valid_table_name_cleans_up(temp_db):
    service = DatabaseCleanupService()
    policy = RetentionPolicy(table_name="my_table", retention_days=5)
    result = service.cleanup_table(temp_db, policy)
    assert result.success is True
    assert result.records_deleted == 1


def test_sql_injection_table_name_rejected(temp_db):
    service = DatabaseCleanupService()
    policy = RetentionPolicy(
        table_name="my_table; DROP TABLE my_table;",
        retention_days=5,
    )
    result = service.cleanup_table(temp_db, policy)
    assert result.success is False
    assert "Invalid table name format" in result.error_message


def test_table_intact_after_rejected_injection(temp_db):
    service = DatabaseCleanupService()
    malicious = RetentionPolicy(
        table_name="my_table; DROP TABLE my_table;",
        retention_days=5,
    )
    service.cleanup_table(temp_db, malicious)

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM my_table")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 2
