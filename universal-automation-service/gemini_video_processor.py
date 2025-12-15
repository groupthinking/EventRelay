#!/usr/bin/env python3
"""
Gemini API Video Processor
Direct YouTube video understanding using Gemini 2.0 API
"""
import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-genai not installed. Run: pip3 install google-genai")

class GeminiVideoProcessor:
    """Process YouTube videos using Gemini 2.5 API for enhanced understanding"""

    def __init__(self, api_key: Optional[str] = None):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai package not installed")

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash-exp"  # Fast and cost-effective
        self.processing_state = {
            "processor": "gemini-2.0-flash-exp",
            "video_url": None,
            "analysis": {},
            "timestamp": datetime.now().isoformat()
        }

    def process_video(self, youtube_url: str) -> Dict[str, Any]:
        """
        Process YouTube video with Gemini API
        Returns comprehensive video analysis in EventRelay-compatible format
        """
        self.processing_state["video_url"] = youtube_url

        # Define comprehensive analysis prompts
        prompts = {
            "summary": "Summarize this video in 3-5 detailed sentences. Focus on the main topic, key points covered, and intended audience.",

            "transcript": "Provide a complete transcript of the spoken content with approximate timestamps. Format: [MM:SS] Speaker text",

            "topics": "List all main topics and subtopics covered in this video. Format as a bulleted list with brief descriptions.",

            "key_concepts": "Extract 8-10 key concepts, learnings, or takeaways from this video. Include actionable insights.",

            "automation_opportunities": "Identify any processes, workflows, or tasks shown in this video that could be automated. For each, describe: 1) The task/process, 2) How it could be automated, 3) Potential tools/technologies needed.",

            "visual_analysis": "Describe the key visual elements shown in the video: 1) On-screen demonstrations, 2) Code snippets or commands shown, 3) UI/UX interactions, 4) Diagrams or visual aids used.",

            "code_extraction": "If any code, commands, or technical syntax is shown in the video, extract it verbatim. Include the language/technology and context.",

            "step_by_step": "If the video is a tutorial or how-to guide, extract the step-by-step procedure shown. Number each step clearly.",

            "sentiment": "Analyze the overall tone and sentiment of the video. Is it educational, entertaining, promotional, technical? Rate engagement level (1-10).",

            "skills_suggested": "Based on this video's content, suggest 3-5 Claude Code skills that could be created to automate or assist with the topics covered."
        }

        results = {}
        for idx, (task, prompt) in enumerate(prompts.items()):
            try:
                print(f"[Gemini] Processing: {task}...")
                response = self.client.models.generate_content(
                    model=f'models/{self.model}',
                    contents=types.Content(
                        parts=[
                            types.Part(
                                file_data=types.FileData(file_uri=youtube_url)
                            ),
                            types.Part(text=prompt)
                        ]
                    )
                )
                results[task] = response.text
                print(f"[Gemini] ✓ Completed: {task}")

                # Add delay between requests to avoid rate limits (15 RPM = 4 sec between)
                if idx < len(prompts) - 1:  # Don't wait after last prompt
                    time.sleep(5)  # 5 second delay = 12 requests per minute (well under 15 RPM limit)

            except Exception as e:
                print(f"[Gemini] ✗ Error in {task}: {str(e)}")
                results[task] = f"Error: {str(e)}"
                # Still wait even on error to respect rate limits
                if idx < len(prompts) - 1:
                    time.sleep(5)

        self.processing_state["analysis"] = results

        # Convert to EventRelay-compatible format
        return self._convert_to_eventrelay_format(youtube_url, results)

    def _convert_to_eventrelay_format(self, youtube_url: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Gemini analysis to EventRelay-compatible format"""

        # Extract video ID
        video_id = self._extract_video_id(youtube_url)

        # Build EventRelay-compatible structure
        eventrelay_format = {
            "video_id": video_id,
            "metadata": {
                "video_id": video_id,
                "url": youtube_url,
                "processor": "gemini-2.5-flash",
                "title": self._extract_title(analysis.get("summary", "")),
                "description": analysis.get("summary", ""),
                "source": "gemini_api"
            },
            "transcript": {
                "text": analysis.get("transcript", ""),
                "segments": self._parse_transcript_segments(analysis.get("transcript", "")),
                "source": "gemini_api"
            },
            "analysis": {
                "sentiment": self._extract_sentiment(analysis.get("sentiment", "")),
                "topics": self._parse_topics(analysis.get("topics", "")),
                "key_concepts": self._parse_key_concepts(analysis.get("key_concepts", "")),
                "visual_elements": analysis.get("visual_analysis", ""),
                "code_snippets": analysis.get("code_extraction", ""),
                "source": "gemini_api"
            },
            "learning_data": {
                "patterns": self._extract_patterns(analysis),
                "key_concepts": self._parse_key_concepts(analysis.get("key_concepts", "")),
                "automation_opportunities": self._parse_automation_opps(analysis.get("automation_opportunities", "")),
                "step_by_step": analysis.get("step_by_step", ""),
                "skills_suggested": self._parse_skills(analysis.get("skills_suggested", "")),
                "sentiment_trends": [self._extract_sentiment(analysis.get("sentiment", ""))],
                "transcript_length": len(analysis.get("transcript", "")),
                "source": "gemini_api"
            },
            "gemini_raw": analysis,  # Preserve full Gemini output
            "status": "completed"
        }

        return eventrelay_format

    def _extract_video_id(self, youtube_url: str) -> str:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        return "unknown"

    def _extract_title(self, summary: str) -> str:
        """Extract likely title from summary (first sentence)"""
        if not summary:
            return "Unknown"
        return summary.split('.')[0][:100]

    def _extract_sentiment(self, sentiment_text: str) -> str:
        """Extract sentiment from analysis text"""
        sentiment_text_lower = sentiment_text.lower()
        if "positive" in sentiment_text_lower or "engaging" in sentiment_text_lower:
            return "positive"
        elif "negative" in sentiment_text_lower or "critical" in sentiment_text_lower:
            return "negative"
        return "neutral"

    def _parse_topics(self, topics_text: str) -> list:
        """Parse topics from text into list"""
        if not topics_text or "Error:" in topics_text:
            return []
        # Split by bullet points or newlines
        lines = topics_text.split('\n')
        topics = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                topic = line.lstrip('-*• ').strip()
                if topic:
                    topics.append(topic)
        return topics[:10]  # Top 10 topics

    def _parse_key_concepts(self, concepts_text: str) -> list:
        """Parse key concepts into list"""
        if not concepts_text or "Error:" in concepts_text:
            return []
        lines = concepts_text.split('\n')
        concepts = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line.startswith('•') or line[0].isdigit()):
                concept = line.lstrip('-*•0123456789. ').strip()
                if concept:
                    concepts.append(concept)
        return concepts[:10]

    def _parse_automation_opps(self, automation_text: str) -> list:
        """Parse automation opportunities"""
        if not automation_text or "Error:" in automation_text:
            return []
        return self._parse_key_concepts(automation_text)  # Same parsing logic

    def _parse_skills(self, skills_text: str) -> list:
        """Parse suggested skills"""
        if not skills_text or "Error:" in skills_text:
            return []
        return self._parse_key_concepts(skills_text)  # Same parsing logic

    def _parse_transcript_segments(self, transcript_text: str) -> list:
        """Parse transcript into segments with timestamps"""
        if not transcript_text or "Error:" in transcript_text:
            return []

        segments = []
        lines = transcript_text.split('\n')
        for line in lines:
            line = line.strip()
            if '[' in line and ']' in line:
                # Try to extract [MM:SS] timestamp
                parts = line.split(']', 1)
                if len(parts) == 2:
                    timestamp = parts[0].strip('[')
                    text = parts[1].strip()
                    segments.append({
                        "timestamp": timestamp,
                        "text": text
                    })

        return segments[:100]  # Limit segments

    def _extract_patterns(self, analysis: Dict[str, Any]) -> list:
        """Extract patterns from full analysis"""
        patterns = []

        # Pattern 1: Automation opportunities
        if "automation_opportunities" in analysis:
            patterns.append({
                "type": "automation",
                "data": analysis["automation_opportunities"][:500]
            })

        # Pattern 2: Step-by-step procedures
        if "step_by_step" in analysis and "Error:" not in analysis["step_by_step"]:
            patterns.append({
                "type": "procedure",
                "data": analysis["step_by_step"][:500]
            })

        # Pattern 3: Code patterns
        if "code_extraction" in analysis and "Error:" not in analysis["code_extraction"]:
            patterns.append({
                "type": "code",
                "data": analysis["code_extraction"][:500]
            })

        return patterns

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 gemini_video_processor.py <youtube_url>")
        sys.exit(1)

    # Use provided API key
    api_key = "AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"
    youtube_url = sys.argv[1]

    processor = GeminiVideoProcessor(api_key=api_key)
    result = processor.process_video(youtube_url)

    print("\n" + "="*80)
    print("GEMINI VIDEO PROCESSING RESULTS")
    print("="*80)
    print(json.dumps(result, indent=2))
