"""
Gemini Video Analyzer - Native Vertex AI URL Context

Uses Google's Gemini model with URL context tool to analyze videos directly.
This bypasses smolagents and uses native Gemini capabilities.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class GeminiVideoAnalyzer:
    """Analyzes video URLs using Gemini's native URL context capability."""

    def __init__(self):
        """Initialize the Gemini client."""
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY required")

        try:
            from google import genai
            from google.genai.types import Tool, GenerateContentConfig, UrlContext

            self.genai = genai
            self.client = genai.Client(api_key=self.api_key)
            self.Tool = Tool
            self.GenerateContentConfig = GenerateContentConfig
            self.UrlContext = UrlContext
            self.available = True
            print("✅ Gemini Video Analyzer initialized with URL context support")
        except ImportError as e:
            self.available = False
            print(f"⚠️ Gemini SDK not available: {e}")

    def analyze_video_url(
        self, video_url: str, prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a video URL using Gemini with URL context.

        Args:
            video_url: YouTube or other video URL
            prompt: Custom analysis prompt (optional)

        Returns:
            Dict with analysis results
        """
        if not self.available:
            return {
                "success": False,
                "error": "Gemini SDK not available",
                "result": None,
            }

        default_prompt = f"""Analyze this video and provide:
1. A concise summary (2-3 sentences)
2. Key topics covered (bullet list)
3. Action items or takeaways
4. Any code examples or technical content shown

Video URL: {video_url}"""

        analysis_prompt = prompt or default_prompt

        try:
            # Use URL context tool for direct URL analysis
            url_context_tool = self.Tool(url_context=self.UrlContext())

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=analysis_prompt,
                config=self.GenerateContentConfig(
                    tools=[url_context_tool],
                    response_modalities=["TEXT"],
                ),
            )

            # Extract response text
            result_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text"):
                    result_text += part.text

            # Get URL context metadata if available
            url_metadata = None
            if hasattr(response.candidates[0], "url_context_metadata"):
                url_metadata = response.candidates[0].url_context_metadata

            return {
                "success": True,
                "result": result_text,
                "url_context_metadata": url_metadata,
                "model": "gemini-2.5-flash",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "result": None}

    def analyze_with_instructions(self, video_url: str, task: str) -> Dict[str, Any]:
        """
        Analyze video with specific task instructions.

        Args:
            video_url: Video URL to analyze
            task: Specific task/question about the video

        Returns:
            Analysis result
        """
        prompt = f"""Based on this video: {video_url}

Task: {task}

Provide a detailed response with:
- Direct answers to the task
- Relevant timestamps if applicable
- Code snippets if the video contains code
- Actionable insights"""

        return self.analyze_video_url(video_url, prompt)


# Singleton instance
_analyzer = None


def get_gemini_video_analyzer() -> GeminiVideoAnalyzer:
    """Get or create the Gemini video analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = GeminiVideoAnalyzer()
    return _analyzer


# Quick test
if __name__ == "__main__":
    analyzer = get_gemini_video_analyzer()
    if analyzer.available:
        result = analyzer.analyze_video_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        print(f"Result: {result}")
    else:
        print("Analyzer not available")
