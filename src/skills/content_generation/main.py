#!/usr/bin/env python3
"""Thin GTM skill wrapper."""

import json
import sys
from typing import Any

SKILL_ID = "content-generation"


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the skill wrapper with a JSON-serializable payload."""
    return {
        "status": "success",
        "skill": SKILL_ID,
        "payload": payload,
    }


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    request = json.loads(raw) if raw else {}
    print(json.dumps(run(request)))
