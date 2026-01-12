"""
Dogfooding Pipeline - Self-Enhancement Through Video Intelligence

This module implements the closed-loop dogfooding pattern:
1. Analyze a video (tutorial, demo, etc.)
2. Extract actionable insights and code patterns
3. Generate improvement suggestions for UVAI itself
4. Optionally apply patches to the codebase

The pipeline uses UVAI to improve UVAI.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import our video analyzer
try:
    from gemini_video_analyzer import get_gemini_video_analyzer, GeminiVideoAnalyzer

    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

# Import memory for lesson recording
try:
    from memory import record_lesson, get_lessons

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


class DogfoodingPipeline:
    """
    Self-enhancement pipeline that uses video intelligence to improve UVAI.

    Flow:
    Video URL → Analysis → Extract Actions → Generate Code → Apply/Suggest
    """

    def __init__(self):
        """Initialize the dogfooding pipeline."""
        self.analyzer: Optional[GeminiVideoAnalyzer] = None
        if ANALYZER_AVAILABLE:
            self.analyzer = get_gemini_video_analyzer()

        # Target codebase paths
        self.target_paths = {
            "frontend": os.path.join(
                os.path.dirname(__file__), "..", "apps", "web", "src"
            ),
            "backend": os.path.dirname(__file__),
            "shared": os.path.join(os.path.dirname(__file__), "..", "shared"),
        }

        # Enhancement history
        self.enhancements: List[Dict[str, Any]] = []

    def analyze_for_improvements(
        self, video_url: str, target_component: str = "frontend"
    ) -> Dict[str, Any]:
        """
        Analyze a video and extract improvement suggestions for UVAI.

        Args:
            video_url: URL of tutorial/demo video
            target_component: Which part of UVAI to improve (frontend, backend, shared)

        Returns:
            Dict with analysis, suggestions, and generated code
        """
        if not self.analyzer or not self.analyzer.available:
            return {
                "success": False,
                "error": "Video analyzer not available",
            }

        # Step 1: Analyze video with improvement-focused prompt
        prompt = f"""Analyze this video and extract actionable improvements for a video intelligence SaaS platform.

The platform has these components:
- Frontend: Next.js/React dashboard for video analysis
- Backend: FastAPI with multi-model AI routing
- Video Processing: Gemini URL context for video understanding

Extract:
1. UI/UX improvements that could be applied
2. Code patterns or techniques shown
3. Architecture suggestions
4. Specific actionable items with code examples

Focus on {target_component} improvements.
Format the code examples as JSON with 'file', 'description', and 'code' fields.

Video URL: {video_url}"""

        result = self.analyzer.analyze_video_url(video_url, prompt)

        if not result.get("success"):
            return result

        # Step 2: Parse the analysis for actionable items
        analysis_text = result.get("result", "")
        suggestions = self._extract_suggestions(analysis_text)

        # Step 3: Generate code patches from suggestions
        code_patches = self._generate_patches(suggestions, target_component)

        # Step 4: Record as a lesson
        if MEMORY_AVAILABLE:
            record_lesson(
                f"Dogfooding analysis: {len(suggestions)} improvements found from {video_url[:50]}",
                {
                    "video_url": video_url,
                    "target": target_component,
                    "suggestion_count": len(suggestions),
                    "patch_count": len(code_patches),
                },
            )

        enhancement = {
            "success": True,
            "video_url": video_url,
            "target_component": target_component,
            "analysis": analysis_text,
            "suggestions": suggestions,
            "code_patches": code_patches,
            "timestamp": datetime.now().isoformat(),
        }

        self.enhancements.append(enhancement)
        return enhancement

    def _extract_suggestions(self, analysis: str) -> List[Dict[str, Any]]:
        """Extract structured suggestions from analysis text."""
        suggestions = []

        # Look for numbered items or bullet points
        lines = analysis.split("\n")
        current_suggestion = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for numbered items
            if any(
                line.startswith(f"{i}.") or line.startswith(f"{i})")
                for i in range(1, 20)
            ):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {
                    "title": line.split(".", 1)[-1].split(")", 1)[-1].strip(),
                    "details": [],
                    "priority": "medium",
                }
            elif line.startswith("-") or line.startswith("*"):
                if current_suggestion:
                    current_suggestion["details"].append(line[1:].strip())
                else:
                    suggestions.append(
                        {
                            "title": line[1:].strip(),
                            "details": [],
                            "priority": "medium",
                        }
                    )

        if current_suggestion:
            suggestions.append(current_suggestion)

        # Assign priorities based on keywords
        high_priority_keywords = ["critical", "must", "essential", "important", "key"]
        for suggestion in suggestions:
            title_lower = suggestion["title"].lower()
            if any(kw in title_lower for kw in high_priority_keywords):
                suggestion["priority"] = "high"

        return suggestions

    def _generate_patches(
        self, suggestions: List[Dict[str, Any]], target_component: str
    ) -> List[Dict[str, Any]]:
        """Generate code patches from suggestions."""
        patches = []

        for suggestion in suggestions:
            # For now, create patch templates
            # In full implementation, this would use Gemini to generate actual code
            patch = {
                "suggestion": suggestion["title"],
                "target": target_component,
                "status": "pending_generation",
                "code": None,
                "file_path": None,
            }

            # Try to infer target file from suggestion
            title_lower = suggestion["title"].lower()
            if "dashboard" in title_lower:
                patch["file_path"] = "apps/web/src/app/dashboard/page.tsx"
            elif "landing" in title_lower or "home" in title_lower:
                patch["file_path"] = "apps/web/src/app/page.tsx"
            elif "api" in title_lower or "endpoint" in title_lower:
                patch["file_path"] = "prescient-twin/main.py"
            elif "animation" in title_lower or "ui" in title_lower:
                patch["file_path"] = "apps/web/src/app/globals.css"

            patches.append(patch)

        return patches

    def apply_enhancement(
        self, enhancement_index: int, patch_index: int
    ) -> Dict[str, Any]:
        """Apply a specific code patch from an enhancement."""
        if enhancement_index >= len(self.enhancements):
            return {"success": False, "error": "Enhancement not found"}

        enhancement = self.enhancements[enhancement_index]
        patches = enhancement.get("code_patches", [])

        if patch_index >= len(patches):
            return {"success": False, "error": "Patch not found"}

        patch = patches[patch_index]

        # For safety, we don't auto-apply - just mark as suggested
        patch["status"] = "suggested"

        return {
            "success": True,
            "patch": patch,
            "message": "Patch marked for review. Manual application recommended.",
        }

    def get_enhancement_summary(self) -> Dict[str, Any]:
        """Get summary of all enhancements."""
        return {
            "total_enhancements": len(self.enhancements),
            "total_suggestions": sum(
                len(e.get("suggestions", [])) for e in self.enhancements
            ),
            "total_patches": sum(
                len(e.get("code_patches", [])) for e in self.enhancements
            ),
            "recent": self.enhancements[-5:] if self.enhancements else [],
        }

    def run_self_improvement_cycle(self, video_urls: List[str]) -> Dict[str, Any]:
        """
        Run a full self-improvement cycle on multiple videos.

        This is the core dogfooding loop:
        1. Analyze each video
        2. Aggregate suggestions
        3. Prioritize improvements
        4. Generate implementation plan
        """
        all_suggestions = []
        all_patches = []

        for url in video_urls:
            result = self.analyze_for_improvements(url)
            if result.get("success"):
                all_suggestions.extend(result.get("suggestions", []))
                all_patches.extend(result.get("code_patches", []))

        # Prioritize
        high_priority = [s for s in all_suggestions if s.get("priority") == "high"]

        return {
            "videos_analyzed": len(video_urls),
            "total_suggestions": len(all_suggestions),
            "high_priority": len(high_priority),
            "patches_generated": len(all_patches),
            "top_suggestions": (
                high_priority[:5] if high_priority else all_suggestions[:5]
            ),
        }


# Singleton instance
_pipeline = None


def get_dogfooding_pipeline() -> DogfoodingPipeline:
    """Get or create the dogfooding pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DogfoodingPipeline()
    return _pipeline


# Quick test
if __name__ == "__main__":
    print("🐕 Dogfooding Pipeline Test")
    pipeline = get_dogfooding_pipeline()

    if pipeline.analyzer and pipeline.analyzer.available:
        print("✅ Analyzer available")

        # Test with a video
        test_url = "https://www.youtube.com/watch?v=jSWuepkuFrU"
        print(f"\n📹 Analyzing: {test_url}")

        result = pipeline.analyze_for_improvements(test_url, "frontend")

        if result.get("success"):
            print(f"✅ Found {len(result.get('suggestions', []))} suggestions")
            print(f"✅ Generated {len(result.get('code_patches', []))} patches")
            for i, s in enumerate(result.get("suggestions", [])[:3]):
                print(f"   {i+1}. {s['title'][:60]}...")
        else:
            print(f"❌ Error: {result.get('error')}")
    else:
        print("❌ Analyzer not available")
