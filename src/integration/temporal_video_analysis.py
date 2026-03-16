"""
Temporal Video Analysis with Timestamp-based Prompts
----------------------------------------------------
Extends Gemini video analysis with temporal reasoning capabilities.
Supports timestamp-based queries, temporal event extraction, and time-bounded analysis.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .gemini_video import GeminiVideoService, VideoAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class TemporalSegment:
    """Represents a time segment in a video."""
    start_time: str  # Format: "MM:SS" or "HH:MM:SS"
    end_time: str
    description: Optional[str] = None
    
    def to_seconds(self, timestamp: str) -> int:
        """Convert timestamp to seconds."""
        parts = timestamp.split(":")
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    
    @property
    def duration_seconds(self) -> int:
        """Get segment duration in seconds."""
        return self.to_seconds(self.end_time) - self.to_seconds(self.start_time)


@dataclass
class TemporalEvent:
    """Event with precise timestamp information."""
    timestamp: str  # Format: "MM:SS" or "HH:MM:SS"
    event_type: str
    description: str
    confidence: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TemporalAnalysisResult:
    """Result from temporal video analysis."""
    segments: List[TemporalSegment]
    events: List[TemporalEvent]
    summary: str
    timeline: Optional[List[dict]] = None
    metadata: dict = field(default_factory=dict)


class TemporalVideoAnalyzer:
    """
    Temporal video analyzer with timestamp-aware prompting.
    
    Capabilities:
    - Analyze specific time segments
    - Extract timestamped events
    - Temporal reasoning across segments
    - Time-bounded question answering
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.gemini_service = GeminiVideoService(api_key=api_key)
    
    async def analyze_segment(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        focus: Optional[str] = None
    ) -> VideoAnalysisResult:
        """
        Analyze a specific time segment of a video.
        
        Args:
            video_url: YouTube URL or file URI
            start_time: Start timestamp (MM:SS or HH:MM:SS)
            end_time: End timestamp
            focus: Optional focus area (e.g., "code", "speaker", "slides")
        
        Returns:
            Analysis result for the segment
        """
        segment = TemporalSegment(start_time, end_time)
        
        prompt = f"""Analyze this video focusing ONLY on the time segment from {start_time} to {end_time}.
        
        Duration: {segment.duration_seconds} seconds
        {f'Focus area: {focus}' if focus else ''}
        
        Extract and return as JSON:
        {{
            "segment_summary": "What happens in this specific time segment",
            "key_moments": [
                {{"timestamp": "MM:SS", "event": "Description", "importance": "high/medium/low"}}
            ],
            "visual_changes": ["List of visual transitions or changes"],
            "audio_content": "What is said or heard in this segment",
            "technical_details": {{"apis": [], "code": [], "commands": []}}
        }}
        
        Be precise about timestamps within the {start_time}-{end_time} range.
        """
        
        result = await self.gemini_service.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        
        return result
    
    async def extract_temporal_events(
        self,
        video_url: str,
        event_types: Optional[List[str]] = None
    ) -> List[TemporalEvent]:
        """
        Extract timestamped events from the entire video.
        
        Args:
            video_url: YouTube URL or file URI
            event_types: Optional list of event types to focus on
                        (e.g., ["code_change", "api_call", "deployment"])
        
        Returns:
            List of temporal events with precise timestamps
        """
        event_filter = ""
        if event_types:
            event_filter = f"Focus on these event types: {', '.join(event_types)}"
        
        prompt = f"""Watch this entire video and extract ALL significant events with PRECISE timestamps.
        
        {event_filter}
        
        Return as JSON:
        {{
            "events": [
                {{
                    "timestamp": "MM:SS",
                    "type": "event_category",
                    "description": "What happened",
                    "confidence": 0.95,
                    "metadata": {{"additional": "context"}}
                }}
            ],
            "total_duration": "MM:SS",
            "event_summary": "Overall summary of events"
        }}
        
        Requirements:
        - Use exact timestamps (MM:SS or HH:MM:SS)
        - Include confidence score (0.0-1.0)
        - Categorize events by type
        - Capture both visual and audio events
        """
        
        result = await self.gemini_service.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        
        # Parse events from result
        events = []
        try:
            summary_text = result.summary
            if isinstance(summary_text, str):
                # Clean up markdown formatting if present
                if summary_text.strip().startswith("```json"):
                    summary_text = summary_text.strip()[7:]
                elif summary_text.strip().startswith("```"):
                    summary_text = summary_text.strip()[3:]
                if summary_text.strip().endswith("```"):
                    summary_text = summary_text.strip()[:-3]
                
                if summary_text.strip().startswith("{"):
                    data = json.loads(summary_text.strip())
                    for evt in data.get("events", []):
                        events.append(TemporalEvent(
                            timestamp=evt.get("timestamp", "00:00"),
                            event_type=evt.get("type", "unknown"),
                            description=evt.get("description", ""),
                            confidence=evt.get("confidence"),
                            metadata=evt.get("metadata", {})
                        ))
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse JSON from temporal event extraction: {e}")
            logger.debug(f"Failed JSON content: {summary_text}")
            # Fallback: extract from key_events
            for evt in result.key_events:
                events.append(TemporalEvent(
                    timestamp=evt.get("timestamp", "00:00"),
                    event_type="extracted",
                    description=evt.get("event", ""),
                ))
        
        return events
    
    async def temporal_question(
        self,
        video_url: str,
        question: str,
        time_context: Optional[str] = None
    ) -> str:
        """
        Answer a question about the video with temporal context.
        
        Args:
            video_url: YouTube URL or file URI
            question: Question to answer
            time_context: Optional temporal constraint (e.g., "between 2:30 and 5:00")
        
        Returns:
            Answer with timestamps
        """
        time_instruction = f"Focus your answer on the time period: {time_context}" if time_context else ""
        
        prompt = f"""Watch this video and answer the following question.
        
        Question: {question}
        {time_instruction}
        
        Provide your answer with:
        1. Direct answer to the question
        2. Relevant timestamps where evidence is found
        3. Specific visual or audio evidence
        
        Format:
        Answer: [Your answer]
        Evidence at [MM:SS]: [What you see/hear]
        Evidence at [MM:SS]: [What you see/hear]
        """
        
        result = await self.gemini_service.answer_video_question(video_url, prompt)
        return result
    
    async def create_timeline(
        self,
        video_url: str,
        granularity: str = "medium"
    ) -> List[dict]:
        """
        Create a detailed timeline of the video.
        
        Args:
            video_url: YouTube URL or file URI
            granularity: "fine" (every 5s), "medium" (every 30s), "coarse" (major sections)
        
        Returns:
            Timeline with timestamp markers
        """
        interval_descriptions = {
            "fine": "every 5-10 seconds",
            "medium": "every 30-60 seconds",
            "coarse": "at major section boundaries"
        }
        
        prompt = f"""Create a detailed timeline of this video with markers {interval_descriptions[granularity]}.
        
        Return as JSON:
        {{
            "timeline": [
                {{
                    "timestamp": "MM:SS",
                    "section_title": "Section name",
                    "description": "What's happening",
                    "key_visuals": ["visual1", "visual2"],
                    "key_audio": "What's being said"
                }}
            ],
            "total_duration": "MM:SS",
            "section_count": 10
        }}
        
        Create a comprehensive timeline that captures all major moments.
        """
        
        result = await self.gemini_service.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        
        # Parse timeline
        try:
            if isinstance(result.summary, str) and result.summary.strip().startswith("{"):
                data = json.loads(result.summary)
                return data.get("timeline", [])
        except json.JSONDecodeError:
            logger.warning("Could not parse timeline JSON")
        
        return []
    
    async def compare_segments(
        self,
        video_url: str,
        segments: List[Tuple[str, str]],
        comparison_focus: Optional[str] = None
    ) -> dict:
        """
        Compare multiple time segments within a video.
        
        Args:
            video_url: YouTube URL or file URI
            segments: List of (start_time, end_time) tuples
            comparison_focus: What to compare (e.g., "code quality", "speaking style")
        
        Returns:
            Comparison analysis
        """
        segment_strs = [f"{s[0]}-{s[1]}" for s in segments]
        focus_str = f"Compare them in terms of: {comparison_focus}" if comparison_focus else ""
        
        prompt = f"""Watch this video and compare these time segments:
        {chr(10).join(f"{i+1}. {seg}" for i, seg in enumerate(segment_strs))}
        
        {focus_str}
        
        Return as JSON:
        {{
            "segments_analyzed": {len(segments)},
            "comparisons": [
                {{
                    "aspect": "What was compared",
                    "segment_1": "Observation for first segment",
                    "segment_2": "Observation for second segment",
                    "difference": "Key differences"
                }}
            ],
            "overall_assessment": "Summary of comparison"
        }}
        """
        
        result = await self.gemini_service.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        
        try:
            if isinstance(result.summary, str) and result.summary.strip().startswith("{"):
                return json.loads(result.summary)
        except json.JSONDecodeError:
            pass
        
        return {"comparison": result.summary}
    
    async def extract_tutorial_steps(
        self,
        video_url: str
    ) -> List[dict]:
        """
        Extract step-by-step tutorial instructions with timestamps.
        Optimized for instructional/tutorial videos.
        
        Returns:
            List of tutorial steps with timestamps
        """
        prompt = """This appears to be a tutorial or instructional video.
        Extract a step-by-step guide with precise timestamps.
        
        Return as JSON:
        {
            "tutorial_title": "Inferred tutorial title",
            "prerequisites": ["List any prerequisites mentioned"],
            "steps": [
                {
                    "step_number": 1,
                    "timestamp": "MM:SS",
                    "title": "Step title",
                    "instructions": "Detailed instructions",
                    "code_snippets": ["Any code shown"],
                    "expected_result": "What should happen",
                    "common_errors": ["Mentioned errors or warnings"]
                }
            ],
            "total_duration": "MM:SS",
            "difficulty": "beginner/intermediate/advanced"
        }
        
        Be thorough and capture every actionable step.
        """
        
        result = await self.gemini_service.analyze_video(
            video_url,
            prompt,
            media_resolution="high",
            thinking_level="high"
        )
        
        try:
            if isinstance(result.summary, str) and result.summary.strip().startswith("{"):
                data = json.loads(result.summary)
                return data.get("steps", [])
        except json.JSONDecodeError:
            logger.warning("Could not parse tutorial steps")
        
        return []
    
    async def close(self):
        """Clean up resources."""
        await self.gemini_service.close()
