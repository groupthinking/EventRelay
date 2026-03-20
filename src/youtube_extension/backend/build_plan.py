"""
Build Plan — Structured Instruction Extraction (Stage 2)
=========================================================

Defines the ``BuildPlan`` / ``BuildStep`` data model and the
``SemanticParser`` that transforms raw video-analysis output into
ordered, actionable build steps that Stage 3 (code generation) can
consume deterministically.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class BuildStep:
    """A single, actionable instruction in a build plan.

    Attributes:
        order:        1-based position in the overall sequence.
        action:       Verb describing what to do (e.g. "create", "install",
                      "configure", "implement").
        target_file:  Relative path of the file being created/modified.
                      Empty string if the step is not file-specific.
        description:  Human-readable explanation of the step.
        code_content: Code snippet associated with this step (may be empty).
        dependencies: Names of prerequisite steps or packages (e.g. ["react",
                      "step-1"]).
    """

    order: int
    action: str
    target_file: str
    description: str
    code_content: str = ""
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "action": self.action,
            "target_file": self.target_file,
            "description": self.description,
            "code_content": self.code_content,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildStep":
        return cls(
            order=int(data.get("order", 0)),
            action=str(data.get("action", "")),
            target_file=str(data.get("target_file", "")),
            description=str(data.get("description", "")),
            code_content=str(data.get("code_content", "")),
            dependencies=list(data.get("dependencies", [])),
        )


@dataclass
class BuildPlan:
    """Ordered collection of build steps derived from a video tutorial.

    Attributes:
        title:        Human-readable project title.
        project_type: "web" | "api" | "mobile" | …
        technologies: Primary tech stack (e.g. ["react", "tailwind"]).
        steps:        Ordered list of :class:`BuildStep` objects.
        summary:      Brief description of what will be built.
        raw_source:   Original data that was parsed (for diagnostics).
    """

    title: str
    project_type: str
    technologies: list[str]
    steps: list[BuildStep]
    summary: str = ""
    raw_source: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "project_type": self.project_type,
            "technologies": self.technologies,
            "steps": [s.to_dict() for s in self.steps],
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildPlan":
        return cls(
            title=str(data.get("title", "")),
            project_type=str(data.get("project_type", "web")),
            technologies=list(data.get("technologies", [])),
            steps=[BuildStep.from_dict(s) for s in data.get("steps", [])],
            summary=str(data.get("summary", "")),
            raw_source=data,
        )


# ---------------------------------------------------------------------------
# Gemini prompt helper
# ---------------------------------------------------------------------------

BUILD_PLAN_PROMPT_TEMPLATE = """\
You are a senior software engineer analyzing a YouTube tutorial video.
Your task is to produce a structured build plan so that a code generator can
reproduce the project shown in the video.

Return ONLY a JSON object that exactly matches the schema below — no prose,
no markdown fences.

Schema:
{{
  "title": "short project title",
  "project_type": "web" | "api" | "mobile" | "other",
  "technologies": ["<tech1>", "<tech2>"],
  "summary": "one-sentence description",
  "steps": [
    {{
      "order": 1,
      "action": "create" | "install" | "configure" | "implement" | "test" | "deploy",
      "target_file": "relative/path/to/file.ext",
      "description": "what this step accomplishes",
      "code_content": "verbatim code shown in the video (empty string if none)",
      "dependencies": ["prerequisite step description or package name"]
    }}
  ]
}}

Rules:
- Steps must be in chronological order (as seen in the video).
- Include at least 3 steps and at most 12 steps.
- Keep code_content to the most essential snippet (≤ 20 lines).
- If a field cannot be determined, use an empty string or empty list.

Video metadata:
  Title: {title}
  Channel: {channel}
  Duration: {duration}

Transcript excerpt:
{transcript}
"""


def build_gemini_prompt(metadata: dict[str, Any], transcript_text: str) -> str:
    """Return the Gemini prompt for structured build-plan extraction."""
    return BUILD_PLAN_PROMPT_TEMPLATE.format(
        title=metadata.get("title", "Unknown"),
        channel=metadata.get("channel", "Unknown"),
        duration=metadata.get("duration", "Unknown"),
        transcript=transcript_text[:3000],
    )


# ---------------------------------------------------------------------------
# SemanticParser
# ---------------------------------------------------------------------------


class SemanticParser:
    """Converts raw video-analysis output into a :class:`BuildPlan`.

    The parser applies a cascade of strategies so it degrades gracefully
    when Gemini is unavailable or returns unexpected output:

    1. If ``ai_analysis`` already contains a ``"build_plan"`` key (JSON),
       use it directly.
    2. If ``ai_analysis`` contains a ``"Learning Path"`` string, derive
       ordered steps from it.
    3. Fall back to transcript-based heuristics.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def parse(self, video_analysis: dict[str, Any]) -> BuildPlan:
        """Parse *video_analysis* dict and return a :class:`BuildPlan`."""
        ai_analysis: dict[str, Any] = video_analysis.get("ai_analysis") or {}
        metadata: dict[str, Any] = (
            video_analysis.get("metadata")
            or video_analysis.get("video_data")
            or {}
        )
        transcript_text: str = (video_analysis.get("transcript") or {}).get("text", "")
        extracted_info: dict[str, Any] = video_analysis.get("extracted_info") or {}

        title = (
            extracted_info.get("title")
            or metadata.get("title")
            or metadata.get("video_title")
            or "Generated Project"
        )
        technologies = self._coerce_list(
            extracted_info.get("technologies")
            or ai_analysis.get("Related Topics")
            or ai_analysis.get("Key Concepts")
            or []
        )
        project_type = extracted_info.get("project_type", "web")
        summary = (
            ai_analysis.get("Content Summary", "")
            or extracted_info.get("summary", "")
        )

        # Strategy 1 — pre-built plan embedded in ai_analysis
        embedded = ai_analysis.get("build_plan")
        if embedded:
            plan = self._parse_embedded_plan(embedded, title, technologies, project_type, summary)
            if plan:
                return plan

        # Strategy 2 — derive from Learning Path
        learning_path = ai_analysis.get("Learning Path", "")
        if learning_path:
            steps = self._steps_from_learning_path(learning_path)
            if steps:
                return BuildPlan(
                    title=title,
                    project_type=project_type,
                    technologies=technologies,
                    steps=steps,
                    summary=summary,
                    raw_source=video_analysis,
                )

        # Strategy 3 — derive from transcript
        if transcript_text:
            steps = self._steps_from_transcript(transcript_text, technologies)
            if steps:
                return BuildPlan(
                    title=title,
                    project_type=project_type,
                    technologies=technologies,
                    steps=steps,
                    summary=summary,
                    raw_source=video_analysis,
                )

        # Strategy 4 — minimal fallback from technologies
        steps = self._steps_from_technologies(technologies)
        return BuildPlan(
            title=title,
            project_type=project_type,
            technologies=technologies,
            steps=steps,
            summary=summary,
            raw_source=video_analysis,
        )

    # ------------------------------------------------------------------ #
    # Strategy helpers
    # ------------------------------------------------------------------ #

    def _parse_embedded_plan(
        self,
        embedded: Any,
        title: str,
        technologies: list[str],
        project_type: str,
        summary: str,
    ) -> BuildPlan | None:
        """Try to parse a pre-built plan from *embedded* (dict or JSON str)."""
        try:
            if isinstance(embedded, str):
                embedded = json.loads(embedded)
            if not isinstance(embedded, dict):
                return None

            steps_raw = embedded.get("steps", [])
            if not isinstance(steps_raw, list):
                return None

            steps = [BuildStep.from_dict(s) for s in steps_raw if isinstance(s, dict)]
            if not steps:
                return None

            return BuildPlan(
                title=embedded.get("title") or title,
                project_type=embedded.get("project_type") or project_type,
                technologies=self._coerce_list(
                    embedded.get("technologies") or technologies
                ),
                steps=steps,
                summary=embedded.get("summary") or summary,
                raw_source=embedded,
            )
        except Exception as exc:  # pragma: no cover – defensive
            logger.debug("Failed to parse embedded build_plan: %s", exc)
            return None

    def _steps_from_learning_path(self, learning_path: str) -> list[BuildStep]:
        """Convert a free-text learning path into ordered :class:`BuildStep` objects."""
        raw_lines = [
            line.strip(" -•*\t")
            for line in re.split(r"[\n\r]+", learning_path)
            if line.strip()
        ]
        steps: list[BuildStep] = []
        for i, line in enumerate(raw_lines[:12], start=1):
            action, target_file = self._infer_action_and_file(line)
            steps.append(
                BuildStep(
                    order=i,
                    action=action,
                    target_file=target_file,
                    description=line,
                )
            )
        return steps

    def _steps_from_transcript(
        self, transcript_text: str, technologies: list[str]
    ) -> list[BuildStep]:
        """Heuristically derive build steps from raw transcript sentences."""
        # Split into sentences and keep only ones that look like instructions
        action_pattern = re.compile(
            r"\b(create|add|install|configure|build|implement|set up|update|write|define|import|run|deploy)\b",
            re.IGNORECASE,
        )
        sentences = [s.strip() for s in re.split(r"[.!?]", transcript_text) if s.strip()]
        candidates = [s for s in sentences if action_pattern.search(s)][:12]

        if not candidates:
            candidates = sentences[:6]

        steps: list[BuildStep] = []
        for i, sentence in enumerate(candidates, start=1):
            action, target_file = self._infer_action_and_file(sentence)
            steps.append(
                BuildStep(
                    order=i,
                    action=action,
                    target_file=target_file,
                    description=sentence[:200],
                    dependencies=technologies[:2] if i == 1 else [],
                )
            )
        return steps

    def _steps_from_technologies(self, technologies: list[str]) -> list[BuildStep]:
        """Generate a minimal build plan from the technology list alone."""
        if not technologies:
            technologies = ["javascript", "html", "css"]

        primary = technologies[0] if technologies else "javascript"
        plan: list[tuple[str, str, str, list[str]]] = [
            ("create", "package.json", f"Initialize {primary} project", []),
            ("install", "", f"Install {', '.join(technologies[:3])} dependencies", []),
            ("create", "src/index.js", "Create application entry point", technologies[:1]),
            ("implement", "src/App.js", "Implement main application component", technologies[:2]),
            ("configure", "README.md", "Document the project", []),
        ]
        return [
            BuildStep(order=i, action=a, target_file=tf, description=desc, dependencies=deps)
            for i, (a, tf, desc, deps) in enumerate(plan, start=1)
        ]

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _infer_action_and_file(text: str) -> tuple[str, str]:
        """Guess the action verb and target file from a freeform instruction."""
        action = "implement"
        for verb in ("install", "create", "configure", "deploy", "test", "implement", "add", "update"):
            if re.search(rf"\b{verb}\b", text, re.IGNORECASE):
                action = verb
                break

        # Look for file-like tokens (contains a dot or a slash)
        file_match = re.search(r"[\w./\-]+\.\w+", text)
        target_file = file_match.group(0) if file_match else ""
        return action, target_file

    @staticmethod
    def _coerce_list(value: Any) -> list[str]:
        """Normalise common value shapes to a flat list of strings."""
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            parts = [p.strip() for p in re.split(r"[,|]", value) if p.strip()]
            return parts or [value.strip()]
        return []


# ---------------------------------------------------------------------------
# Module-level helper used by code_generator
# ---------------------------------------------------------------------------


def parse_build_plan(video_analysis: dict[str, Any]) -> BuildPlan:
    """Convenience wrapper — parse *video_analysis* into a :class:`BuildPlan`."""
    return SemanticParser().parse(video_analysis)
