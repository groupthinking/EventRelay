"""Unit tests for CacheService — cache key, stats, clear, file-based caching."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.services.cache_service import CacheService

_VIDEO_URL = "https://www.youtube.com/watch?v=auJzb1D-fag"
_VIDEO_ID = "auJzb1D-fag"


@pytest.fixture
def cache(tmp_path):
    return CacheService(
        cache_dir=str(tmp_path / "legacy"),
        enhanced_cache_dir=str(tmp_path / "enhanced"),
    )


# ===========================================================================
# Initialization
# ===========================================================================


class TestCacheServiceInit:
    def test_cache_dirs_created(self, tmp_path):
        svc = CacheService(
            cache_dir=str(tmp_path / "legacy"),
            enhanced_cache_dir=str(tmp_path / "enhanced"),
        )
        assert svc.cache_dir.exists()
        assert svc.enhanced_cache_dir.exists()

    def test_cache_dir_stored_as_path(self, tmp_path):
        svc = CacheService(cache_dir=str(tmp_path / "c"), enhanced_cache_dir=str(tmp_path / "e"))
        assert isinstance(svc.cache_dir, Path)
        assert isinstance(svc.enhanced_cache_dir, Path)


# ===========================================================================
# _get_cache_key
# ===========================================================================


class TestGetCacheKey:
    def test_returns_12_char_hex(self, cache):
        key = cache._get_cache_key(_VIDEO_URL)
        assert len(key) == 12
        assert all(c in "0123456789abcdef" for c in key)

    def test_deterministic(self, cache):
        assert cache._get_cache_key(_VIDEO_URL) == cache._get_cache_key(_VIDEO_URL)

    def test_different_urls_different_keys(self, cache):
        k1 = cache._get_cache_key("https://www.youtube.com/watch?v=aaaaaaaaaaa")
        k2 = cache._get_cache_key("https://www.youtube.com/watch?v=bbbbbbbbbbb")
        assert k1 != k2

    def test_matches_sha256_prefix(self, cache):
        expected = hashlib.sha256(_VIDEO_URL.encode()).hexdigest()[:12]
        assert cache._get_cache_key(_VIDEO_URL) == expected


# ===========================================================================
# get_cached_result — miss cases
# ===========================================================================


class TestGetCachedResultMiss:
    def test_returns_none_for_uncached_video(self, cache):
        assert cache.get_cached_result(_VIDEO_URL) is None

    def test_returns_none_for_invalid_url(self, cache):
        assert cache.get_cached_result("https://invalid.com/") is None


# ===========================================================================
# get_cache_statistics — empty cache
# ===========================================================================


class TestGetCacheStatisticsEmpty:
    def test_returns_dict(self, cache):
        stats = cache.get_cache_statistics()
        assert isinstance(stats, dict)

    def test_required_keys_present(self, cache):
        stats = cache.get_cache_statistics()
        assert "total_cached_videos" in stats
        assert "categories" in stats
        assert "total_size_mb" in stats

    def test_empty_cache_zero_videos(self, cache):
        stats = cache.get_cache_statistics()
        assert stats["total_cached_videos"] == 0

    def test_empty_cache_zero_size(self, cache):
        stats = cache.get_cache_statistics()
        assert stats["total_size_mb"] == 0.0

    def test_empty_cache_no_categories(self, cache):
        stats = cache.get_cache_statistics()
        assert stats["categories"] == {}


# ===========================================================================
# get_cache_statistics — populated cache
# ===========================================================================


class TestGetCacheStatisticsPopulated:
    def test_counts_markdown_files(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("# Analysis")
        stats = cache.get_cache_statistics()
        assert stats["total_cached_videos"] >= 1

    def test_category_appears_in_stats(self, cache):
        cat = cache.cache_dir / "coding"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("content")
        stats = cache.get_cache_statistics()
        assert "coding" in stats["categories"]

    def test_category_count_correct(self, cache):
        cat = cache.cache_dir / "coding"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("a")
        (cat / "bbbbbbbbbbb_analysis.md").write_text("b")
        stats = cache.get_cache_statistics()
        assert stats["categories"]["coding"]["count"] == 2


# ===========================================================================
# clear_cache
# ===========================================================================


class TestClearCache:
    def test_clear_all_removes_legacy_contents(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("data")
        cache.clear_cache()
        # After clearing, legacy dir should be empty (recreated)
        assert cache.cache_dir.exists()
        assert len(list(cache.cache_dir.iterdir())) == 0

    def test_clear_specific_video_removes_its_files(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("data")
        (cat / f"{_VIDEO_ID}_metadata.json").write_text("{}")
        cache.clear_cache(_VIDEO_URL)
        assert not (cat / f"{_VIDEO_ID}_analysis.md").exists()
        assert not (cat / f"{_VIDEO_ID}_metadata.json").exists()

    def test_clear_specific_video_preserves_other_videos(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("data")
        (cat / "bbbbbbbbbbb_analysis.md").write_text("other")
        cache.clear_cache(_VIDEO_URL)
        assert (cat / "bbbbbbbbbbb_analysis.md").exists()

    def test_clear_invalid_url_does_not_raise(self, cache):
        cache.clear_cache("https://invalid.com/")  # Should not raise

    def test_clear_all_removes_enhanced_contents(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "vid123_ts_enhanced.md").write_text("enhanced")
        cache.clear_cache()
        # enhanced_cache_dir was deleted by clear_all
        assert not cache.enhanced_cache_dir.exists()

    def test_clear_specific_video_removes_enhanced_files(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / f"{_VIDEO_ID}_ts_enhanced.md").write_text("enhanced")
        cache.clear_cache(_VIDEO_URL)
        assert not (cat / f"{_VIDEO_ID}_ts_enhanced.md").exists()

    def test_clear_specific_video_preserves_unrelated_enhanced_files(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / f"{_VIDEO_ID}_ts_enhanced.md").write_text("target")
        (cat / "other123_ts_enhanced.md").write_text("keep")
        cache.clear_cache(_VIDEO_URL)
        assert (cat / "other123_ts_enhanced.md").exists()


# ===========================================================================
# _get_legacy_cached_result
# ===========================================================================


class TestGetLegacyCachedResult:
    def test_returns_cached_result_when_fresh(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_file = cat / f"{_VIDEO_ID}_analysis.md"
        meta_file = cat / f"{_VIDEO_ID}_metadata.json"
        md_file.write_text("# Analysis content")
        meta_file.write_text('{"title": "Test Video"}')
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert result["video_id"] == _VIDEO_ID
        assert result["video_url"] == _VIDEO_URL
        assert result["cached"] is True
        assert "# Analysis content" in result["markdown_content"]

    def test_returns_none_when_cache_expired(self, cache):
        import os
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_file = cat / f"{_VIDEO_ID}_analysis.md"
        meta_file = cat / f"{_VIDEO_ID}_metadata.json"
        md_file.write_text("old content")
        meta_file.write_text("{}")
        # Set mtime to 25 hours ago
        old_time = time.time() - 90000
        os.utime(md_file, (old_time, old_time))
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is None

    def test_returns_none_when_no_metadata_file(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_file = cat / f"{_VIDEO_ID}_analysis.md"
        md_file.write_text("content")
        # no metadata file
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is None

    def test_returns_none_when_no_files(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is None

    def test_result_includes_save_path(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_file = cat / f"{_VIDEO_ID}_analysis.md"
        meta_file = cat / f"{_VIDEO_ID}_metadata.json"
        md_file.write_text("content")
        meta_file.write_text('{}')
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert str(md_file) == result["save_path"]

    def test_metadata_contents_returned(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_file = cat / f"{_VIDEO_ID}_analysis.md"
        meta_file = cat / f"{_VIDEO_ID}_metadata.json"
        md_file.write_text("content")
        meta_file.write_text('{"duration": 300}')
        result = cache._get_legacy_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert result["metadata"]["duration"] == 300


# ===========================================================================
# _get_enhanced_cached_result
# ===========================================================================


class TestGetEnhancedCachedResult:
    def test_returns_result_when_files_exist(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        md_file = cat / f"{_VIDEO_ID}_ts_enhanced.md"
        meta_file = cat / f"{_VIDEO_ID}_ts_metadata.json"
        md_file.write_text("# Enhanced content")
        meta_file.write_text('{"source": "enhanced"}')
        result = cache._get_enhanced_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert result["cached"] is True
        assert result["video_id"] == _VIDEO_ID

    def test_returns_none_when_no_enhanced_files(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        result = cache._get_enhanced_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is None

    def test_returns_none_when_enhanced_dir_missing(self, tmp_path):
        svc = CacheService(
            cache_dir=str(tmp_path / "legacy"),
            enhanced_cache_dir=str(tmp_path / "enhanced"),
        )
        # Delete the enhanced dir after init
        import shutil
        shutil.rmtree(str(svc.enhanced_cache_dir))
        result = svc._get_enhanced_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is None

    def test_metadata_empty_dict_when_no_metadata_file(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        md_file = cat / f"{_VIDEO_ID}_ts_enhanced.md"
        md_file.write_text("# content")
        result = cache._get_enhanced_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert result["metadata"] == {}

    def test_picks_latest_candidate_when_multiple_files(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        older = cat / f"{_VIDEO_ID}_aaa_enhanced.md"
        newer = cat / f"{_VIDEO_ID}_zzz_enhanced.md"
        older.write_text("old version")
        newer.write_text("new version")
        result = cache._get_enhanced_cached_result(_VIDEO_ID, _VIDEO_URL)
        assert result is not None
        assert result["markdown_content"] == "new version"


# ===========================================================================
# get_cached_result — hit cases (full integration via file system)
# ===========================================================================


class TestGetCachedResultHit:
    def test_finds_legacy_cached_result(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("# data")
        (cat / f"{_VIDEO_ID}_metadata.json").write_text('{}')
        result = cache.get_cached_result(_VIDEO_URL)
        assert result is not None
        assert result["cached"] is True

    def test_falls_back_to_enhanced_when_no_legacy(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / f"{_VIDEO_ID}_ts_enhanced.md").write_text("enhanced data")
        result = cache.get_cached_result(_VIDEO_URL)
        assert result is not None
        assert result["cached"] is True

    def test_prefers_legacy_over_enhanced(self, cache):
        # Populate both
        legacy_cat = cache.cache_dir / "tutorial"
        legacy_cat.mkdir()
        (legacy_cat / f"{_VIDEO_ID}_analysis.md").write_text("legacy data")
        (legacy_cat / f"{_VIDEO_ID}_metadata.json").write_text('{}')
        enhanced_cat = cache.enhanced_cache_dir / "tutorial"
        enhanced_cat.mkdir(parents=True, exist_ok=True)
        (enhanced_cat / f"{_VIDEO_ID}_ts_enhanced.md").write_text("enhanced data")
        result = cache.get_cached_result(_VIDEO_URL)
        assert result is not None
        assert "legacy data" in result["markdown_content"]


# ===========================================================================
# get_cache_statistics — timestamps
# ===========================================================================


class TestGetCacheStatisticsTimestamps:
    def test_oldest_cache_set_when_files_exist(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("data")
        stats = cache.get_cache_statistics()
        assert stats["oldest_cache"] is not None

    def test_newest_cache_set_when_files_exist(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("data")
        stats = cache.get_cache_statistics()
        assert stats["newest_cache"] is not None

    def test_oldest_newest_cache_none_when_empty(self, cache):
        stats = cache.get_cache_statistics()
        assert stats["oldest_cache"] is None
        assert stats["newest_cache"] is None

    def test_category_size_mb_is_float(self, cache):
        cat = cache.cache_dir / "coding"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("a" * 1024)
        stats = cache.get_cache_statistics()
        assert isinstance(stats["categories"]["coding"]["size_mb"], float)

    def test_category_type_is_legacy(self, cache):
        cat = cache.cache_dir / "coding"
        cat.mkdir()
        (cat / "auJzb1D-fag_analysis.md").write_text("content")
        stats = cache.get_cache_statistics()
        assert stats["categories"]["coding"]["type"] == "legacy"


# ===========================================================================
# get_cache_statistics — enhanced stats
# ===========================================================================


class TestGetCacheStatisticsEnhanced:
    def test_enhanced_files_counted(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "vid123_ts_enhanced.md").write_text("enhanced")
        stats = cache.get_cache_statistics()
        assert stats["enhanced_cache_stats"]["total_videos"] >= 1

    def test_enhanced_category_appears_in_main_categories(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "vid123_ts_enhanced.md").write_text("enhanced")
        stats = cache.get_cache_statistics()
        assert "enhanced_tutorial" in stats["categories"]

    def test_enhanced_category_type_is_enhanced(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "vid123_ts_enhanced.md").write_text("enhanced")
        stats = cache.get_cache_statistics()
        assert stats["categories"]["enhanced_tutorial"]["type"] == "enhanced"

    def test_enhanced_videos_added_to_total_count(self, cache):
        cat = cache.enhanced_cache_dir / "tutorial"
        cat.mkdir(parents=True, exist_ok=True)
        (cat / "vid123_ts_enhanced.md").write_text("enhanced")
        (cat / "vid456_ts_enhanced.md").write_text("enhanced2")
        stats = cache.get_cache_statistics()
        assert stats["total_cached_videos"] == 2


# ===========================================================================
# get_video_cache_info
# ===========================================================================


class TestGetVideoCacheInfo:
    def test_returns_none_when_not_cached(self, cache):
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is None

    def test_returns_info_when_cached(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("# Content")
        (cat / f"{_VIDEO_ID}_metadata.json").write_text('{"title": "Test"}')
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert result["video_id"] == _VIDEO_ID
        assert result["cached"] is True

    def test_result_has_required_fields(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("content")
        (cat / f"{_VIDEO_ID}_metadata.json").write_text("{}")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        for key in ("video_id", "markdown_content", "metadata", "cached",
                    "cache_age_hours", "file_size", "last_modified", "cache_type"):
            assert key in result

    def test_cache_type_is_legacy(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("content")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert result["cache_type"] == "legacy"

    def test_frontmatter_stripped(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        md_content = "---\ntitle: Test\n---\n# Real content"
        (cat / f"{_VIDEO_ID}_analysis.md").write_text(md_content)
        (cat / f"{_VIDEO_ID}_metadata.json").write_text("{}")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert result["markdown_content"] == "# Real content"

    def test_cache_age_is_numeric(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("content")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert isinstance(result["cache_age_hours"], float)

    def test_file_size_is_positive(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("some content here")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert result["file_size"] > 0

    def test_metadata_empty_when_no_metadata_file(self, cache):
        cat = cache.cache_dir / "tutorial"
        cat.mkdir()
        (cat / f"{_VIDEO_ID}_analysis.md").write_text("content")
        result = cache.get_video_cache_info(_VIDEO_ID)
        assert result is not None
        assert result["metadata"] == {}


# ===========================================================================
# PermissionError fallback (lines 54-68)
# ===========================================================================


class TestPermissionErrorFallback:
    def test_cache_dir_falls_back_on_permission_error(self, monkeypatch, tmp_path):
        call_count = 0
        original_mkdir = Path.mkdir

        def patched_mkdir(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("no permission")
            return original_mkdir(self, **kwargs)

        monkeypatch.setattr(Path, "mkdir", patched_mkdir)
        svc = CacheService(
            cache_dir=str(tmp_path / "restricted"),
            enhanced_cache_dir=str(tmp_path / "enhanced"),
        )
        # Should have fallen back to /tmp path
        assert "/tmp" in str(svc.cache_dir)

    def test_enhanced_cache_dir_falls_back_on_permission_error(self, monkeypatch, tmp_path):
        call_count = 0
        original_mkdir = Path.mkdir

        def patched_mkdir(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise PermissionError("no permission")
            return original_mkdir(self, **kwargs)

        monkeypatch.setattr(Path, "mkdir", patched_mkdir)
        svc = CacheService(
            cache_dir=str(tmp_path / "legacy"),
            enhanced_cache_dir=str(tmp_path / "restricted"),
        )
        assert "/tmp" in str(svc.enhanced_cache_dir)
