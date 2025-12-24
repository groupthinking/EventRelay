#!/usr/bin/env python3
"""
GROK4 Video Subagent for YouTube Extension
AI-powered video analysis using GROK4 API
"""

import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Grok4VideoSubagent:
    """
    GROK4-powered video analysis subagent
    
    Features:
    - AI-powered content analysis without relying on transcripts
    - IP block resilience through GROK4 API
    - Enhanced actionable content generation
    - MCP integration ready
    """
    
    def __init__(self):
        # API Configuration
        self.grok_api_key = (
            os.getenv('XAI_API_KEY') or 
            os.getenv('GROK_API_KEY') or
            os.getenv('XAI_GROK4_API')
        )
        
        if not self.grok_api_key:
            logger.warning("⚠️ GROK4 API key not found. Set XAI_API_KEY or GROK_API_KEY")
        
        # GROK4 API endpoints
        self.grok_base_url = "https://api.x.ai/v1"
        self.grok_model = "grok-4-0709"
        
        # Session management
        self.session = None
        
        # Output directories
        self.output_dir = Path("grok4_processed_videos")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("🚀 GROK4 Video Subagent initialized")
    
    async def _init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    'Authorization': f'Bearer {self.grok_api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'UVAI-GROK4-Subagent/1.0'
                }
            )
    
    async def _call_grok4_api(self, prompt: str, max_tokens: int = 4000) -> Optional[str]:
        """Call GROK4 API for content analysis"""
        if not self.grok_api_key:
            raise ValueError("GROK4 API key not configured")
        
        await self._init_session()
        
        payload = {
            "model": self.grok_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert video content analyzer. Provide detailed, actionable insights about video content."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            async with self.session.post(
                f"{self.grok_base_url}/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logger.error(f"GROK4 API error {response.status}: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"GROK4 API call failed: {e}")
            return None
    
    def _extract_video_id(self, video_url: str) -> str:
        """Extract YouTube video ID from URL"""
        import re
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, video_url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {video_url}")
    
    async def analyze_video_content(self, video_url: str) -> Dict[str, Any]:
        """
        Analyze video content using GROK4 AI
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"🔍 GROK4 analyzing video: {video_url}")
        
        try:
            video_id = self._extract_video_id(video_url)
            
            # Create comprehensive analysis prompt
            analysis_prompt = f"""
            Analyze this YouTube video: {video_url}
            Video ID: {video_id}
            
            Please provide a comprehensive analysis including:
            
            1. **Content Summary**: What is this video about?
            2. **Key Topics**: Main subjects and concepts discussed
            3. **Technical Details**: Any code, tools, or technical information
            4. **Learning Objectives**: What can viewers learn from this?
            5. **Difficulty Level**: Beginner/Intermediate/Advanced
            6. **Prerequisites**: What should viewers know beforehand?
            7. **Actionable Insights**: Specific steps or actions viewers can take
            8. **Related Resources**: What to explore next
            9. **Industry Context**: How this fits into broader trends
            10. **Implementation Notes**: Practical considerations
            
            Format the response as structured markdown with clear sections.
            Focus on providing actionable, practical insights.
            """
            
            # Get GROK4 analysis
            ai_analysis = await self._call_grok4_api(analysis_prompt)
            
            if not ai_analysis:
                raise RuntimeError("GROK4 analysis failed")
            
            # Generate actionable content
            action_prompt = f"""
            Based on this video analysis:
            {ai_analysis}
            
            Generate a structured action plan with:
            1. **Immediate Actions** (next 24 hours)
            2. **Short-term Goals** (next week)
            3. **Long-term Learning Path** (next month)
            4. **Resources to Gather**
            5. **Skills to Develop**
            6. **Projects to Build**
            
            Make it practical and achievable.
            """
            
            action_plan = await self._call_grok4_api(action_prompt)
            
            # Compile results
            result = {
                'video_id': video_id,
                'video_url': video_url,
                'analysis_timestamp': datetime.now().isoformat(),
                'ai_analysis': ai_analysis,
                'action_plan': action_plan,
                'processing_method': 'grok4_ai_analysis',
                'success': True
            }
            
            # Save results
            await self._save_results(video_id, result)
            
            logger.info(f"✅ GROK4 analysis completed for {video_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ GROK4 analysis failed: {e}")
            return {
                'video_url': video_url,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _save_results(self, video_id: str, results: Dict[str, Any]):
        """Save analysis results to file"""
        try:
            output_file = self.output_dir / f"{video_id}_grok4_analysis.json"
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"💾 Results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    async def process_video_with_grok4(self, video_url: str) -> Dict[str, Any]:
        """
        Main method to process video using GROK4
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Analysis results dictionary
        """
        return await self.analyze_video_content(video_url)
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            logger.info("🔒 GROK4 session closed")

# CLI interface for testing
async def main():
    """CLI interface for testing GROK4 subagent"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python grok4_video_subagent.py <youtube_url>")
        sys.exit(1)
    
    video_url = sys.argv[1]
    
    subagent = Grok4VideoSubagent()
    
    try:
        print(f"🚀 Processing video: {video_url}")
        results = await subagent.process_video_with_grok4(video_url)
        
        if results.get('success'):
            print("\n✅ Analysis completed successfully!")
            print(f"📊 Video ID: {results.get('video_id')}")
            print(f"📝 Analysis saved to: grok4_processed_videos/")
            print("\n🤖 AI Analysis Preview:")
            print("-" * 50)
            analysis = results.get('ai_analysis', '')
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        else:
            print(f"❌ Analysis failed: {results.get('error')}")
            
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        await subagent.close()

if __name__ == "__main__":
    asyncio.run(main())
