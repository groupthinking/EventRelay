#!/usr/bin/env python3
"""Build the category matrix and enforce run-level guardrails.

Runs in the ``prepare`` job of ``autonomous-video-processing.yml``. It fails the
run *before* any external API call when the requested batch exceeds the video or
model-call caps.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from autonomous_video_processing import (  # noqa: E402
    DEFAULT_MAX_MODEL_CALLS,
    DEFAULT_MAX_VIDEOS_PER_RUN,
    GuardrailError,
    enforce_guardrails,
)


def parse_categories(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    return int(raw) if raw else default


def main() -> int:
    categories = parse_categories(os.environ.get("CATEGORIES", ""))
    if not categories:
        print("::error::no categories supplied", file=sys.stderr)
        return 2

    try:
        budget = enforce_guardrails(
            categories=categories,
            videos_per_category=_int_env("VIDEOS_PER_CATEGORY", 5),
            mode=os.environ.get("PIPELINE_MODE", "discovery"),
            max_videos_per_run=_int_env("MAX_VIDEOS_PER_RUN", DEFAULT_MAX_VIDEOS_PER_RUN),
            max_model_calls=_int_env("MAX_MODEL_CALLS", DEFAULT_MAX_MODEL_CALLS),
        )
    except (GuardrailError, ValueError) as exc:
        print(f"::error::guardrail violation: {exc}", file=sys.stderr)
        return 1

    matrix = {"include": [{"category": category} for category in categories]}
    print(f"Planned budget: {budget}")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"matrix={json.dumps(matrix)}\n")
    else:
        print(json.dumps(matrix))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
