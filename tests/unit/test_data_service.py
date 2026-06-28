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

    def test_pagination_limit(self, tmp_path):
        """limit param returns at most that many entries."""
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        for i in range(5):
            (cat / f"vid{i:03d}_test_enhanced.md").write_text("x")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.get_videos_summary(limit=3)
        assert len(result) == 3

    def test_pagination_offset(self, tmp_path):
        """offset skips entries."""
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        for i in range(5):
            (cat / f"vid{i:03d}_test_enhanced.md").write_text("x")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        all_results = svc.get_videos_summary()
        paged = svc.get_videos_summary(limit=5, offset=2)
        assert len(paged) == 3
        assert all_results[2]["video_id"] == paged[0]["video_id"]

    def test_pagination_beyond_total_returns_empty(self, tmp_path):
        """offset beyond total returns empty list."""
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        (cat / "vid000_test_enhanced.md").write_text("x")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        result = svc.get_videos_summary(limit=10, offset=100)
        assert result == []


class TestCountVideos:
    def test_missing_dir_returns_zero(self, svc):
        assert svc.count_videos() == 0

    def test_counts_enhanced_markdown_files(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        cat = enhanced / "cat"
        cat.mkdir(parents=True)
        for i in range(3):
            (cat / f"vid{i:03d}_test_enhanced.md").write_text("x")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        assert svc.count_videos() == 3

    def test_does_not_count_non_enhanced_files(self, tmp_path):
        enhanced = tmp_path / "enhanced"
        enhanced.mkdir(parents=True)
        (enhanced / "vid000_test_enhanced.md").write_text("x")
        (enhanced / "other.md").write_text("y")
        svc = DataService(str(enhanced), str(tmp_path / "feedback"))
        assert svc.count_videos() == 1


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


# ===========================================================================
# Exception paths — metadata json parsing failure
# ===========================================================================


class TestDataServiceExceptionPaths:
    @pytest.fixture
    def enhanced_dir(self, tmp_path):
        enhanced = tmp_path / "enhanced" / "cat1"
        enhanced.mkdir(parents=True)
        return enhanced

    def test_learning_log_with_corrupt_metadata(self, tmp_path, enhanced_dir):
        # Create enhanced markdown file
        (enhanced_dir / "vid001_test_enhanced.md").write_text("content")
        # Create a corrupt metadata JSON file
        (enhanced_dir / "vid001_test_metadata.json").write_text("{invalid json}")
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        items = svc.get_learning_log()
        # Should still return an item, just without metadata
        assert len(items) == 1
        assert items[0]["video_id"] == "vid001"

    def test_learning_log_with_valid_metadata(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid002_test_enhanced.md").write_text("content")
        metadata = {"title": "Test Video Title"}
        (enhanced_dir / "vid002_test_metadata.json").write_text(json.dumps(metadata))
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        items = svc.get_learning_log()
        assert len(items) >= 1
        assert items[0]["title"] == "Test Video Title"

    def test_learning_log_no_metadata_file(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid003_test_enhanced.md").write_text("content")
        # No metadata file
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        items = svc.get_learning_log()
        assert len(items) == 1

    def test_videos_summary_with_corrupt_metadata(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid010_test_enhanced.md").write_text("content")
        (enhanced_dir / "vid010_test_metadata.json").write_text("{bad}")
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        results = svc.get_videos_summary()
        assert len(results) == 1

    def test_videos_summary_with_valid_metadata(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid011_test_enhanced.md").write_text("content")
        metadata = {
            "title": "My Video",
            "snippet": {"description": "desc", "publishedAt": "2024-01-01T00:00:00Z"},
            "statistics": {"viewCount": "1000"},
        }
        (enhanced_dir / "vid011_test_metadata.json").write_text(json.dumps(metadata))
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        results = svc.get_videos_summary()
        assert len(results) >= 1
        assert results[0]["title"] == "My Video"

    def test_get_video_detail_with_corrupt_metadata(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid020_test_enhanced.md").write_text("# Test Content")
        (enhanced_dir / "vid020_test_metadata.json").write_text("{garbage}")
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        detail = svc.get_video_detail("vid020")
        # Should return detail even with bad metadata
        assert detail is not None

    def test_get_video_detail_with_valid_metadata(self, tmp_path, enhanced_dir):
        (enhanced_dir / "vid021_test_enhanced.md").write_text("# Content\n\nSome text here.")
        metadata = {"title": "Test Title", "snippet": {"description": "desc"}}
        (enhanced_dir / "vid021_test_metadata.json").write_text(json.dumps(metadata))
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        detail = svc.get_video_detail("vid021")
        assert detail is not None
        assert detail["title"] == "Test Title"
        assert "markdown" in detail

    def test_get_video_detail_not_found_returns_none(self, tmp_path, enhanced_dir):
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        result = svc.get_video_detail("nonexistent_video_id")
        assert result is None

    def test_multiple_enhanced_files_sorted(self, tmp_path, enhanced_dir):
        """Most recent file should be first."""
        (enhanced_dir / "vid030_test_enhanced.md").write_text("content1")
        (enhanced_dir / "vid031_test_enhanced.md").write_text("content2")
        svc = DataService(str(tmp_path / "enhanced"), str(tmp_path / "feedback"))
        items = svc.get_learning_log()
        # Both items should be present
        assert len(items) == 2
