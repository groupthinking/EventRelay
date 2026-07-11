"""Unit tests for the DB connection-pool env-var sizing helper.

Covers `_parse_pool_size`, which runs at import time and therefore must never
raise on malformed configuration — it should log and fall back to the default.
"""

import pytest

from youtube_extension.backend.services.database_optimizer import _parse_pool_size


class TestParsePoolSize:
    def test_valid_value_is_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_POOL_TEST", "17")
        assert _parse_pool_size("DB_POOL_TEST", 5) == 17

    def test_unset_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DB_POOL_TEST", raising=False)
        assert _parse_pool_size("DB_POOL_TEST", 42) == 42

    def test_non_numeric_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_POOL_TEST", "not-a-number")
        assert _parse_pool_size("DB_POOL_TEST", 5) == 5

    def test_empty_string_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_POOL_TEST", "")
        assert _parse_pool_size("DB_POOL_TEST", 9) == 9

    @pytest.mark.parametrize("bad", ["0", "-3"])
    def test_non_positive_falls_back_to_default(
        self, bad: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_POOL_TEST", bad)
        assert _parse_pool_size("DB_POOL_TEST", 8) == 8

    def test_value_above_ceiling_is_clamped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_POOL_TEST", "1000000")
        assert _parse_pool_size("DB_POOL_TEST", 5, max_allowed=200) == 200

    def test_value_at_ceiling_is_kept(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_POOL_TEST", "200")
        assert _parse_pool_size("DB_POOL_TEST", 5, max_allowed=200) == 200
