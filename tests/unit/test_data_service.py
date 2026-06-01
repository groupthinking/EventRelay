"""Unit tests for DataService — file-based data operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.data_service import DataService


@pytest.fixture
def svc(tmp_path):
    return DataService(
        enhanced_analysis_dir=str(tmp_path / "enhanced"),
        feedback_dir=str(tmp_path / "feedback"),
    )


# ===========================================================================
# Initialization
# ===========================================================================


class TestDataServiceInit:
    def test_feedback_dir_created(self, tmp_path):
        svc = DataService(
            enhanced_analysis_dir=str(tmp_path / "enhanced"),
            feedback_dir=str(tmp_path / "feedback"),
        )
        assert (tmp_path / "feedback").exists()

    def test_paths_stored_as_path_objects(self, tmp_path):
        svc = DataService(
            enhanced_analysis_dir=str(tmp_path / "enhanced"),
            feedback_dir=str(tmp_path / "feedback"),
        )
        assert isinstance(svc.enhanced_analysis_dir, Path)
        assert isinstance(svc.feedback_dir, Path)


# ===========================================================================
# get_learning_log
# ===========================================================================


class TestGetLearningLog:
    def test_missing_dir_returns_empty_list(self, svc):
        assert svc.get_learning_log() == []

    def test_returns_list(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        enhanced.mkdir()
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.get_learning_log()
        assert isinstance(result, list)

    def test_returns_entry_for_enhanced_file(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "coding"
        cat.mkdir(parents=True)
        (cat / "abc123_title_enhanced.md").write_text("# Analysis")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.get_learning_log()
        assert len(result) == 1
        assert result[0]["video_id"] == "abc123"

    def test_entry_has_required_keys(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "tutorial"
        cat.mkdir(parents=True)
        (cat / "vid001_test_enhanced.md").write_text("content")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        entry = svc.get_learning_log()[0]
        for key in ("video_id", "category", "title", "timestamp"):
            assert key in entry

    def test_uses_metadata_title_when_available(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "tech"
        cat.mkdir(parents=True)
        (cat / "vid002_test_enhanced.md").write_text("body")
        (cat / "vid002_test_metadata.json").write_text(
            json.dumps({"title": "My Custom Title"})
        )
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        entry = svc.get_learning_log()[0]
        assert entry["title"] == "My Custom Title"

    def test_falls_back_to_video_id_title(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "tech"
        cat.mkdir(parents=True)
        (cat / "vid003_test_enhanced.md").write_text("body")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        entry = svc.get_learning_log()[0]
        assert "vid003" in entry["title"]

    def test_sorted_newest_first(self, tmp_path):
        import time
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        f1 = cat / "old001_test_enhanced.md"
        f1.write_text("old")
        time.sleep(0.05)
        f2 = cat / "new002_test_enhanced.md"
        f2.write_text("new")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.get_learning_log()
        assert result[0]["video_id"] == "new002"


# ===========================================================================
# get_videos_summary
# ===========================================================================


class TestGetVideosSummary:
    def test_missing_dir_returns_empty(self, svc):
        assert svc.get_videos_summary() == []

    def test_returns_entry_for_each_enhanced_file(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "science"
        cat.mkdir(parents=True)
        (cat / "vid010_test_enhanced.md").write_text("a")
        (cat / "vid011_test_enhanced.md").write_text("b")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        assert len(svc.get_videos_summary()) == 2

    def test_entry_has_markdown_path(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        (cat / "vid020_test_enhanced.md").write_text("x")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        entry = svc.get_videos_summary()[0]
        assert "markdown_path" in entry
        assert entry["markdown_path"].endswith(".md")


# ===========================================================================
# get_video_detail
# ===========================================================================


class TestGetVideoDetail:
    def test_missing_dir_returns_none(self, svc):
        assert svc.get_video_detail("doesnotexist") is None

    def test_unknown_video_returns_none(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        enhanced.mkdir()
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        assert svc.get_video_detail("xyz") is None

    def test_returns_detail_for_existing_video(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        (cat / "vid030_title_enhanced.md").write_text("# My Video")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        detail = svc.get_video_detail("vid030")
        assert detail is not None
        assert detail["video_id"] == "vid030"
        assert "markdown" in detail

    def test_markdown_content_returned(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        (cat / "vid031_title_enhanced.md").write_text("# Hello World")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        detail = svc.get_video_detail("vid031")
        assert "Hello World" in detail["markdown"]


# ===========================================================================
# save_feedback / get_feedback_summary
# ===========================================================================


class TestFeedback:
    def test_save_feedback_returns_true(self, svc):
        assert svc.save_feedback({"id": "fb-1", "rating": 5}) is True

    def test_save_creates_jsonl_file(self, tmp_path):
        svc = DataService(
            str(tmp_path / "enhanced"),
            str(tmp_path / "feedback"),
        )
        svc.save_feedback({"id": "fb-1"})
        assert (tmp_path / "feedback" / "feedback.jsonl").exists()

    def test_get_feedback_empty_returns_empty(self, svc):
        assert svc.get_feedback_summary() == []

    def test_get_feedback_returns_saved_entry(self, svc):
        svc.save_feedback({"id": "fb-1", "note": "good"})
        entries = svc.get_feedback_summary()
        assert len(entries) == 1
        assert entries[0]["id"] == "fb-1"

    def test_feedback_has_timestamp(self, svc):
        svc.save_feedback({"id": "fb-2"})
        entry = svc.get_feedback_summary()[0]
        assert "timestamp" in entry

    def test_multiple_feedbacks_returned(self, svc):
        svc.save_feedback({"id": "a"})
        svc.save_feedback({"id": "b"})
        svc.save_feedback({"id": "c"})
        assert len(svc.get_feedback_summary()) == 3

    def test_limit_respected(self, svc):
        for i in range(10):
            svc.save_feedback({"id": str(i)})
        assert len(svc.get_feedback_summary(limit=3)) == 3


# ===========================================================================
# get_data_statistics
# ===========================================================================


class TestGetDataStatistics:
    def test_missing_dir_returns_zero_counts(self, svc):
        stats = svc.get_data_statistics()
        assert stats["enhanced_videos"] == 0
        assert stats["feedback_entries"] == 0

    def test_required_keys_present(self, svc):
        stats = svc.get_data_statistics()
        for key in ("enhanced_videos", "categories", "feedback_entries", "total_storage_mb"):
            assert key in stats

    def test_counts_enhanced_files(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "finance"
        cat.mkdir(parents=True)
        (cat / "vid100_test_enhanced.md").write_text("x")
        (cat / "vid101_test_enhanced.md").write_text("y")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        stats = svc.get_data_statistics()
        assert stats["enhanced_videos"] == 2
        assert "finance" in stats["categories"]

    def test_counts_feedback_entries(self, tmp_path):
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        svc.save_feedback({"id": "1"})
        svc.save_feedback({"id": "2"})
        stats = svc.get_data_statistics()
        assert stats["feedback_entries"] == 2
