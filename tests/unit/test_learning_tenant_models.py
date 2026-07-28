"""Unit tests for LearningType/DifficultyLevel/ProgressStatus/TenantStatus/SubscriptionTier enums
and LearningOutcome/LearningPath/LearningProgress/Tenant model methods."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.learning import (
    DifficultyLevel,
    LearningOutcome,
    LearningPath,
    LearningProgress,
    LearningType,
    ProgressStatus,
)
from youtube_extension.backend.models.tenant import (
    SubscriptionTier,
    Tenant,
    TenantStatus,
)


def _ns(**attrs) -> SimpleNamespace:
    return SimpleNamespace(**attrs)


# ===========================================================================
# LearningType enum
# ===========================================================================


class TestLearningTypeEnum:
    def test_concept_value(self):
        assert LearningType.CONCEPT.value == "concept"

    def test_skill_value(self):
        assert LearningType.SKILL.value == "skill"

    def test_process_value(self):
        assert LearningType.PROCESS.value == "process"

    def test_tool_value(self):
        assert LearningType.TOOL.value == "tool"

    def test_framework_value(self):
        assert LearningType.FRAMEWORK.value == "framework"

    def test_best_practice_value(self):
        assert LearningType.BEST_PRACTICE.value == "best_practice"

    def test_has_six_members(self):
        assert len(LearningType) == 6


# ===========================================================================
# DifficultyLevel enum
# ===========================================================================


class TestDifficultyLevelEnum:
    def test_beginner_value(self):
        assert DifficultyLevel.BEGINNER.value == "beginner"

    def test_intermediate_value(self):
        assert DifficultyLevel.INTERMEDIATE.value == "intermediate"

    def test_advanced_value(self):
        assert DifficultyLevel.ADVANCED.value == "advanced"

    def test_expert_value(self):
        assert DifficultyLevel.EXPERT.value == "expert"

    def test_has_four_members(self):
        assert len(DifficultyLevel) == 4


# ===========================================================================
# ProgressStatus enum
# ===========================================================================


class TestProgressStatusEnum:
    def test_not_started_value(self):
        assert ProgressStatus.NOT_STARTED.value == "not_started"

    def test_in_progress_value(self):
        assert ProgressStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_value(self):
        assert ProgressStatus.COMPLETED.value == "completed"

    def test_mastered_value(self):
        assert ProgressStatus.MASTERED.value == "mastered"

    def test_needs_review_value(self):
        assert ProgressStatus.NEEDS_REVIEW.value == "needs_review"

    def test_has_five_members(self):
        assert len(ProgressStatus) == 5


# ===========================================================================
# LearningOutcome.is_practical
# ===========================================================================


class TestLearningOutcomeIsPractical:
    def test_practical_when_has_actionable_steps(self):
        o = _ns(actionable_steps=["step1"], examples=[])
        assert LearningOutcome.is_practical(o) is True

    def test_practical_when_has_examples(self):
        o = _ns(actionable_steps=[], examples=[{"code": "x = 1"}])
        assert LearningOutcome.is_practical(o) is True

    def test_practical_when_both_present(self):
        o = _ns(actionable_steps=["do this"], examples=[{"code": "x"}])
        assert LearningOutcome.is_practical(o) is True

    def test_not_practical_when_both_empty(self):
        o = _ns(actionable_steps=[], examples=[])
        assert LearningOutcome.is_practical(o) is False


# ===========================================================================
# LearningPath.get_outcome_count
# ===========================================================================


class TestLearningPathGetOutcomeCount:
    def test_empty_outcomes_list(self):
        p = _ns(learning_outcomes=[])
        assert LearningPath.get_outcome_count(p) == 0

    def test_none_outcomes_list(self):
        p = _ns(learning_outcomes=None)
        assert LearningPath.get_outcome_count(p) == 0

    def test_count_with_outcomes(self):
        p = _ns(learning_outcomes=["id1", "id2", "id3"])
        assert LearningPath.get_outcome_count(p) == 3


# ===========================================================================
# LearningProgress.add_time_spent
# ===========================================================================


class TestLearningProgressAddTimeSpent:
    def test_increments_time_spent(self):
        prog = _ns(time_spent_minutes=10, last_accessed_at=None)
        LearningProgress.add_time_spent(prog, 30)
        assert prog.time_spent_minutes == 40

    def test_updates_last_accessed_at(self):
        before = datetime.utcnow()
        prog = _ns(time_spent_minutes=0, last_accessed_at=None)
        LearningProgress.add_time_spent(prog, 5)
        assert prog.last_accessed_at >= before

    def test_accumulates_multiple_calls(self):
        prog = _ns(time_spent_minutes=0, last_accessed_at=None)
        LearningProgress.add_time_spent(prog, 10)
        LearningProgress.add_time_spent(prog, 20)
        assert prog.time_spent_minutes == 30


# ===========================================================================
# LearningProgress.mark_completed
# ===========================================================================


class TestLearningProgressMarkCompleted:
    def test_sets_status_completed(self):
        prog = _ns(status=ProgressStatus.IN_PROGRESS, completed_at=None, progress_percentage=50.0)
        LearningProgress.mark_completed(prog)
        assert prog.status == ProgressStatus.COMPLETED

    def test_sets_completed_at(self):
        before = datetime.utcnow()
        prog = _ns(status=ProgressStatus.IN_PROGRESS, completed_at=None, progress_percentage=0.0)
        LearningProgress.mark_completed(prog)
        assert prog.completed_at >= before

    def test_sets_progress_to_100(self):
        prog = _ns(status=ProgressStatus.IN_PROGRESS, completed_at=None, progress_percentage=75.0)
        LearningProgress.mark_completed(prog)
        assert prog.progress_percentage == 100.0


# ===========================================================================
# LearningProgress.add_bookmark
# ===========================================================================


class TestLearningProgressAddBookmark:
    def test_adds_bookmark_to_list(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=120, title="Key concept")
        assert len(prog.bookmarks) == 1

    def test_bookmark_has_timestamp(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=60, title="Intro")
        assert prog.bookmarks[0]["timestamp"] == 60

    def test_bookmark_has_title(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=60, title="Intro section")
        assert prog.bookmarks[0]["title"] == "Intro section"

    def test_bookmark_notes_default_none(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=60, title="Note")
        assert prog.bookmarks[0]["notes"] is None

    def test_bookmark_with_notes(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=60, title="Note", notes="Remember this!")
        assert prog.bookmarks[0]["notes"] == "Remember this!"

    def test_initializes_bookmarks_when_none(self):
        prog = _ns(bookmarks=None)
        LearningProgress.add_bookmark(prog, timestamp=30, title="First")
        assert len(prog.bookmarks) == 1

    def test_multiple_bookmarks_accumulate(self):
        prog = _ns(bookmarks=[])
        LearningProgress.add_bookmark(prog, timestamp=10, title="A")
        LearningProgress.add_bookmark(prog, timestamp=20, title="B")
        assert len(prog.bookmarks) == 2


# ===========================================================================
# TenantStatus enum
# ===========================================================================


class TestTenantStatusEnum:
    def test_active_value(self):
        assert TenantStatus.ACTIVE.value == "active"

    def test_suspended_value(self):
        assert TenantStatus.SUSPENDED.value == "suspended"

    def test_cancelled_value(self):
        assert TenantStatus.CANCELLED.value == "cancelled"

    def test_trial_value(self):
        assert TenantStatus.TRIAL.value == "trial"

    def test_pending_value(self):
        assert TenantStatus.PENDING.value == "pending"

    def test_has_five_members(self):
        assert len(TenantStatus) == 5


# ===========================================================================
# SubscriptionTier enum
# ===========================================================================


class TestSubscriptionTierEnum:
    def test_free_value(self):
        assert SubscriptionTier.FREE.value == "free"

    def test_basic_value(self):
        assert SubscriptionTier.BASIC.value == "basic"

    def test_pro_value(self):
        assert SubscriptionTier.PRO.value == "pro"

    def test_enterprise_value(self):
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"

    def test_has_four_members(self):
        assert len(SubscriptionTier) == 4


# ===========================================================================
# Tenant.is_feature_enabled
# ===========================================================================


class TestTenantIsFeatureEnabled:
    def test_enabled_feature_returns_true(self):
        t = _ns(features_enabled={"ai_analysis": True})
        assert Tenant.is_feature_enabled(t, "ai_analysis") is True

    def test_disabled_feature_returns_false(self):
        t = _ns(features_enabled={"ai_analysis": False})
        assert Tenant.is_feature_enabled(t, "ai_analysis") is False

    def test_missing_feature_returns_false(self):
        t = _ns(features_enabled={})
        assert Tenant.is_feature_enabled(t, "unknown_feature") is False

    def test_truthy_value_is_truthy(self):
        t = _ns(features_enabled={"quota": 100})
        assert Tenant.is_feature_enabled(t, "quota")


# ===========================================================================
# Tenant.enable_feature
# ===========================================================================


class TestTenantEnableFeature:
    def test_enables_feature(self):
        t = _ns(features_enabled={})
        Tenant.enable_feature(t, "bulk_export")
        assert t.features_enabled["bulk_export"] is True

    def test_disables_feature(self):
        t = _ns(features_enabled={"bulk_export": True})
        Tenant.enable_feature(t, "bulk_export", enabled=False)
        assert t.features_enabled["bulk_export"] is False

    def test_initializes_features_when_none(self):
        t = _ns(features_enabled=None)
        Tenant.enable_feature(t, "new_feature")
        assert t.features_enabled == {"new_feature": True}


# ===========================================================================
# Tenant.get_usage_stats
# ===========================================================================


class TestTenantGetUsageStats:
    def test_returns_dict(self):
        t = _ns()
        assert isinstance(Tenant.get_usage_stats(t), dict)

    def test_has_videos_processed(self):
        t = _ns()
        stats = Tenant.get_usage_stats(t)
        assert "videos_processed_this_month" in stats

    def test_has_storage_used(self):
        t = _ns()
        assert "storage_used_gb" in Tenant.get_usage_stats(t)

    def test_has_api_calls(self):
        t = _ns()
        assert "api_calls_this_hour" in Tenant.get_usage_stats(t)

    def test_has_active_users(self):
        t = _ns()
        assert "active_users" in Tenant.get_usage_stats(t)
