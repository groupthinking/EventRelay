"""Focused tests for portable path selection helpers."""

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from utils import path_utils


def test_select_writable_dir_does_not_create_missing_preferred(
    tmp_path: Path,
) -> None:
    preferred = tmp_path / "foreign-home" / "workspace"
    fallback = tmp_path / "runtime" / "workspace"

    selected = path_utils.select_writable_dir(preferred, fallback)

    assert selected == fallback
    assert fallback.is_dir()
    assert not preferred.exists()


def test_select_writable_dir_prefers_directory_that_accepts_files(
    tmp_path: Path,
) -> None:
    preferred = tmp_path / "preferred"
    preferred.mkdir()

    selected = path_utils.select_writable_dir(preferred, tmp_path / "fallback")

    assert selected == preferred
    assert list(preferred.iterdir()) == []


def test_select_writable_dir_falls_back_when_preferred_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferred = tmp_path / "preferred"
    preferred.mkdir()
    fallback = tmp_path / "fallback"
    real_mkstemp = tempfile.mkstemp

    def fake_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        if kwargs.get("dir") == str(preferred):
            raise PermissionError("preferred is read-only")
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(path_utils.tempfile, "mkstemp", fake_mkstemp)

    assert path_utils.select_writable_dir(preferred, fallback) == fallback


def test_select_writable_dir_rejects_unwritable_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback = tmp_path / "fallback"

    def reject_probe(*args: Any, **kwargs: Any) -> tuple[int, str]:
        raise PermissionError("no writable directory")

    monkeypatch.setattr(path_utils.tempfile, "mkstemp", reject_probe)

    with pytest.raises(PermissionError, match="Fallback directory is not writable"):
        path_utils.select_writable_dir(tmp_path / "missing", fallback)


def test_select_readable_file_prefers_openable_regular_file(tmp_path: Path) -> None:
    preferred = tmp_path / "preferred.json"
    preferred.write_text("{}", encoding="utf-8")

    selected = path_utils.select_readable_file(preferred, tmp_path / "fallback.json")

    assert selected == preferred


def test_select_readable_file_falls_back_when_open_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferred = tmp_path / "preferred.json"
    preferred.write_text("{}", encoding="utf-8")
    fallback = tmp_path / "fallback.json"
    real_open = Path.open

    def fake_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == preferred:
            raise PermissionError("preferred is unreadable")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)

    assert path_utils.select_readable_file(preferred, fallback) == fallback


def test_select_readable_file_rejects_directory(tmp_path: Path) -> None:
    preferred = tmp_path / "preferred.json"
    preferred.mkdir()
    fallback = tmp_path / "fallback.json"

    assert path_utils.select_readable_file(preferred, fallback) == fallback
