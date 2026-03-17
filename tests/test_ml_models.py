"""Tests for UVAI ML models.

Validates models locally before Ray deployment.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "src"),
)

from uvai.ml.models.action_priority_ranker import (  # noqa: E402
    ActionPriorityRanker,
)
from uvai.ml.models.transcript_quality_scorer import (  # noqa: E402
    TranscriptQualityScorer,
)


def test_transcript_quality_scorer_basic() -> None:
    """Test that scorer produces a valid prediction."""

    scorer = TranscriptQualityScorer()

    # Video with captions in English
    metadata = {
        "title": "How to Build a SaaS Platform",
        "duration_seconds": 600,
        "has_captions": True,
        "language": "en",
        "subscriber_count": 50_000,
        "view_count": 100_000,
        "category": "Education",
    }

    prediction = scorer.predict(metadata)

    assert 0.0 <= prediction.quality_score <= 1.0
    assert prediction.recommended_source in {
        "youtube_api", "speech_v2", "gemini_video", "gemini_video_file",
    }
    assert 0.0 <= prediction.confidence <= 1.0
    assert prediction.processing_estimate_seconds > 0
    assert prediction.reasoning != ""

    # With captions + English, YouTube API should be recommended
    assert prediction.recommended_source == "youtube_api"
    assert prediction.quality_score >= 0.85

    print(f"  ✅ Basic prediction: score={prediction.quality_score}, "
          f"source={prediction.recommended_source}, "
          f"confidence={prediction.confidence}")


def test_transcript_quality_scorer_no_captions() -> None:
    """Without captions, scorer should recommend Gemini or STT."""

    scorer = TranscriptQualityScorer()

    metadata = {
        "title": "Rare Language Vlog",
        "duration_seconds": 300,
        "has_captions": False,
        "language": "th",  # Thai — not Tier 1
        "subscriber_count": 500,
        "view_count": 2_000,
    }

    prediction = scorer.predict(metadata)

    assert prediction.recommended_source != "youtube_api"
    assert prediction.quality_score < 0.90  # Lower confidence
    has_no_captions = "No closed captions" in prediction.reasoning
    has_fallback = "fallback" in prediction.reasoning.lower()
    assert has_no_captions or has_fallback

    print(f"  ✅ No-captions prediction: score={prediction.quality_score}, "
          f"source={prediction.recommended_source}")


def test_transcript_quality_scorer_live_stream() -> None:
    """Live streams should score lower than equivalent non-live videos."""

    scorer = TranscriptQualityScorer()

    live_metadata = {
        "title": "24/7 Live Stream",
        "duration_seconds": 7200,
        "has_captions": True,
        "language": "en",
        "is_live": True,
    }

    non_live_metadata = {
        "title": "24/7 Video",
        "duration_seconds": 7200,
        "has_captions": True,
        "language": "en",
        "is_live": False,
    }

    live_prediction = scorer.predict(live_metadata)
    non_live_prediction = scorer.predict(non_live_metadata)

    # Live should score lower than non-live (relative penalty)
    live_score = live_prediction.quality_score
    non_live_score = non_live_prediction.quality_score
    assert live_score <= non_live_score
    assert live_score < non_live_score  # Strict
    est = live_prediction.processing_estimate_seconds
    assert est > 2  # Scaled for long video

    print(
        f"  ✅ Live stream prediction: "
        f"score={live_prediction.quality_score} "
        f"vs non-live={non_live_prediction.quality_score}, "
        f"source={live_prediction.recommended_source}"
    )


def test_action_priority_ranker_basic() -> None:
    """Test that ranker sorts actions correctly."""

    ranker = ActionPriorityRanker()

    actions = [
        "maybe think about updating the docs someday",
        "Implement a rate limiter to handle 10,000 requests/second by Friday",
        "noted that the server was once slow",
        "Deploy the authentication service immediately — blocking $50K deal",
        "review the competitors",
    ]

    result = ranker.rank(actions)

    assert result.total_actions == 5
    assert len(result.ranked_actions) == 5  # noqa: PLR2004
    assert result.processing_time_seconds >= 0

    # Highest priority should be the urgent deployment
    top = result.ranked_actions[0]
    assert "Deploy" in top.original_text or "Implement" in top.original_text
    assert top.tier.value in {"critical", "high"}

    # Lowest should be the passive observation
    bottom = result.ranked_actions[-1]
    assert bottom.priority_score < top.priority_score

    print("  ✅ Ranking order (top→bottom):")
    for i, action in enumerate(result.ranked_actions):
        rank = i + 1
        tier = action.tier.value
        score = action.priority_score
        print(
            f"     {rank}. [{tier:8s}] "
            f"{score:.2f} — "
            f"{action.original_text[:60]}..."
        )


def test_action_ranker_with_context() -> None:
    """Video context should influence ranking."""

    ranker = ActionPriorityRanker()

    actions = [
        "Optimize the conversion funnel "
        "to improve retention by 15%",
        "Consider exploring new color schemes",
    ]

    context = {
        "view_count": 5_000_000,
        "category": "Education",
    }

    result = ranker.rank(actions, video_context=context)

    # With viral video context, business impact action should score higher
    top = result.ranked_actions[0]
    txt = top.original_text.lower()
    assert "conversion" in txt or "retention" in txt

    print(
        f"  ✅ Context-aware ranking: "
        f"top={top.priority_score:.2f} "
        f"({top.tier.value})"
    )


def test_model_info() -> None:
    """Models expose metadata."""

    scorer = TranscriptQualityScorer()
    ranker = ActionPriorityRanker()

    scorer_info = scorer.model_info
    ranker_info = ranker.model_info

    assert scorer_info["name"] == (
        "TranscriptQualityScorer"
    )
    assert ranker_info["name"] == (
        "ActionPriorityRanker"
    )
    assert "version" in scorer_info
    assert "version" in ranker_info

    print(
        f"  ✅ Model info: "
        f"scorer={scorer_info['version']}, "
        f"ranker={ranker_info['version']}"
    )


if __name__ == "__main__":
    tests = [
        (
            "Transcript Quality Scorer — Basic",
            test_transcript_quality_scorer_basic,
        ),
        (
            "Transcript Quality Scorer — No Captions",
            test_transcript_quality_scorer_no_captions,
        ),
        (
            "Transcript Quality Scorer — Live Stream",
            test_transcript_quality_scorer_live_stream,
        ),
        (
            "Action Priority Ranker — Basic",
            test_action_priority_ranker_basic,
        ),
        (
            "Action Priority Ranker — Context",
            test_action_ranker_with_context,
        ),
        ("Model Info", test_model_info),
    ]

    print("\n🧪 UVAI ML Model Tests\n" + "=" * 50)

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n📋 {name}:")
        try:
            test_fn()
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(
        f"Results: {passed} passed, "
        f"{failed} failed, "
        f"{passed + failed} total"
    )

    if failed > 0:
        sys.exit(1)
    print("🎉 All tests passed!")
