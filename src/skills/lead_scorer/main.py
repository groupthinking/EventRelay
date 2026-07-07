#!/usr/bin/env python3
"""Thin GTM skill wrapper."""

import json
import sys
from typing import Any


def run(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "skill": __name__.split(".")[-2],
        "payload": payload,
    }


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    request = json.loads(raw) if raw else {}
    print(json.dumps(run(request)))
