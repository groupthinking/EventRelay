#!/usr/bin/env python3
"""HyperFrames output agent for rendering transcript-driven videos."""

from __future__ import annotations

import asyncio
import html
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from youtube_extension.utils import extract_video_id

from ..base_agent import BaseAgent
from ..dto import AgentRequest, AgentResult
from ..registry import register

HYPERFRAMES_VERSION = "0.5.5"


@register
class HyperFramesAgent(BaseAgent):
    """Render a lightweight recap video with HyperFrames."""

    name = "hyperframes"

    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or {}
        self._render_root = Path(
            cfg.get("render_root")
            or os.getenv("HYPERFRAMES_RENDER_ROOT", ".runtime/hyperframes")
        )
        self._enabled = self._is_enabled(cfg.get("enabled"))
        self._duration_seconds = int(cfg.get("duration_seconds", 12))

    async def run(self, req: AgentRequest) -> AgentResult:
        if not self._enabled:
            return AgentResult(
                status="ok",
                output={"status": "disabled", "reason": "HyperFrames integration disabled"},
                logs=[],
            )

        video_url = str(req.params.get("video_url") or "").strip()
        transcript = str(req.params.get("transcript") or "").strip()
        metadata = req.params.get("metadata") or {}
        transcript_segments = req.params.get("transcript_segments") or []

        if not video_url:
            return AgentResult(status="error", output={}, logs=["Missing video URL"])
        if not transcript:
            return AgentResult(status="error", output={}, logs=["Missing transcript text"])

        try:
            video_id = extract_video_id(video_url)
        except ValueError as exc:
            return AgentResult(status="error", output={}, logs=[str(exc)])

        title = self._build_title(metadata, video_id)
        summary = self._build_summary(transcript)
        highlights = self._build_highlights(transcript_segments, transcript)

        output_dir = self._render_root / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "rendered.mp4"

        temp_dir = Path(tempfile.mkdtemp(prefix=f"hyperframes-{video_id}-"))
        project_dir = temp_dir / video_id
        project_dir.mkdir(parents=True, exist_ok=True)
        project_file = project_dir / "index.html"
        temp_output = project_dir / "rendered.mp4"

        try:
            project_file.write_text(
                self._build_composition_html(
                    title=title,
                    summary=summary,
                    highlights=highlights,
                ),
                encoding="utf-8",
            )
            await self._render_project(project_dir=project_dir, output_path=temp_output)
            shutil.move(str(temp_output), str(output_path))
        except Exception as exc:
            return AgentResult(status="error", output={}, logs=[str(exc)])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return AgentResult(
            status="ok",
            output={
                "status": "complete",
                "video_id": video_id,
                "title": title,
                "summary": summary,
                "format": "mp4",
                "duration_seconds": self._duration_seconds,
                "file_path": str(output_path.resolve()),
                "highlights": highlights,
            },
            logs=[],
        )

    async def _render_project(self, *, project_dir: Path, output_path: Path) -> None:
        command = self._build_command(output_path)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                "HyperFrames render failed: "
                + (stderr.decode("utf-8", errors="replace").strip() or stdout.decode("utf-8", errors="replace").strip())
            )
        if not output_path.exists():
            raise RuntimeError("HyperFrames render completed without producing an output file")

    def _build_command(self, output_path: Path) -> list[str]:
        if shutil.which("hyperframes"):
            return [
                "npx",
                "--no-install",
                "hyperframes",
                "render",
                "--output",
                str(output_path),
                "--quiet",
            ]

        return [
            "npx",
            "--yes",
            f"hyperframes@{HYPERFRAMES_VERSION}",
            "render",
            "--output",
            str(output_path),
            "--quiet",
        ]

    def _build_composition_html(
        self,
        *,
        title: str,
        summary: str,
        highlights: list[dict[str, str]],
    ) -> str:
        escaped_title = html.escape(title)
        escaped_summary = html.escape(summary)
        highlight_markup = "".join(
            (
                '<div class="highlight clip" '
                f'data-start="{1 + index * 2}" data-duration="4" data-track-index="{index + 1}">'
                f"<span>{html.escape(item['timestamp'])}</span>"
                f"<p>{html.escape(item['text'])}</p>"
                "</div>"
            )
            for index, item in enumerate(highlights)
        )
        return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>{escaped_title}</title>
    <style>
      :root {{
        color-scheme: dark;
        font-family: Inter, Arial, sans-serif;
      }}
      html, body {{
        margin: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at top left, #12343b 0%, #040507 65%);
        color: #f8fafc;
      }}
      #stage {{
        position: relative;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: linear-gradient(135deg, rgba(17,24,39,0.96), rgba(6,95,70,0.88));
      }}
      .clip {{
        position: absolute;
        opacity: 0;
        animation: fadeIn 0.8s ease forwards;
      }}
      .eyebrow {{
        top: 88px;
        left: 104px;
        letter-spacing: 0.38em;
        font-size: 30px;
        text-transform: uppercase;
        color: #5eead4;
      }}
      .title {{
        top: 152px;
        left: 104px;
        width: 1100px;
        font-size: 92px;
        font-weight: 800;
        line-height: 1.02;
      }}
      .summary {{
        top: 402px;
        left: 104px;
        width: 1110px;
        font-size: 38px;
        line-height: 1.45;
        color: rgba(226, 232, 240, 0.92);
      }}
      .rail {{
        position: absolute;
        top: 116px;
        right: 104px;
        width: 520px;
        bottom: 116px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: rgba(2, 6, 23, 0.4);
        backdrop-filter: blur(18px);
      }}
      .rail-header {{
        position: absolute;
        top: 42px;
        left: 42px;
        font-size: 24px;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: rgba(148, 163, 184, 0.92);
      }}
      .highlight {{
        left: 42px;
        right: 42px;
        min-height: 160px;
        padding: 28px 30px;
        border-left: 4px solid #5eead4;
        background: rgba(15, 23, 42, 0.62);
      }}
      .highlight span {{
        display: inline-block;
        margin-bottom: 14px;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #5eead4;
      }}
      .highlight p {{
        margin: 0;
        font-size: 32px;
        line-height: 1.32;
      }}
      .highlight:nth-of-type(1) {{ top: 110px; }}
      .highlight:nth-of-type(2) {{ top: 314px; }}
      .highlight:nth-of-type(3) {{ top: 518px; }}
      .footer {{
        left: 104px;
        right: 104px;
        bottom: 72px;
        display: flex;
        justify-content: space-between;
        font-size: 24px;
        color: rgba(148, 163, 184, 0.9);
      }}
      @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(18px); }}
        to {{ opacity: 1; transform: translateY(0); }}
      }}
    </style>
  </head>
  <body>
    <div
      id="stage"
      data-composition-id="eventrelay-hyperframes"
      data-start="0"
      data-duration="{self._duration_seconds}"
      data-width="1920"
      data-height="1080"
    >
      <div class="eyebrow clip" data-start="0" data-duration="{self._duration_seconds}" data-track-index="0">
        EventRelay HyperFrames Render
      </div>
      <div class="title clip" data-start="0" data-duration="{self._duration_seconds}" data-track-index="0">
        {escaped_title}
      </div>
      <div class="summary clip" data-start="0.5" data-duration="{self._duration_seconds - 1}" data-track-index="0">
        {escaped_summary}
      </div>
      <div class="rail clip" data-start="1" data-duration="{self._duration_seconds - 1}" data-track-index="1">
        <div class="rail-header">Key Moments</div>
        {highlight_markup}
      </div>
      <div class="footer clip" data-start="8" data-duration="4" data-track-index="2">
        <span>Single workflow: YouTube → context → agents → outputs</span>
        <span>Powered by HyperFrames</span>
      </div>
    </div>
  </body>
</html>
"""

    def _build_title(self, metadata: dict[str, Any], video_id: str) -> str:
        raw_title = str(metadata.get("title") or "").strip()
        return raw_title[:96] or f"Video recap · {video_id}"

    @staticmethod
    def _build_summary(transcript: str) -> str:
        compact = " ".join(transcript.split())
        if len(compact) <= 260:
            return compact
        return compact[:257].rstrip() + "..."

    @staticmethod
    def _build_highlights(
        transcript_segments: list[dict[str, Any]],
        transcript: str,
    ) -> list[dict[str, str]]:
        highlights: list[dict[str, str]] = []
        for segment in transcript_segments:
            text = " ".join(str(segment.get("text") or "").split())
            if not text:
                continue
            timestamp = HyperFramesAgent._format_timestamp(segment.get("start") or segment.get("start_time"))
            highlights.append(
                {
                    "timestamp": timestamp,
                    "text": text[:110].rstrip() + ("..." if len(text) > 110 else ""),
                }
            )
            if len(highlights) == 3:
                return highlights

        sentences = [
            sentence.strip()
            for sentence in transcript.replace("\n", " ").split(".")
            if sentence.strip()
        ]
        for index, sentence in enumerate(sentences[:3]):
            highlights.append(
                {
                    "timestamp": f"{index:02d}:00",
                    "text": sentence[:110].rstrip() + ("..." if len(sentence) > 110 else ""),
                }
            )
        return highlights or [{"timestamp": "00:00", "text": "Transcript summary unavailable."}]

    @staticmethod
    def _format_timestamp(value: Any) -> str:
        try:
            total_seconds = max(0, int(float(value)))
        except (TypeError, ValueError):
            return "00:00"
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _is_enabled(config_value: Any) -> bool:
        if isinstance(config_value, bool):
            return config_value
        env_value = str(os.getenv("HYPERFRAMES_ENABLED", "")).strip().lower()
        if config_value is None:
            return env_value in {"1", "true", "yes", "on"}
        return str(config_value).strip().lower() in {"1", "true", "yes", "on"}
