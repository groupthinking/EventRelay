"""Regression coverage for Grok Build project wiring (#2760)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GROK_CONFIG = ROOT / ".grok" / "config.toml"
AGENTS_MD = ROOT / "AGENTS.md"

_SECRETISH = re.compile(
    r"(?:ghp_|github_pat_|sk_live_|sk_test_|xai-|vercel_)"
    r"[A-Za-z0-9_\-]{8,}"
)


@pytest.mark.unit
def test_grok_project_config_exists() -> None:
    assert GROK_CONFIG.is_file(), f"missing {GROK_CONFIG}"


@pytest.mark.unit
def test_grok_project_config_mcp_stubs() -> None:
    raw = GROK_CONFIG.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    servers = parsed["mcp_servers"]

    assert set(servers) == {"github", "vercel"}
    assert "command" not in servers["github"]
    assert servers["github"]["url"] == "https://api.githubcopilot.com/mcp/"
    assert servers["github"]["headers"]["Authorization"] == "Bearer ${GITHUB_TOKEN}"
    assert servers["vercel"]["url"] == "https://mcp.vercel.com"
    assert "headers" not in servers["vercel"]
    assert "env" not in servers["vercel"]
    assert "Authorization: Bearer ${VERCEL_TOKEN}" not in raw
    assert "grok mcp add --transport http -s project github" in raw
    assert "grok mcp add --transport http -s project vercel" in raw
    assert "--header 'Authorization: Bearer ${GITHUB_TOKEN}'" in raw
    assert '--header "Authorization: Bearer ${GITHUB_TOKEN}"' not in raw
    assert "writes the literal secret" in raw
    assert "Do not pass a double-quoted Authorization header" in raw
    assert "OAuth 2.1" in raw
    assert "mcp_credentials.json" in raw
    assert _SECRETISH.search(raw) is None


@pytest.mark.unit
def test_agents_md_encodes_locked_public_facts() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8")
    for needle in (
        "https://uvai.io",
        "github.com/groupthinking/EventRelay",
        "v0-uvai",
        "google/gemini-3.8-flash",
        "upstash-uvai-pack",
        "STORAGE_REDIS_URL",
        "redis-carmine-saddle",
        "Turnstile→Stripe",
        "MNNfat_QP0E",
        "Do not bounce work to forge, slingshot, reach, uvai-skills, ClipToAction",
        "Google G.A.T.E./GEAR",
        "50/50 milestone is already met",
        ".grok/config.toml",
        "stop and ask",
    ):
        assert needle in text, f"missing locked fact: {needle}"
