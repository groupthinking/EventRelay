import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from youtube_extension.backend.services.database_cleanup_service import (
    CleanupResult,
    DatabaseCleanupService,
    RetentionPolicy,
    _ALLOWED_TIME_COLUMNS,
    _TABLE_NAME_RE,
    _validate_identifier,
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


# ===========================================================================
# _validate_identifier — unit tests
# ===========================================================================


class TestValidateIdentifier:
    """Tests for the _validate_identifier security function."""

    def test_valid_simple_name(self):
        assert _validate_identifier("metrics") == '"metrics"'

    def test_valid_underscore_prefix(self):
        assert _validate_identifier("_internal") == '"_internal"'

    def test_valid_mixed_case(self):
        assert _validate_identifier("ApiUsage") == '"ApiUsage"'

    def test_valid_with_numbers(self):
        assert _validate_identifier("table_v2") == '"table_v2"'

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("")

    def test_rejects_semicolon(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("table; DROP TABLE users")

    def test_rejects_dash(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("my-table")

    def test_rejects_space(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("my table")

    def test_rejects_quotes(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier('table"name')

    def test_rejects_starts_with_number(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("0_invalid")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("a" * 129)

    def test_accepts_max_length(self):
        name = "a" * 128
        assert _validate_identifier(name) == f'"{name}"'

    def test_rejects_sql_comment(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("table--comment")

    def test_rejects_backtick(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("`table`")

    def test_rejects_parentheses(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("table()")

    def test_rejects_newline(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("table\nname")


# ===========================================================================
# SQL injection attack vectors — regression tests
# ===========================================================================


class TestSQLInjectionVectors:
    """Ensure various SQL injection attack patterns are all rejected."""

    @pytest.fixture
    def service(self):
        return DatabaseCleanupService()

    @pytest.fixture
    def db_with_data(self, tmp_path):
        db_path = str(tmp_path / "target.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, timestamp TEXT)"
        )
        ts = datetime.now(timezone.utc).isoformat()
        conn.execute("INSERT INTO users (name, timestamp) VALUES (?, ?)", ("alice", ts))
        conn.commit()
        conn.close()
        return db_path

    @pytest.mark.parametrize(
        "malicious_name",
        [
            "users; DROP TABLE users;--",
            "users UNION SELECT * FROM sqlite_master--",
            "users; INSERT INTO users VALUES(99,'hacked','now');--",
            "users WHERE 1=1;--",
            "users\"; DROP TABLE users;--",
            "users' OR '1'='1",
            "users/**/UNION/**/SELECT/**/1,2,3--",
        ],
    )
    def test_injection_in_table_name_rejected(
        self, service, db_with_data, malicious_name
    ):
        policy = RetentionPolicy(table_name=malicious_name, retention_days=1)
        result = service.cleanup_table(db_with_data, policy)
        assert result.success is False
        assert "Invalid table name" in result.error_message

    @pytest.mark.parametrize(
        "malicious_name",
        [
            "users; DROP TABLE users;--",
            "users UNION SELECT * FROM sqlite_master--",
            "users; INSERT INTO users VALUES(99,'hacked','now');--",
        ],
    )
    def test_data_intact_after_injection_attempt(
        self, service, db_with_data, malicious_name
    ):
        policy = RetentionPolicy(table_name=malicious_name, retention_days=1)
        service.cleanup_table(db_with_data, policy)

        # Verify data is untouched
        conn = sqlite3.connect(db_with_data)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1


# ===========================================================================
# Allowed time columns allowlist tests
# ===========================================================================


class TestAllowedTimeColumns:
    """Verify the time column allowlist is correctly enforced."""

    def test_allowlist_is_frozenset(self):
        assert isinstance(_ALLOWED_TIME_COLUMNS, frozenset)

    def test_expected_columns_present(self):
        assert "timestamp" in _ALLOWED_TIME_COLUMNS
        assert "created_at" in _ALLOWED_TIME_COLUMNS
        assert "createdAt" in _ALLOWED_TIME_COLUMNS
        assert "ts" in _ALLOWED_TIME_COLUMNS

    def test_arbitrary_column_not_in_allowlist(self):
        assert "user_input" not in _ALLOWED_TIME_COLUMNS
        assert "DROP TABLE" not in _ALLOWED_TIME_COLUMNS

    def test_all_allowlisted_columns_pass_identifier_validation(self):
        for col in _ALLOWED_TIME_COLUMNS:
            # Should not raise
            result = _validate_identifier(col)
            assert result == f'"{col}"'


# ===========================================================================
# Table name regex tests
# ===========================================================================


class TestTableNameRegex:
    """Verify the _TABLE_NAME_RE regex catches all dangerous patterns."""

    def test_rejects_empty(self):
        assert not _TABLE_NAME_RE.match("")

    def test_accepts_simple_alpha(self):
        assert _TABLE_NAME_RE.match("metrics")

    def test_accepts_underscore_start(self):
        assert _TABLE_NAME_RE.match("_private")

    def test_rejects_number_start(self):
        assert not _TABLE_NAME_RE.match("123table")

    def test_rejects_special_chars(self):
        for char in [";", " ", "-", "'", '"', "(", ")", ".", ",", "/", "\\"]:
            assert not _TABLE_NAME_RE.match(f"table{char}name")

