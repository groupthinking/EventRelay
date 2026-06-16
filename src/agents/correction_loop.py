#!/usr/bin/env python3
"""
Correction Feedback Loop - Closes the quality-to-rewrite cycle.

Currently, EventRelay's quality agent scores output but nothing acts on low
scores. This module wires quality assessment into architecture agent rewrites:

    quality_agent.assess() → score < threshold → architecture_agent.rewrite() → code_gen.regenerate()

Think of it like a spell-checker that not only underlines mistakes but also
rewrites the sentence for you — except at the architecture level.

Max 2 correction iterations to prevent infinite loops.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .skill_monitor_emitter import get_emitter

logger = logging.getLogger(__name__)

# Threshold below which correction is triggered (0-100 scale)
DEFAULT_QUALITY_THRESHOLD = 70
MAX_CORRECTION_ITERATIONS = 2


@dataclass
class CorrectionResult:
    """Result of a correction loop run."""

    triggered: bool
    iterations_run: int
    initial_score: float
    final_score: float
    corrections: list[dict[str, Any]] = field(default_factory=list)
    feedback_used: bool = False


class CorrectionLoop:
    """
    Orchestrates the quality → rewrite → regenerate cycle.

    Usage:
        loop = CorrectionLoop(
            quality_fn=quality_agent.assess_actionability,
            rewrite_fn=architecture_agent.handle_rewrite,
            regenerate_fn=code_generator.regenerate,
        )
        result = await loop.run(pipeline_output, feedback=user_feedback)
    """

    def __init__(
        self,
        quality_fn=None,
        rewrite_fn=None,
        regenerate_fn=None,
        threshold: float = DEFAULT_QUALITY_THRESHOLD,
        max_iterations: int = MAX_CORRECTION_ITERATIONS,
    ):
        """
        Args:
            quality_fn: Callable that scores output. Signature:
                        (actions, transcript_segments, metadata) -> dict with "score" key
            rewrite_fn: Async callable that rewrites architecture based on feedback.
                        Signature: (context) -> dict with revised plan
            regenerate_fn: Async callable that regenerates code from revised plan.
                          Signature: (architecture, video_analysis) -> dict
            threshold: Score below which correction triggers (0-100)
            max_iterations: Maximum rewrite attempts
        """
        self.quality_fn = quality_fn
        self.rewrite_fn = rewrite_fn
        self.regenerate_fn = regenerate_fn
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.emitter = get_emitter()

    async def run(
        self,
        pipeline_output: dict[str, Any],
        feedback: Optional[dict[str, Any]] = None,
    ) -> CorrectionResult:
        """Execute the correction loop.

        Args:
            pipeline_output: Current pipeline state containing stage outputs.
                            Expected keys: "video-ingest_output", "code-gen_output",
                            "build-validator_output", "architect_output"
            feedback: Optional user feedback dict with keys:
                     "rating" (1-5), "comment" (str), "tab" (str)

        Returns:
            CorrectionResult with details of what happened.
        """
        video_analysis = pipeline_output.get("video-ingest_output", {})
        actions = video_analysis.get("content_analysis", {}).get("actions", [])
        transcript_segments = video_analysis.get("transcript_segments", [])

        # Initial quality assessment
        if not self.quality_fn:
            logger.warning("No quality function provided — skipping correction loop")
            return CorrectionResult(
                triggered=False,
                iterations_run=0,
                initial_score=0,
                final_score=0,
            )

        quality_report = self.quality_fn(actions, transcript_segments)
        initial_score = quality_report.get("score", 0)
        current_score = initial_score

        logger.info(f"Quality gate: initial score = {initial_score:.1f} (threshold: {self.threshold})")

        await self.emitter.emit("pipeline.event", {
            "event": "quality_gate.assessed",
            "score": initial_score,
            "threshold": self.threshold,
            "will_correct": initial_score < self.threshold,
        })

        # Check if correction is needed
        if initial_score >= self.threshold:
            return CorrectionResult(
                triggered=False,
                iterations_run=0,
                initial_score=initial_score,
                final_score=initial_score,
            )

        # Factor in user feedback if available
        feedback_context = self._build_feedback_context(feedback)

        corrections = []
        for iteration in range(self.max_iterations):
            logger.info(
                f"Correction iteration {iteration + 1}/{self.max_iterations} "
                f"(current score: {current_score:.1f})"
            )

            await self.emitter.emit("pipeline.event", {
                "event": "correction.triggered",
                "iteration": iteration + 1,
                "current_score": current_score,
                "threshold": self.threshold,
            })

            # Step 1: Architecture agent rewrites the plan
            rewrite_context = {
                "quality_report": quality_report,
                "current_architecture": pipeline_output.get("architect_output", {}),
                "video_analysis": video_analysis,
                "feedback": feedback_context,
                "iteration": iteration + 1,
                "correction_prompt": self._build_correction_prompt(
                    quality_report, feedback_context
                ),
            }

            revised_architecture = None
            if self.rewrite_fn:
                try:
                    revised_architecture = await self.rewrite_fn(rewrite_context)
                    pipeline_output["architect_output"] = revised_architecture
                except Exception as e:
                    logger.error(f"Architecture rewrite failed: {e}")
                    corrections.append({
                        "iteration": iteration + 1,
                        "step": "rewrite",
                        "success": False,
                        "error": str(e),
                    })
                    break

            # Step 2: Regenerate code from revised architecture
            regenerated = None
            if self.regenerate_fn and revised_architecture:
                try:
                    regenerated = await self.regenerate_fn(
                        revised_architecture, video_analysis
                    )
                    pipeline_output["code-gen_output"] = regenerated
                except Exception as e:
                    logger.error(f"Code regeneration failed: {e}")
                    corrections.append({
                        "iteration": iteration + 1,
                        "step": "regenerate",
                        "success": False,
                        "error": str(e),
                    })
                    break

            # Step 3: Re-assess quality
            quality_report = self.quality_fn(actions, transcript_segments)
            current_score = quality_report.get("score", 0)

            corrections.append({
                "iteration": iteration + 1,
                "previous_score": corrections[-1].get("new_score", initial_score) if corrections else initial_score,
                "new_score": current_score,
                "step": "complete",
                "success": True,
                "revised_architecture": revised_architecture is not None,
                "regenerated_code": regenerated is not None,
            })

            await self.emitter.emit("pipeline.event", {
                "event": "correction.completed",
                "iteration": iteration + 1,
                "new_score": current_score,
                "improved": current_score > initial_score,
            })

            if current_score >= self.threshold:
                logger.info(
                    f"Quality threshold met after {iteration + 1} iteration(s): "
                    f"{current_score:.1f} >= {self.threshold}"
                )
                break

        return CorrectionResult(
            triggered=True,
            iterations_run=len(corrections),
            initial_score=initial_score,
            final_score=current_score,
            corrections=corrections,
            feedback_used=feedback is not None,
        )

    def _build_feedback_context(self, feedback: Optional[dict]) -> str:
        """Convert user feedback into a prompt-friendly context string."""
        if not feedback:
            return ""

        parts = []
        if feedback.get("rating"):
            parts.append(f"User rating: {feedback['rating']}/5")
        if feedback.get("comment"):
            parts.append(f"User feedback: {feedback['comment']}")
        if feedback.get("tab"):
            parts.append(f"Feedback on: {feedback['tab']} tab")

        return " | ".join(parts) if parts else ""

    def _build_correction_prompt(
        self, quality_report: dict, feedback_context: str
    ) -> str:
        """Build the prompt that tells the architecture agent what to fix."""
        score = quality_report.get("score", 0)
        components = quality_report.get("components", {})

        weakest = sorted(components.items(), key=lambda x: x[1])[:3] if components else []
        weak_areas = ", ".join(f"{k} ({v:.2f})" for k, v in weakest)

        prompt = (
            f"The current output scored {score:.1f}/100. "
            f"Threshold is {self.threshold}. "
            f"Weakest areas: {weak_areas}. "
        )

        if feedback_context:
            prompt += f"User feedback: {feedback_context}. "

        prompt += (
            "Rewrite the architecture plan to address these weaknesses. "
            "Focus on making actions more concrete, reproducible, and detailed. "
            "Keep the core structure but improve specificity and completeness."
        )

        return prompt
