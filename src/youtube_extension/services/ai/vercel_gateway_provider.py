"""Vercel AI Gateway provider (OpenAI-compatible).

A lightweight, dependency-free client for the Vercel AI Gateway
(https://ai-gateway.vercel.sh/v1), which routes to 280+ models across
OpenAI, Anthropic, Google, and others behind a single OpenAI-compatible
API. Authentication uses the ``VERCEL_API_KEY`` already present in the
deployment environment, so the multi-provider AI design documented in
CLAUDE.md works even when no direct Gemini/OpenAI key is configured.

REAL_MODE_ONLY: every call here is a real, billed model invocation. There is
no mock path -- if ``VERCEL_API_KEY`` is absent, ``gateway_available()``
returns False and callers fall back to their own deterministic logic.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

GATEWAY_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
DEFAULT_MODEL = os.getenv("VERCEL_AI_MODEL", "google/gemini-2.0-flash")


def _resolve_gateway_key() -> str:
    """Resolve Vercel AI Gateway API key (vck_…)."""
    return (
        os.getenv("AI_GATEWAY_API_KEY")
        or os.getenv("VERCEL_AI_GATEWAY_API_KEY")
        or os.getenv("VERCEL_AI_GATEWAY_API")
        or os.getenv("VERCEL_API_KEY")
        or ""
    ).strip()


def gateway_available() -> bool:
    """True when a Vercel AI Gateway key is configured."""
    return bool(_resolve_gateway_key())


def chat(
    messages: list[dict],
    model: str | None = None,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: int = 60,
) -> str:
    """Run a chat completion through the gateway and return the text content.

    Raises on transport/auth errors so callers can fall back deterministically.
    """
    key = _resolve_gateway_key()
    if not key:
        raise RuntimeError(
            "AI Gateway API key is not set (AI_GATEWAY_API_KEY or VERCEL_API_KEY)"
        )
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        GATEWAY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # surface the gateway's message
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"Vercel AI Gateway HTTP {exc.code}: {detail}") from exc

    choice = (data.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    logger.info(
        "Vercel AI Gateway model=%s tokens=%s cost=%s",
        data.get("model"),
        usage.get("total_tokens"),
        usage.get("cost"),
    )
    return content


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


def extract_events(
    transcript: str, model: str | None = None, max_events: int = 30
) -> list[dict]:
    """Extract structured events from transcript text using a real LLM.

    Returns a list of dicts with keys: type, title, description, timestamp.
    Returns an empty list if the gateway is unavailable or the response cannot
    be parsed, letting the caller fall back to heuristic extraction.
    """
    if not gateway_available():
        return []

    system = (
        "You extract actionable events from video transcripts. "
        "Return ONLY a compact JSON array (no prose, no code fence). "
        'Each item: {"type": one of action|mention|topic|insight, '
        '"title": short string, "description": string or null, '
        '"timestamp": string or null}.'
    )
    # Increase context window to 120k chars (~30k tokens) to avoid silent data loss
    limit = 120_000
    truncated_transcript = transcript[:limit]
    if len(transcript) > limit:
        logger.info("Transcript truncated from %d to %d chars for Vercel AI Gateway extraction", len(transcript), limit)
        truncated_transcript += "\n[... transcript truncated ...]"

    user = (
        f"Extract up to {max_events} key events from this transcript text:\n\n"
        + truncated_transcript
    )
    content = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        max_tokens=2048,
    )
    try:
        parsed = json.loads(_strip_code_fence(content))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Gateway event JSON parse failed: %s", exc)
        return []

    if not isinstance(parsed, list):
        return []

    events: list[dict] = []
    for raw in parsed[:max_events]:
        if not isinstance(raw, dict):
            continue
        etype = str(raw.get("type", "topic")).lower()
        if etype not in {"action", "mention", "topic", "insight"}:
            etype = "topic"
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        events.append(
            {
                "type": etype,
                "title": title[:200],
                "description": (raw.get("description") or None),
                "timestamp": (raw.get("timestamp") or None),
            }
        )
    return events
