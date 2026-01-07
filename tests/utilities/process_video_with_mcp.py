"""Compatibility wrapper exposing the canonical video processor module.

Historically, callers imported ``process_video_with_mcp`` from the project
root. The real implementation now lives in ``agents.process_video_with_mcp``;
this file keeps the legacy import path functional while avoiding duplicate
logic.
"""

from agents.process_video_with_mcp import *  # noqa: F401,F403

