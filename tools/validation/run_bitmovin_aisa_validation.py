#!/usr/bin/env python3
"""Run the EventRelay vs. Bitmovin AI Scene Analysis validation pass.

This runner is intentionally conservative:
- It always runs the EventRelay transcript-first baseline when API keys exist.
- It only uses Bitmovin AI Scene Analysis when real AISA JSON outputs are
  supplied; otherwise it reports the exact credentials and media inputs needed
  for a live Bitmovin run.
- It never fabricates scene metadata, because that would invalidate the test.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "docs" / "reports"


DEFAULT_CORPUS = [
    {
        "video_id": "mjkecNwp1X0",
        "url": "https://www.youtube.com/watch?v=mjkecNwp1X0",
        "title": "ChatGPT Agent Builder Full Tutorial: Building AI Agents in 2025 for Beginners",
        "category": "tutorial_demo",
        "reason": "Representative of EventRelay's developer/tutorial workflow.",
    },
    {
        "video_id": "rfonp8KiIso",
        "url": "https://www.youtube.com/watch?v=rfonp8KiIso",
        "title": "How to Build AI Agents Using Make.com (FREE COURSE 2025)",
        "category": "workflow_automation",
        "reason": "Representative of business workflow automation content.",
    },
    {
        "video_id": "ftBWgcwvEk4",
        "url": "https://www.youtube.com/watch?v=ftBWgcwvEk4",
        "title": "8 Hour AI Agents Course in 30 Minutes (DeepLearning.AI)",
        "category": "course_summary",
        "reason": "Representative of long-form educational content compressed into actionable moments.",
    },
]


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["action", "topic", "insight", "tool", "resource"],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["type", "title", "description", "timestamp", "priority"],
                "additionalProperties": False,
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["setup", "build", "deploy", "learn", "research", "configure"],
                    },
                    "estimatedMinutes": {"type": ["number", "null"]},
                },
                "required": ["title", "description", "category", "estimatedMinutes"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string"},
        "topics": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["events", "actions", "summary", "topics"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """You are an expert content analyst. Extract structured data from video transcripts.
Be specific and practical; avoid vague or generic items.
For events: classify type (action/topic/insight/tool/resource) and priority (high/medium/low).
For actions: generate concrete tasks a developer/learner should do after watching."""


@dataclass
class TranscriptResult:
    text: str
    segment_count: int
    word_count: int
    source: str


def load_environment() -> None:
    """Load repo env files without overriding already-exported shell values."""

    for candidate in [
        REPO_ROOT / ".env",
        REPO_ROOT / ".env.local",
        REPO_ROOT / "apps" / "web" / ".env.local",
        REPO_ROOT / "apps" / "web" / ".env.production",
    ]:
        if candidate.exists():
            load_dotenv(candidate, override=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPORT_DIR,
        help="Directory for JSON and Markdown reports.",
    )
    parser.add_argument(
        "--aisa-json-dir",
        type=Path,
        default=None,
        help="Optional directory containing Bitmovin AISA JSON files named by video_id or slug.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of default corpus videos to process.",
    )
    return parser.parse_args()


def fetch_transcript(video_id: str) -> TranscriptResult:
    transcript = YouTubeTranscriptApi().fetch(video_id, languages=["en"])
    parts = []
    raw_text_parts = []
    for item in transcript:
        text = item.text.replace("\n", " ").strip()
        if text:
            raw_text_parts.append(text)
            parts.append(f"[{format_seconds(item.start)}] {text}")
    full_text = " ".join(parts).strip()
    raw_text = " ".join(raw_text_parts).strip()
    return TranscriptResult(
        text=full_text,
        segment_count=len(transcript),
        word_count=len(raw_text.split()),
        source="youtube_transcript_api",
    )


def format_seconds(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def build_user_prompt(transcript: str, title: str, url: str) -> str:
    trimmed = transcript[:8000]
    return f"""Analyze this video transcript and extract structured data.

Video: {title}
URL: {url}

TRANSCRIPT:
{trimmed}

Respond with only valid JSON matching the requested schema."""


def extract_eventrelay_baseline(transcript: str, title: str, url: str) -> dict[str, Any]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for the EventRelay baseline extraction")

    client = OpenAI()
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(transcript, title, url),
        text={
            "format": {
                "type": "json_schema",
                "name": "eventrelay_event_extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)


def load_aisa_json(aisa_json_dir: Path | None, video: dict[str, str]) -> dict[str, Any] | None:
    if not aisa_json_dir:
        return None

    candidates = [
        aisa_json_dir / f"{video['video_id']}.json",
        aisa_json_dir / f"{slugify(video['title'])}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text())
    return None


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def scene_list(aisa_json: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(aisa_json.get("scenes"), list):
        return aisa_json["scenes"]
    data = aisa_json.get("data")
    if isinstance(data, dict) and isinstance(data.get("scenes"), list):
        return data["scenes"]
    return []


def map_aisa_moments(aisa_json: dict[str, Any], video_id: str) -> list[dict[str, Any]]:
    moments = []
    for scene in scene_list(aisa_json):
        content = scene.get("content") if isinstance(scene.get("content"), dict) else {}
        iab = scene.get("iab") if isinstance(scene.get("iab"), dict) else {}
        moments.append(
            {
                "moment_id": scene.get("id") or f"{video_id}:{len(moments) + 1}",
                "source_video_id": video_id,
                "start_seconds": scene.get("startInSeconds"),
                "end_seconds": scene.get("endInSeconds"),
                "transcript_span": None,
                "event_type": "evidence",
                "summary": scene.get("summary") or scene.get("verboseSummary") or scene.get("title"),
                "visual_context": {
                    "objects": content.get("objects") or [],
                    "brands": content.get("brands") or [],
                    "settings": content.get("settings") or [],
                    "characters": content.get("characters") or [],
                    "atmosphere": content.get("atmosphere") or [],
                },
                "topics": scene.get("keywords") or [],
                "sensitive_topics": scene.get("sensitiveTopics") or [],
                "iab": {
                    "content_taxonomies": iab.get("contentTaxonomies") or [],
                    "ad_opportunity_taxonomies": iab.get("adOpportunityTaxonomies") or [],
                    "sensitive_topic_taxonomies": iab.get("sensitiveTopicTaxonomies") or [],
                },
                "actionability_score": None,
                "evidence": [scene.get("verboseSummary") or scene.get("summary") or ""],
            }
        )
    return moments


def summarize_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    events = extraction.get("events") if isinstance(extraction.get("events"), list) else []
    actions = extraction.get("actions") if isinstance(extraction.get("actions"), list) else []
    topics = extraction.get("topics") if isinstance(extraction.get("topics"), list) else []
    timestamped = [event for event in events if event.get("timestamp")]
    high_priority = [event for event in events if event.get("priority") == "high"]
    return {
        "events_count": len(events),
        "actions_count": len(actions),
        "topics_count": len(topics),
        "timestamped_events_count": len(timestamped),
        "high_priority_events_count": len(high_priority),
        "event_titles": [event.get("title") for event in events[:5]],
        "action_titles": [action.get("title") for action in actions[:5]],
        "topics": topics[:10],
    }


def summarize_aisa(moments: list[dict[str, Any]]) -> dict[str, Any]:
    visual_moments = 0
    sensitive_moments = 0
    keyword_total = 0
    for moment in moments:
        visual = moment["visual_context"]
        if any(visual.get(key) for key in ["objects", "brands", "settings", "characters", "atmosphere"]):
            visual_moments += 1
        if moment.get("sensitive_topics"):
            sensitive_moments += 1
        keyword_total += len(moment.get("topics") or [])

    return {
        "scene_count": len(moments),
        "visual_context_moments": visual_moments,
        "sensitive_topic_moments": sensitive_moments,
        "keyword_count": keyword_total,
        "first_moment": moments[0] if moments else None,
    }


def evaluate_value(baseline: dict[str, Any], aisa: dict[str, Any] | None) -> dict[str, Any]:
    if not aisa:
        return {
            "status": "blocked",
            "decision": "Cannot evaluate Bitmovin uplift without real AISA JSON for the same assets.",
            "next_step": "Provide BITMOVIN_API_KEY, BITMOVIN_OUTPUT_ID, and direct MP4/HLS/DASH media URLs, or place exported AISA JSON files in --aisa-json-dir.",
        }

    improvements = []
    if aisa["scene_count"] > baseline["timestamped_events_count"]:
        improvements.append("scene boundaries may improve timestamp coverage")
    if aisa["visual_context_moments"]:
        improvements.append("visual metadata can ground non-spoken evidence")
    if aisa["keyword_count"]:
        improvements.append("scene keywords may improve search and topic recall")

    if improvements:
        decision = "Potential value found; run human review on mapped moments before integrating."
    else:
        decision = "No clear uplift visible from supplied AISA output."

    return {
        "status": "evaluated",
        "decision": decision,
        "potential_improvements": improvements,
    }


def bitmovin_readiness() -> dict[str, Any]:
    return {
        "api_key_present": bool(os.environ.get("BITMOVIN_API_KEY")),
        "output_id_present": bool(os.environ.get("BITMOVIN_OUTPUT_ID")),
        "live_aisa_status": (
            "ready_for_direct_media_inputs"
            if os.environ.get("BITMOVIN_API_KEY") and os.environ.get("BITMOVIN_OUTPUT_ID")
            else "blocked_missing_bitmovin_credentials"
        ),
        "required_live_inputs": [
            "BITMOVIN_API_KEY",
            "BITMOVIN_OUTPUT_ID",
            "direct MP4, HLS, or DASH URLs for the same assets being evaluated",
        ],
    }


def write_reports(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = out_dir / f"bitmovin-aisa-validation-{stamp}.json"
    md_path = out_dir / f"bitmovin-aisa-validation-{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report))
    return json_path, md_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Bitmovin AI Scene Analysis Validation Run",
        "",
        f"Run timestamp: {report['run_timestamp']}",
        "",
        "## Verdict",
        "",
        report["verdict"],
        "",
        "## Bitmovin Readiness",
        "",
        f"- API key present: {report['bitmovin_readiness']['api_key_present']}",
        f"- Output ID present: {report['bitmovin_readiness']['output_id_present']}",
        f"- Live AISA status: {report['bitmovin_readiness']['live_aisa_status']}",
        "",
        "## Per-Video Results",
        "",
    ]

    for item in report["videos"]:
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- URL: {item['url']}",
                f"- Category: {item['category']}",
                f"- Transcript: {item['transcript']['word_count']} words across {item['transcript']['segment_count']} segments",
                f"- Baseline events/actions/topics: {item['eventrelay_baseline']['events_count']} / {item['eventrelay_baseline']['actions_count']} / {item['eventrelay_baseline']['topics_count']}",
                f"- Timestamped baseline events: {item['eventrelay_baseline']['timestamped_events_count']}",
                f"- Bitmovin AISA: {item['aisa']['status']}",
                f"- Value evaluation: {item['value_evaluation']['decision']}",
                "",
            ]
        )
        if item["eventrelay_baseline"]["event_titles"]:
            lines.append("Baseline event titles:")
            for title in item["eventrelay_baseline"]["event_titles"]:
                lines.append(f"- {title}")
            lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Sources",
            "",
            "- EventRelay baseline: local transcript-first OpenAI Responses API extraction, matching the app schema.",
            "- Bitmovin AISA docs: https://developer.bitmovin.com/encoding/docs/getting-started-with-ai-scene-analysis",
            "- Bitmovin AISA API result shape: https://developer.bitmovin.com/encoding/docs/ai-scene-analysis",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    load_environment()

    corpus = DEFAULT_CORPUS[: args.limit]
    readiness = bitmovin_readiness()
    videos = []

    for video in corpus:
        try:
            transcript = fetch_transcript(video["video_id"])
            extraction = extract_eventrelay_baseline(
                transcript=transcript.text,
                title=video["title"],
                url=video["url"],
            )
            baseline_summary = summarize_extraction(extraction)

            aisa_json = load_aisa_json(args.aisa_json_dir, video)
            if aisa_json:
                moments = map_aisa_moments(aisa_json, video["video_id"])
                aisa_summary = {
                    "status": "loaded_from_json",
                    **summarize_aisa(moments),
                }
            else:
                aisa_summary = {
                    "status": "not_run",
                    "reason": (
                        "No local AISA JSON was supplied. Live Bitmovin run also requires "
                        "BITMOVIN_API_KEY, BITMOVIN_OUTPUT_ID, and direct MP4/HLS/DASH input URLs."
                    ),
                }

            videos.append(
                {
                    **video,
                    "transcript": {
                        "source": transcript.source,
                        "segment_count": transcript.segment_count,
                        "word_count": transcript.word_count,
                    },
                    "eventrelay_baseline": baseline_summary,
                    "aisa": aisa_summary,
                    "value_evaluation": evaluate_value(baseline_summary, aisa_summary if aisa_json else None),
                    "raw_eventrelay_extraction": extraction,
                }
            )
        except Exception as exc:
            videos.append(
                {
                    **video,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    complete_baselines = [video for video in videos if "eventrelay_baseline" in video]
    aisa_loaded = [video for video in videos if video.get("aisa", {}).get("status") == "loaded_from_json"]

    if not complete_baselines:
        verdict = "Validation did not run: EventRelay baseline extraction failed for every video."
    elif not aisa_loaded:
        verdict = (
            "Partial validation run completed. EventRelay baseline extraction ran, but Bitmovin AISA "
            "uplift could not be measured because no Bitmovin credentials/direct media inputs or AISA JSON outputs were available."
        )
    else:
        verdict = "Validation completed with EventRelay baseline and Bitmovin AISA JSON comparison."

    interpretation = (
        "The current run can judge EventRelay's transcript-first extraction behavior, but it cannot make "
        "a defensible yes/no call on Bitmovin uplift until real scene-level metadata exists for the same assets. "
        "Do not treat synthetic or model-generated scene descriptions as Bitmovin validation evidence."
    )

    report = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "verdict": verdict,
        "bitmovin_readiness": readiness,
        "videos": videos,
        "interpretation": interpretation,
    }

    json_path, md_path = write_reports(report, args.out_dir)
    print(f"Wrote JSON report: {json_path}")
    print(f"Wrote Markdown report: {md_path}")
    print(verdict)
    return 0 if complete_baselines else 1


if __name__ == "__main__":
    sys.exit(main())
