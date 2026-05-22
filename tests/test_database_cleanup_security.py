import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta, timezone
from dataclasses import asdict

from youtube_extension.backend.services.database_cleanup_service import (
    DatabaseCleanupService, RetentionPolicy, CleanupResult
)

@pytest.fixture
def temp_db():
    # Create a temporary sqlite database
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Setup some dummy data
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE my_table (id INTEGER PRIMARY KEY, timestamp TEXT, data TEXT)")

    # Insert old record
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    cursor.execute("INSERT INTO my_table (timestamp, data) VALUES (?, ?)", (old_date, "old data"))

    # Insert new record
    new_date = (datetime.now(timezone.utc)).isoformat()
    cursor.execute("INSERT INTO my_table (timestamp, data) VALUES (?, ?)", (new_date, "new data"))

    conn.commit()
    conn.close()

    yield path

    os.unlink(path)

def test_database_cleanup_sql_injection_prevention(temp_db):
    service = DatabaseCleanupService()

    # Test valid table name
    valid_policy = RetentionPolicy(
        table_name="my_table",
        retention_days=5
    )
    result = service.cleanup_table(temp_db, valid_policy)
    assert result.success is True
    assert result.records_deleted == 1

    # Test invalid table name (SQL injection attempt)
    malicious_policy = RetentionPolicy(
        table_name="my_table; DROP TABLE my_table;",
        retention_days=5
    )
    result_malicious = service.cleanup_table(temp_db, malicious_policy)
    assert result_malicious.success is False
    assert "Invalid table name format" in result_malicious.error_message

    # Verify the table still exists and data is intact (minus the deleted old record)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM my_table")
    count = cursor.fetchone()[0]
    assert count == 1
    conn.close()
