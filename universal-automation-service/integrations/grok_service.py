import os
import sys
import json
from typing import Dict, Any, Optional

# Add the directory containing grok_client.py to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from grok_client import GrokClient, GrokModel
except ImportError:
    # Fallback for when running from different contexts
    from .grok_client import GrokClient, GrokModel

class GrokService:
    """
    Service adapter for xAI Grok interactions, specifically focused on 
    Video Analysis and "Analysis Agent" roles.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        if not self.api_key:
            print("⚠️ GrokService initialized without API Key. Interactions will fail.")
        
        # Default to the most capable model for reasoning
        self.model = GrokModel.GROK_4_0709 if hasattr(GrokModel, 'GROK_4_0709') else "grok-4-0709"

    def process_video_context(self, video_metadata: Dict[str, Any], transcript: str) -> Dict[str, Any]:
        """
        Analyze video context (metadata + transcript) using Grok.
        This fulfills the "Read Everything" and "Map Relationships" capabilities 
        by synthesizing text data.
        """
        if not self.api_key:
            return {"error": "No API Key configured"}

        prompt = f"""
        You are an advanced Video Analysis Agent.
        
        Video Title: {video_metadata.get('title', 'Unknown')}
        Duration: {video_metadata.get('duration', 'Unknown')}
        
        Transcript Excerpt:
        {transcript[:15000]} # Limit context window if needed
        
        Task:
        1. Identify the core intent (e.g., Tutorial, Demo, Lecture).
        2. Extract key entities and tools mentioned.
        3. Break down the content into logical steps or chapters.
        4. Assess validity/confidence of the information.
        
        Return JSON format.
        """

        try:
            with GrokClient(api_key=self.api_key, model=self.model) as client:
                response = client.chat(
                    messages=[
                        {"role": "system", "content": "You are a precise JSON-outputting analysis engine."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                
                # Attempt to parse JSON from response
                content = response.content
                # Simple cleanup if markdown code blocks are used
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                    
                return {
                    "raw_analysis": response.content,
                    "parsed": json.loads(content) if "{" in content else None,
                    "model_used": self.model
                }
        except Exception as e:
            return {"error": f"Grok analysis failed: {str(e)}"}

    async def agentic_workflow_generation(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an actionable workflow (code or steps) based on analysis.
        Matches the "Generation Agent" role.
        """
        if not self.api_key:
             return {"error": "No API Key"}

        prompt = f"""
        Based on this video analysis:
        {json.dumps(analysis_result.get('parsed', {}), indent=2)}
        
        Generate a comprehensive Implementation Plan (Markdown) and 
        extract any specific Python/Shell code blocks required to replicate the video's outcome.
        """
        
        try:
            with GrokClient(api_key=self.api_key, model="grok-code-fast-1") as client:
                 response = client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4
                )
                 return {"workflow": response.content}
        except Exception as e:
            return {"error": f"Workflow generation failed: {str(e)}"}
