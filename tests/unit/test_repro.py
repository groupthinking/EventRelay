"""Unit tests for youtube_extension.utils.repro — repro ID resolution."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.utils.repro import attach_repro_id_to_payload, get_repro_id


class TestGetReproId:
    def test_returns_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "test-repro-123")
        assert get_repro_id() == "test-repro-123"

    def test_env_var_stripped(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "  spaced  ")
        assert get_repro_id() == "spaced"

    def test_returns_default_when_no_env(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        assert get_repro_id(default="my-default") == "my-default"

    def test_returns_uuid4_when_no_env_no_default(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = get_repro_id()
        uuid.UUID(result)  # Raises ValueError if not a valid UUID

    def test_uuid_is_unique_per_call(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        assert get_repro_id() != get_repro_id()

    def test_env_var_takes_precedence_over_default(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "env-wins")
        assert get_repro_id(default="default-loses") == "env-wins"

    def test_blank_env_var_falls_through_to_default(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "   ")
        assert get_repro_id(default="fallback") == "fallback"

    def test_blank_default_falls_through_to_uuid(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = get_repro_id(default="  ")
        uuid.UUID(result)


class TestAttachReproIdToPayload:
    def test_adds_repro_id_key(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "fixed-id")
        result = attach_repro_id_to_payload({"a": 1})
        assert result["repro-id"] == "fixed-id"

    def test_original_payload_preserved(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "fixed-id")
        result = attach_repro_id_to_payload({"key": "value"})
        assert result["key"] == "value"

    def test_does_not_mutate_input(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "fixed-id")
        payload = {"original": True}
        attach_repro_id_to_payload(payload)
        assert "repro-id" not in payload

    def test_explicit_repro_id_used(self, monkeypatch):
        monkeypatch.delenv("REPRO_ID", raising=False)
        result = attach_repro_id_to_payload({}, repro_id="explicit-id")
        assert result["repro-id"] == "explicit-id"

    def test_empty_payload(self, monkeypatch):
        monkeypatch.setenv("REPRO_ID", "id")
        result = attach_repro_id_to_payload({})
        assert result == {"repro-id": "id"}
