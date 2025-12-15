#!/usr/bin/env python3
"""
Real Video Processor for UVAI Video-to-Software Pipeline
========================================================

This module provides real video processing capabilities for the UVAI platform,
replacing mock implementations with actual video analysis and processing.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Path setup
uvai_root = Path(__file__).parent.parent.parent.parent

try:
    from src.mcp.mcp_video_processor import MCPVideoProcessor
    from src.adapters.multi_modal_engine.engine import VideoToSystemEngine
    from src.core.youtube_extension.backend.ai_insights_processor import get_ai_insights
except (ImportError, AttributeError) as e:
    logging.warning(f"Import error in real_video_processor: {e}")
    MCPVideoProcessor = None
    VideoToSystemEngine = None
    get_ai_insights = None

logger = logging.getLogger(__name__)

class RealVideoProcessor:
    """
    Real video processor that integrates existing UVAI components
    for actual video-to-software processing
    """
    
    def __init__(self):
        self.mcp_processor = None
        self.engine = None
        
        # Initialize components if available
        if MCPVideoProcessor:
            try:
                self.mcp_processor = MCPVideoProcessor()
                logger.info("✅ MCP Video Processor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP processor: {e}")
        
        if VideoToSystemEngine:
            try:
                self.engine = VideoToSystemEngine()
                logger.info("✅ Video-to-System Engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize video engine: {e}")
    
    async def process_video(self, video_url: str) -> Dict[str, Any]:
        """
        Process a YouTube video and extract comprehensive information
        for software generation
        """
        logger.info(f"🎥 Processing video: {video_url}")
        
        try:
            # Step 1: Extract basic video information and transcript
            video_data = await self._extract_video_data(video_url)
            
            # Step 2: Get AI insights if available
            ai_insights = await self._get_ai_insights(video_url)
            
            # Step 3: Process with MCP if available
            mcp_result = None
            if self.mcp_processor:
                try:
                    mcp_result = await self.mcp_processor.process_video_mcp(
                        video_url, 
                        ai_insights=ai_insights
                    )
                except Exception as e:
                    logger.warning(f"MCP processing failed: {e}")
            
            # Step 4: Combine results
            result = self._combine_results(video_data, ai_insights, mcp_result)
            
            logger.info(f"✅ Video processing complete for {video_url}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Video processing failed: {e}")
            raise
    
    async def _extract_video_data(self, video_url: str) -> Dict[str, Any]:
        """Extract basic video data including transcript"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            import re
            
            # Extract video ID
            video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
            if not video_id_match:
                raise ValueError(f"Invalid YouTube URL: {video_url}")
            
            video_id = video_id_match.group(1)
            
            # Get transcript
            try:
                yt_api = YouTubeTranscriptApi()
                transcript = yt_api.fetch(video_id)
                transcript_text = " ".join([entry['text'] for entry in transcript])
            except Exception as e:
                logger.warning(f"Failed to get transcript: {e}")
                transcript = []
                transcript_text = ""
            
            return {
                "video_id": video_id,
                "video_url": video_url,
                "transcript": transcript,
                "transcript_text": transcript_text,
                "title": self._extract_title_from_transcript(transcript_text),
                "duration": len(transcript) * 5 if transcript else 0,  # Rough estimate
                "language": "en",  # Default
                "processing_timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract video data: {e}")
            return {
                "video_id": "unknown",
                "video_url": video_url,
                "transcript": [],
                "transcript_text": "",
                "title": "Unknown Video",
                "duration": 0,
                "error": str(e)
            }
    
    async def _get_ai_insights(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get AI insights from video if available"""
        try:
            if get_ai_insights:
                return await get_ai_insights(video_url)
            else:
                logger.info("AI insights not available")
                return None
        except Exception as e:
            logger.warning(f"Failed to get AI insights: {e}")
            return None
    
    def _extract_title_from_transcript(self, transcript_text: str) -> str:
        """Extract a title from transcript text"""
        if not transcript_text:
            return "Untitled Video"
        
        # Get first sentence or first 50 characters
        sentences = transcript_text.split('.')
        if sentences:
            title = sentences[0].strip()
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        
        return transcript_text[:50] + "..." if len(transcript_text) > 50 else transcript_text
    
    def _combine_results(self, video_data: Dict, ai_insights: Optional[Dict], mcp_result: Optional[Dict]) -> Dict[str, Any]:
        """Combine all processing results into a unified response"""
        result = {
            "status": "success",
            "video_data": video_data,
            "processing_pipeline": []
        }
        
        # Add basic video data
        result["processing_pipeline"].append({
            "stage": "video_extraction",
            "status": "completed",
            "data": video_data
        })
        
        # Add AI insights if available
        if ai_insights:
            result["ai_insights"] = ai_insights
            result["processing_pipeline"].append({
                "stage": "ai_insights",
                "status": "completed",
                "data": ai_insights
            })
        
        # Add MCP results if available
        if mcp_result:
            result["mcp_analysis"] = mcp_result
            result["processing_pipeline"].append({
                "stage": "mcp_processing",
                "status": "completed",
                "data": mcp_result
            })
        
        # Extract key information for software generation
        result["extracted_info"] = self._extract_software_info(video_data, ai_insights, mcp_result)
        
        return result
    
    def _extract_software_info(self, video_data: Dict, ai_insights: Optional[Dict], mcp_result: Optional[Dict]) -> Dict[str, Any]:
        """Extract software-relevant information from processed video data"""
        transcript_text = video_data.get("transcript_text", "").lower()
        
        # Detect technologies mentioned
        technologies = self._detect_technologies(transcript_text)
        
        # Detect project type
        project_type = self._detect_project_type(transcript_text, technologies)
        
        # Extract features mentioned
        features = self._extract_features(transcript_text)
        
        # Determine complexity level
        complexity = self._assess_complexity(transcript_text, len(video_data.get("transcript", [])))
        
        return {
            "technologies": technologies,
            "project_type": project_type,
            "features": features,
            "complexity": complexity,
            "title": video_data.get("title", "Unknown Project"),
            "estimated_duration": video_data.get("duration", 0),
            "has_code_examples": "code" in transcript_text or "function" in transcript_text,
            "has_ui_elements": any(ui_term in transcript_text for ui_term in ["button", "form", "component", "interface"]),
            "tutorial_steps": self._extract_tutorial_steps(video_data.get("transcript", []))
        }
    
    def _detect_technologies(self, text: str) -> List[str]:
        """Detect mentioned technologies in the transcript"""
        tech_keywords = {
            "react": ["react", "jsx", "component", "useState", "useEffect"],
            "javascript": ["javascript", "js", "function", "var", "const", "let"],
            "python": ["python", "def", "import", "pip", "django", "flask"],
            "html": ["html", "div", "span", "element", "tag"],
            "css": ["css", "style", "flex", "grid", "bootstrap"],
            "typescript": ["typescript", "interface", "type"],
            "vue": ["vue", "vuejs", "vue.js"],
            "angular": ["angular", "ng-", "component"],
            "nodejs": ["node", "npm", "express", "server"],
            "nextjs": ["next", "next.js", "nextjs"],
            "tailwind": ["tailwind", "tailwindcss"]
        }
        
        detected = []
        for tech, keywords in tech_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected.append(tech)
        
        return detected if detected else ["javascript", "html", "css"]  # Default web stack
    
    def _detect_project_type(self, text: str, technologies: List[str]) -> str:
        """Detect the type of project being demonstrated"""
        if any(term in text for term in ["website", "web app", "frontend", "ui"]):
            return "web"
        elif any(term in text for term in ["api", "backend", "server", "database"]):
            return "api"
        elif any(term in text for term in ["mobile", "app", "android", "ios"]):
            return "mobile"
        elif any(term in text for term in ["desktop", "electron", "tkinter"]):
            return "desktop"
        elif "python" in technologies and any(term in text for term in ["script", "automation"]):
            return "script"
        else:
            return "web"  # Default
    
    def _extract_features(self, text: str) -> List[str]:
        """Extract mentioned features from the transcript"""
        feature_keywords = {
            "authentication": ["login", "auth", "signup", "password"],
            "database": ["database", "data", "store", "save"],
            "responsive_design": ["responsive", "mobile", "tablet"],
            "api_integration": ["api", "fetch", "request", "endpoint"],
            "user_interface": ["ui", "interface", "button", "form"],
            "real_time": ["real time", "live", "socket"],
            "payment": ["payment", "checkout", "stripe", "paypal"],
            "search": ["search", "filter", "find"],
            "dashboard": ["dashboard", "admin", "panel"],
            "chat": ["chat", "message", "communication"]
        }
        
        detected_features = []
        for feature, keywords in feature_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_features.append(feature)
        
        return detected_features if detected_features else ["responsive_design", "user_interface"]
    
    def _assess_complexity(self, text: str, transcript_length: int) -> str:
        """Assess the complexity of the project based on content"""
        complexity_indicators = [
            "advanced", "complex", "enterprise", "scalable", 
            "architecture", "patterns", "optimization"
        ]
        
        if transcript_length > 500:  # Long video
            return "high"
        elif any(indicator in text for indicator in complexity_indicators):
            return "high"
        elif transcript_length > 200:
            return "medium"
        else:
            return "low"
    
    def _extract_tutorial_steps(self, transcript: List[Dict]) -> List[str]:
        """Extract tutorial steps from transcript segments"""
        steps = []
        step_indicators = ["first", "next", "then", "now", "step", "let's", "we'll"]
        
        for entry in transcript:
            text = entry.get('text', '').lower()
            if any(indicator in text for indicator in step_indicators):
                steps.append(entry.get('text', '').strip())
        
        return steps[:10]  # Limit to first 10 steps

# Initialize global processor instance
_video_processor = None

def get_video_processor() -> RealVideoProcessor:
    """Get or create the global video processor instance"""
    global _video_processor
    if _video_processor is None:
        _video_processor = RealVideoProcessor()
    return _video_processor