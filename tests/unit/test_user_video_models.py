"""Unit tests for user and video model enums and pure-logic methods."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.user import (
    AuthProvider,
    User,
    UserProfile,
    UserSession,
    UserStatus,
)
from youtube_extension.backend.models.video import (
    ProcessingType,
    Video,
    VideoAnalysis,
    VideoMetadata,
    VideoProcessingJob,
    VideoQuality,
    VideoStatus,
)


def _ns(**attrs) -> SimpleNamespace:
    return SimpleNamespace(**attrs)


# ===========================================================================
# UserStatus enum
# ===========================================================================


class TestUserStatusEnum:
    def test_active_value(self):
        assert UserStatus.ACTIVE.value == "active"

    def test_inactive_value(self):
        assert UserStatus.INACTIVE.value == "inactive"

    def test_suspended_value(self):
        assert UserStatus.SUSPENDED.value == "suspended"

    def test_pending_verification_value(self):
        assert UserStatus.PENDING_VERIFICATION.value == "pending_verification"

    def test_has_four_members(self):
        assert len(UserStatus) == 4


# ===========================================================================
# AuthProvider enum
# ===========================================================================


class TestAuthProviderEnum:
    def test_local_value(self):
        assert AuthProvider.LOCAL.value == "local"

    def test_google_value(self):
        assert AuthProvider.GOOGLE.value == "google"

    def test_github_value(self):
        assert AuthProvider.GITHUB.value == "github"

    def test_microsoft_value(self):
        assert AuthProvider.MICROSOFT.value == "microsoft"

    def test_apple_value(self):
        assert AuthProvider.APPLE.value == "apple"

    def test_has_five_members(self):
        assert len(AuthProvider) == 5


# ===========================================================================
# User.get_full_name
# ===========================================================================


class TestUserGetFullName:
    def test_returns_full_name_when_set(self):
        u = _ns(full_name="Jane Doe", first_name="Jane", last_name="Doe", email="jane@example.com")
        assert User.get_full_name(u) == "Jane Doe"

    def test_first_and_last_when_no_full_name(self):
        u = _ns(full_name=None, first_name="Jane", last_name="Doe", email="jane@example.com")
        assert User.get_full_name(u) == "Jane Doe"

    def test_only_first_name(self):
        u = _ns(full_name=None, first_name="Jane", last_name=None, email="jane@example.com")
        assert User.get_full_name(u) == "Jane"

    def test_only_last_name(self):
        u = _ns(full_name=None, first_name=None, last_name="Doe", email="jane@example.com")
        assert User.get_full_name(u) == "Doe"

    def test_email_fallback_when_no_name(self):
        u = _ns(full_name=None, first_name=None, last_name=None, email="jane.smith@example.com")
        assert User.get_full_name(u) == "jane.smith"

    def test_email_fallback_simple(self):
        u = _ns(full_name=None, first_name=None, last_name=None, email="user@test.org")
        assert User.get_full_name(u) == "user"

    def test_full_name_takes_priority_over_first_last(self):
        u = _ns(full_name="Override Name", first_name="First", last_name="Last", email="x@y.com")
        assert User.get_full_name(u) == "Override Name"


# ===========================================================================
# User.is_active
# ===========================================================================


class TestUserIsActive:
    def test_active_status_returns_true(self):
        u = _ns(status=UserStatus.ACTIVE)
        assert User.is_active(u) is True

    def test_inactive_status_returns_false(self):
        u = _ns(status=UserStatus.INACTIVE)
        assert User.is_active(u) is False

    def test_suspended_returns_false(self):
        u = _ns(status=UserStatus.SUSPENDED)
        assert User.is_active(u) is False

    def test_pending_verification_returns_false(self):
        u = _ns(status=UserStatus.PENDING_VERIFICATION)
        assert User.is_active(u) is False


# ===========================================================================
# User.can_login
# ===========================================================================


class TestUserCanLogin:
    def test_active_can_login(self):
        u = _ns(status=UserStatus.ACTIVE)
        assert User.can_login(u) is True

    def test_pending_verification_can_login(self):
        u = _ns(status=UserStatus.PENDING_VERIFICATION)
        assert User.can_login(u) is True

    def test_inactive_cannot_login(self):
        u = _ns(status=UserStatus.INACTIVE)
        assert User.can_login(u) is False

    def test_suspended_cannot_login(self):
        u = _ns(status=UserStatus.SUSPENDED)
        assert User.can_login(u) is False


# ===========================================================================
# User.update_last_activity
# ===========================================================================


class TestUserUpdateLastActivity:
    def test_sets_last_activity_at(self):
        before = datetime.utcnow()
        u = _ns(last_activity_at=None)
        User.update_last_activity(u)
        assert u.last_activity_at >= before

    def test_updates_existing_timestamp(self):
        old_time = datetime(2020, 1, 1)
        u = _ns(last_activity_at=old_time)
        User.update_last_activity(u)
        assert u.last_activity_at > old_time


# ===========================================================================
# UserProfile.get_skills_by_category
# ===========================================================================


class TestUserProfileGetSkillsByCategory:
    def test_returns_dict(self):
        p = _ns(skills=["Python", "SQL"])
        result = UserProfile.get_skills_by_category(p)
        assert isinstance(result, dict)

    def test_technical_key_present(self):
        p = _ns(skills=["Python"])
        result = UserProfile.get_skills_by_category(p)
        assert "technical" in result

    def test_skills_under_technical(self):
        p = _ns(skills=["Python", "SQL"])
        result = UserProfile.get_skills_by_category(p)
        assert result["technical"] == ["Python", "SQL"]

    def test_none_skills_returns_empty_list(self):
        p = _ns(skills=None)
        result = UserProfile.get_skills_by_category(p)
        assert result["technical"] == []

    def test_empty_skills_returns_empty_list(self):
        p = _ns(skills=[])
        result = UserProfile.get_skills_by_category(p)
        assert result["technical"] == []


# ===========================================================================
# UserProfile.add_interest
# ===========================================================================


class TestUserProfileAddInterest:
    def test_adds_interest_to_list(self):
        p = _ns(interests=[])
        UserProfile.add_interest(p, "Python")
        assert "Python" in p.interests

    def test_does_not_duplicate_existing_interest(self):
        p = _ns(interests=["Python"])
        UserProfile.add_interest(p, "Python")
        assert p.interests.count("Python") == 1

    def test_case_insensitive_dedup(self):
        p = _ns(interests=["python"])
        UserProfile.add_interest(p, "Python")
        assert len(p.interests) == 1

    def test_initializes_when_none(self):
        p = _ns(interests=None)
        UserProfile.add_interest(p, "ML")
        assert p.interests == ["ML"]

    def test_multiple_different_interests_accumulate(self):
        p = _ns(interests=[])
        UserProfile.add_interest(p, "ML")
        UserProfile.add_interest(p, "NLP")
        assert len(p.interests) == 2


# ===========================================================================
# UserSession.is_expired
# ===========================================================================


class TestUserSessionIsExpired:
    def test_past_expires_at_is_expired(self):
        s = _ns(expires_at=datetime.utcnow() - timedelta(hours=1))
        assert UserSession.is_expired(s) is True

    def test_future_expires_at_is_not_expired(self):
        s = _ns(expires_at=datetime.utcnow() + timedelta(hours=1))
        assert UserSession.is_expired(s) is False


# ===========================================================================
# UserSession.extend_session
# ===========================================================================


class TestUserSessionExtendSession:
    def test_sets_expires_at_in_future(self):
        before = datetime.utcnow()
        s = _ns(expires_at=datetime.utcnow(), last_activity_at=None)
        UserSession.extend_session(s)
        assert s.expires_at > before + timedelta(minutes=59)

    def test_custom_minutes(self):
        before = datetime.utcnow()
        s = _ns(expires_at=datetime.utcnow(), last_activity_at=None)
        UserSession.extend_session(s, minutes=120)
        assert s.expires_at > before + timedelta(minutes=119)

    def test_updates_last_activity_at(self):
        before = datetime.utcnow()
        s = _ns(expires_at=datetime.utcnow(), last_activity_at=None)
        UserSession.extend_session(s)
        assert s.last_activity_at >= before


# ===========================================================================
# UserSession.end_session
# ===========================================================================


class TestUserSessionEndSession:
    def test_sets_is_active_false(self):
        s = _ns(is_active=True, ended_at=None)
        UserSession.end_session(s)
        assert s.is_active is False

    def test_sets_ended_at(self):
        before = datetime.utcnow()
        s = _ns(is_active=True, ended_at=None)
        UserSession.end_session(s)
        assert s.ended_at >= before


# ===========================================================================
# VideoStatus enum
# ===========================================================================


class TestVideoStatusEnum:
    def test_pending_value(self):
        assert VideoStatus.PENDING.value == "pending"

    def test_processing_value(self):
        assert VideoStatus.PROCESSING.value == "processing"

    def test_completed_value(self):
        assert VideoStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert VideoStatus.FAILED.value == "failed"

    def test_cancelled_value(self):
        assert VideoStatus.CANCELLED.value == "cancelled"

    def test_has_five_members(self):
        assert len(VideoStatus) == 5


# ===========================================================================
# ProcessingType enum
# ===========================================================================


class TestProcessingTypeEnum:
    def test_transcript_value(self):
        assert ProcessingType.TRANSCRIPT.value == "transcript"

    def test_analysis_value(self):
        assert ProcessingType.ANALYSIS.value == "analysis"

    def test_summary_value(self):
        assert ProcessingType.SUMMARY.value == "summary"

    def test_learning_extraction_value(self):
        assert ProcessingType.LEARNING_EXTRACTION.value == "learning_extraction"

    def test_code_generation_value(self):
        assert ProcessingType.CODE_GENERATION.value == "code_generation"

    def test_full_pipeline_value(self):
        assert ProcessingType.FULL_PIPELINE.value == "full_pipeline"

    def test_has_six_members(self):
        assert len(ProcessingType) == 6


# ===========================================================================
# VideoQuality enum
# ===========================================================================


class TestVideoQualityEnum:
    def test_low_value(self):
        assert VideoQuality.LOW.value == "low"

    def test_medium_value(self):
        assert VideoQuality.MEDIUM.value == "medium"

    def test_high_value(self):
        assert VideoQuality.HIGH.value == "high"

    def test_hd_value(self):
        assert VideoQuality.HD.value == "hd"

    def test_uhd_value(self):
        assert VideoQuality.UHD.value == "uhd"

    def test_has_five_members(self):
        assert len(VideoQuality) == 5


# ===========================================================================
# Video.get_formatted_duration
# ===========================================================================


class TestVideoGetFormattedDuration:
    def test_none_duration_returns_unknown(self):
        v = _ns(duration_seconds=None)
        assert Video.get_formatted_duration(v) == "Unknown"

    def test_zero_duration_returns_unknown(self):
        v = _ns(duration_seconds=0)
        assert Video.get_formatted_duration(v) == "Unknown"

    def test_under_one_minute(self):
        v = _ns(duration_seconds=45)
        assert Video.get_formatted_duration(v) == "0:45"

    def test_exactly_one_minute(self):
        v = _ns(duration_seconds=60)
        assert Video.get_formatted_duration(v) == "1:00"

    def test_minutes_and_seconds(self):
        v = _ns(duration_seconds=90)
        assert Video.get_formatted_duration(v) == "1:30"

    def test_leading_zero_on_seconds(self):
        v = _ns(duration_seconds=65)
        assert Video.get_formatted_duration(v) == "1:05"

    def test_hours_minutes_seconds(self):
        v = _ns(duration_seconds=3661)
        assert Video.get_formatted_duration(v) == "1:01:01"

    def test_exactly_one_hour(self):
        v = _ns(duration_seconds=3600)
        assert Video.get_formatted_duration(v) == "1:00:00"

    def test_two_hours_plus(self):
        v = _ns(duration_seconds=7322)
        assert Video.get_formatted_duration(v) == "2:02:02"


# ===========================================================================
# Video.is_long_form
# ===========================================================================


class TestVideoIsLongForm:
    def test_none_duration_is_not_long_form(self):
        v = _ns(duration_seconds=None)
        assert not Video.is_long_form(v)

    def test_short_video_not_long_form(self):
        v = _ns(duration_seconds=300)
        assert not Video.is_long_form(v)

    def test_exactly_10_minutes_not_long_form(self):
        v = _ns(duration_seconds=600)
        assert not Video.is_long_form(v)

    def test_over_10_minutes_is_long_form(self):
        v = _ns(duration_seconds=601)
        assert Video.is_long_form(v)

    def test_one_hour_is_long_form(self):
        v = _ns(duration_seconds=3600)
        assert Video.is_long_form(v)


# ===========================================================================
# Video.get_engagement_rate
# ===========================================================================


class TestVideoGetEngagementRate:
    def test_no_view_count_returns_zero(self):
        v = _ns(view_count=None, like_count=100)
        assert Video.get_engagement_rate(v) == 0.0

    def test_zero_view_count_returns_zero(self):
        v = _ns(view_count=0, like_count=100)
        assert Video.get_engagement_rate(v) == 0.0

    def test_calculates_engagement_rate(self):
        v = _ns(view_count=1000, like_count=100)
        assert abs(Video.get_engagement_rate(v) - 10.0) < 1e-9

    def test_none_likes_counts_as_zero(self):
        v = _ns(view_count=1000, like_count=None)
        assert Video.get_engagement_rate(v) == 0.0

    def test_100_percent_engagement(self):
        v = _ns(view_count=100, like_count=100)
        assert abs(Video.get_engagement_rate(v) - 100.0) < 1e-9

    def test_fractional_rate(self):
        v = _ns(view_count=3, like_count=1)
        expected = (1 / 3) * 100
        assert abs(Video.get_engagement_rate(v) - expected) < 1e-6


# ===========================================================================
# VideoMetadata.get_word_count
# ===========================================================================


class TestVideoMetadataGetWordCount:
    def test_none_content_returns_zero(self):
        m = _ns(content=None)
        assert VideoMetadata.get_word_count(m) == 0

    def test_empty_string_returns_zero(self):
        m = _ns(content="")
        assert VideoMetadata.get_word_count(m) == 0

    def test_single_word(self):
        m = _ns(content="hello")
        assert VideoMetadata.get_word_count(m) == 1

    def test_multiple_words(self):
        m = _ns(content="hello world foo bar")
        assert VideoMetadata.get_word_count(m) == 4

    def test_extra_spaces_ignored(self):
        m = _ns(content="hello  world")
        assert VideoMetadata.get_word_count(m) == 2


# ===========================================================================
# VideoMetadata.get_transcript_segments
# ===========================================================================


class TestVideoMetadataGetTranscriptSegments:
    def test_non_transcript_type_returns_empty(self):
        m = _ns(metadata_type="captions", structured_data={"segments": [{"t": 0}]})
        assert VideoMetadata.get_transcript_segments(m) == []

    def test_no_structured_data_returns_empty(self):
        m = _ns(metadata_type="transcript", structured_data=None)
        assert VideoMetadata.get_transcript_segments(m) == []

    def test_empty_structured_data_returns_empty(self):
        m = _ns(metadata_type="transcript", structured_data={})
        assert VideoMetadata.get_transcript_segments(m) == []

    def test_returns_segments(self):
        segs = [{"start": 0, "text": "Hello"}, {"start": 5, "text": "World"}]
        m = _ns(metadata_type="transcript", structured_data={"segments": segs})
        assert VideoMetadata.get_transcript_segments(m) == segs

    def test_returns_empty_segments_list(self):
        m = _ns(metadata_type="transcript", structured_data={"segments": []})
        assert VideoMetadata.get_transcript_segments(m) == []


# ===========================================================================
# VideoAnalysis.get_topic_frequency
# ===========================================================================


class TestVideoAnalysisGetTopicFrequency:
    def test_none_topics_returns_empty_dict(self):
        a = _ns(topics=None)
        assert VideoAnalysis.get_topic_frequency(a) == {}

    def test_empty_topics_returns_empty_dict(self):
        a = _ns(topics=[])
        assert VideoAnalysis.get_topic_frequency(a) == {}

    def test_topics_each_get_count_one(self):
        a = _ns(topics=["Python", "AI", "ML"])
        result = VideoAnalysis.get_topic_frequency(a)
        assert result == {"Python": 1, "AI": 1, "ML": 1}

    def test_single_topic(self):
        a = _ns(topics=["Python"])
        assert VideoAnalysis.get_topic_frequency(a) == {"Python": 1}


# ===========================================================================
# VideoAnalysis.get_readability_score
# ===========================================================================


class TestVideoAnalysisGetReadabilityScore:
    def test_none_summary_returns_none(self):
        a = _ns(summary=None)
        assert VideoAnalysis.get_readability_score(a) is None

    def test_empty_summary_returns_none(self):
        a = _ns(summary="")
        assert VideoAnalysis.get_readability_score(a) is None

    def test_returns_float(self):
        a = _ns(summary="Hello world. This is a test.")
        score = VideoAnalysis.get_readability_score(a)
        assert isinstance(score, float)

    def test_score_between_0_and_100(self):
        a = _ns(summary="One. " * 50)
        score = VideoAnalysis.get_readability_score(a)
        assert 0.0 <= score <= 100.0

    def test_optimal_sentence_length_scores_high(self):
        # ~17-18 words per sentence gets near-optimal score
        sentence = "word " * 17 + "end."
        summary = sentence * 3
        a = _ns(summary=summary)
        score = VideoAnalysis.get_readability_score(a)
        assert score >= 90.0


# ===========================================================================
# VideoProcessingJob.get_duration_seconds
# ===========================================================================


class TestVideoProcessingJobGetDurationSeconds:
    def test_no_started_at_returns_none(self):
        j = _ns(started_at=None, completed_at=datetime.utcnow())
        assert VideoProcessingJob.get_duration_seconds(j) is None

    def test_no_completed_at_returns_none(self):
        j = _ns(started_at=datetime.utcnow(), completed_at=None)
        assert VideoProcessingJob.get_duration_seconds(j) is None

    def test_both_none_returns_none(self):
        j = _ns(started_at=None, completed_at=None)
        assert VideoProcessingJob.get_duration_seconds(j) is None

    def test_calculates_duration(self):
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 1, 30)
        j = _ns(started_at=start, completed_at=end)
        assert VideoProcessingJob.get_duration_seconds(j) == 90

    def test_returns_int(self):
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 45)
        j = _ns(started_at=start, completed_at=end)
        assert isinstance(VideoProcessingJob.get_duration_seconds(j), int)


# ===========================================================================
# VideoProcessingJob.can_retry
# ===========================================================================


class TestVideoProcessingJobCanRetry:
    def test_failed_with_retries_remaining(self):
        j = _ns(status=VideoStatus.FAILED, retry_count=1, max_retries=3)
        assert VideoProcessingJob.can_retry(j) is True

    def test_failed_no_retries_remaining(self):
        j = _ns(status=VideoStatus.FAILED, retry_count=3, max_retries=3)
        assert VideoProcessingJob.can_retry(j) is False

    def test_failed_retries_exceeded(self):
        j = _ns(status=VideoStatus.FAILED, retry_count=5, max_retries=3)
        assert VideoProcessingJob.can_retry(j) is False

    def test_not_failed_returns_false(self):
        j = _ns(status=VideoStatus.PROCESSING, retry_count=0, max_retries=3)
        assert VideoProcessingJob.can_retry(j) is False

    def test_completed_cannot_retry(self):
        j = _ns(status=VideoStatus.COMPLETED, retry_count=0, max_retries=3)
        assert VideoProcessingJob.can_retry(j) is False

    def test_zero_max_retries(self):
        j = _ns(status=VideoStatus.FAILED, retry_count=0, max_retries=0)
        assert VideoProcessingJob.can_retry(j) is False


# ===========================================================================
# VideoProcessingJob.is_stuck
# ===========================================================================


class TestVideoProcessingJobIsStuck:
    def test_no_started_at_not_stuck(self):
        j = _ns(started_at=None, status=VideoStatus.PROCESSING)
        assert VideoProcessingJob.is_stuck(j) is False

    def test_not_processing_not_stuck(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(hours=5), status=VideoStatus.COMPLETED)
        assert VideoProcessingJob.is_stuck(j) is False

    def test_failed_not_stuck(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(hours=5), status=VideoStatus.FAILED)
        assert VideoProcessingJob.is_stuck(j) is False

    def test_processing_recent_not_stuck(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(hours=1), status=VideoStatus.PROCESSING)
        assert VideoProcessingJob.is_stuck(j) is False

    def test_processing_old_is_stuck(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(hours=3), status=VideoStatus.PROCESSING)
        assert VideoProcessingJob.is_stuck(j) is True

    def test_custom_timeout(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(hours=2), status=VideoStatus.PROCESSING)
        assert VideoProcessingJob.is_stuck(j, timeout_hours=1) is True

    def test_custom_timeout_not_exceeded(self):
        j = _ns(started_at=datetime.utcnow() - timedelta(minutes=30), status=VideoStatus.PROCESSING)
        assert VideoProcessingJob.is_stuck(j, timeout_hours=2) is False
