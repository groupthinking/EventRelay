#!/usr/bin/env python3
"""
LLAMA 3.1 8B BACKGROUND AGENT
High-performance local inference agent for continuous video processing and quality assessment

This agent runs locally using Llama 3.1 8B Instruct model, providing:
- Continuous video content analysis
- Quality assessment and scoring
- Action generation and validation
- Learning from processed videos
- MCP tool integration for external data sources
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# Llama and optional embeddings dependencies
try:
    from llama_cpp import Llama
    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False
    Llama = None

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None

# Local imports
try:
    from .specialized.quality_agent import QualityAgent
    from .action_implementer import ActionImplementer
    from .observability_setup import UVAIObservability
except ImportError:
    # Fallback for direct execution
    QualityAgent = None
    ActionImplementer = None
    UVAIObservability = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [LLAMA-AGENT] %(message)s'
)
logger = logging.getLogger("llama_background_agent")


@dataclass
class VideoAnalysisResult:
    """Result of video analysis by Llama agent"""
    video_id: str
    content_category: str
    confidence_score: float
    key_topics: List[str]
    action_items: List[Dict[str, Any]]
    quality_score: float
    processing_time: float
    model_used: str
    timestamp: str


@dataclass
class LearningInsight:
    """Insight learned from video processing"""
    insight_type: str
    description: str
    confidence: float
    applicable_videos: List[str]
    timestamp: str


class LlamaBackgroundAgent:
    """Background agent using Llama 3.1 8B for continuous video processing"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._get_default_model_path()
        self.llm = None
        self.embedding_model = None
        self.quality_agent = QualityAgent() if QualityAgent else None
        self.action_implementer = ActionImplementer() if ActionImplementer else None
        self.observability = UVAIObservability() if UVAIObservability else None
        
        # Performance tracking
        self.total_videos_processed = 0
        self.average_processing_time = 0.0
        self.learning_insights = []
        
        # MCP tool registry
        self.mcp_tools = {}
        
        logger.info(f"🔮 LLAMA BACKGROUND AGENT INITIALIZING with model: {self.model_path}")
    
    def _get_default_model_path(self) -> str:
        """Get default model path from environment or download if needed"""
        model_path = os.getenv("LLAMA_MODEL_PATH")
        if model_path and Path(model_path).exists():
            return model_path
        
        # Default to local models directory
        models_dir = Path("models/llama-3.1-8b-instruct")
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if model exists
        model_file = models_dir / "model.gguf"
        if model_file.exists():
            return str(model_file)
        
        # Download model if not present
        logger.info("Downloading Llama 3.1 8B Instruct model...")
        return self._download_llama_model(models_dir)
    
    def _download_llama_model(self, models_dir: Path) -> str:
        """Download Llama 3.1 8B Instruct model from HuggingFace"""
        try:
            import huggingface_hub
            from huggingface_hub import hf_hub_download
            
            # Optional HuggingFace token from environment
            hf_token = os.getenv("HF_TOKEN")
            
            # Prefer a public model first (no token required)
            model_repos = [
                ("bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"),
                ("bartowski/Llama-3.1-8B-Instruct-GGUF", "Llama-3.1-8B-Instruct.Q4_K_M.gguf"),
                ("TheBloke/Llama-3.1-8B-Instruct-GGUF", "llama-3.1-8b-instruct.Q4_K_M.gguf"),
                ("TheBloke/Llama-3.1-8B-Instruct-GGUF", "llama-3.1-8b-instruct.Q4_0.gguf")
            ]
            
            for repo_id, filename in model_repos:
                try:
                    logger.info(f"Trying to download {filename} from {repo_id}")
                    model_file = hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        local_dir=models_dir,
                        local_dir_use_symlinks=False,
                        token=hf_token
                    )
                    logger.info(f"✅ Model downloaded successfully: {model_file}")
                    return model_file
                except Exception as e:
                    logger.warning(f"Failed to download {filename}: {e}")
                    continue
            
            # If all downloads fail, raise error
            raise Exception("Failed to download any Llama model variants")
            
        except ImportError:
            logger.error("huggingface_hub not available. Please install: pip install huggingface_hub")
            raise
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise
    
    async def initialize(self) -> bool:
        """Initialize the Llama model and embedding model"""
        try:
            if not HAS_LLAMA:
                logger.error("llama-cpp-python not available. Install: pip install llama-cpp-python[server]")
                return False
            
            # Initialize Llama model
            logger.info("Loading Llama 3.1 8B Instruct model...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,  # Context window
                n_threads=os.cpu_count(),  # Use all CPU cores
                n_gpu_layers=0,  # CPU-only for now (can enable GPU if available)
                verbose=False
            )
            
            # Initialize embedding model if available
            if HAS_SENTENCE_TRANSFORMERS:
                logger.info("Loading sentence transformer for embeddings...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            else:
                logger.info("SentenceTransformer not available; proceeding without embeddings")
            
            # Smoke test model with minimal generation; don't gate on specific text
            try:
                _ = self.llm("ok", max_tokens=1, temperature=0.0, stop=["\n"])['choices'][0]['text']
                logger.info("✅ Llama model smoke test passed")
            except Exception as e:
                logger.warning(f"Llama smoke test non-fatal issue: {e}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to initialize Llama agent: {e}")
            return False
    
    async def analyze_video_content(self, transcript: str, metadata: Dict[str, Any]) -> VideoAnalysisResult:
        """Analyze video content using Llama 3.1 8B"""
        start_time = time.time()
        
        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(transcript, metadata)
            
            # Get Llama response
            response = self.llm(
                prompt,
                max_tokens=1024,
                temperature=0.3,
                stop=["\n\n", "User:", "Human:", "Assistant:"]
            )
            
            analysis_text = response['choices'][0]['text'].strip()
            
            # Parse response
            result = self._parse_analysis_response(analysis_text, metadata.get('video_id', 'unknown'))
            
            # Calculate processing time
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            # Update performance metrics
            self._update_performance_metrics(processing_time)
            
            logger.info(f"Video {result.video_id} analyzed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing video content: {e}")
            # Return fallback result
            return VideoAnalysisResult(
                video_id=metadata.get('video_id', 'unknown'),
                content_category='unknown',
                confidence_score=0.0,
                key_topics=[],
                action_items=[],
                quality_score=0.0,
                processing_time=time.time() - start_time,
                model_used='llama-3.1-8b-instruct',
                timestamp=datetime.now().isoformat()
            )
    
    def _create_analysis_prompt(self, transcript: str, metadata: Dict[str, Any]) -> str:
        """Create optimized prompt for Llama analysis"""
        return f"""You are an expert video content analyst. Analyze the following YouTube video transcript and provide structured insights.

VIDEO METADATA:
- Title: {metadata.get('title', 'Unknown')}
- Duration: {metadata.get('duration', 'Unknown')}
- Upload Date: {metadata.get('upload_date', 'Unknown')}

TRANSCRIPT:
{transcript[:3000]}  # Limit transcript length for context

ANALYSIS TASK:
1. Determine the content category (e.g., tutorial, review, discussion, demonstration)
2. Extract 3-5 key topics/themes
3. Generate 2-4 actionable items that viewers could implement
4. Assess content quality and actionability (0-100 scale)

RESPONSE FORMAT (JSON):
{{
    "content_category": "string",
    "confidence_score": 0.95,
    "key_topics": ["topic1", "topic2", "topic3"],
    "action_items": [
        {{
            "type": "implementation",
            "title": "Action title",
            "description": "What to do",
            "difficulty": "easy|medium|hard"
        }}
    ],
    "quality_score": 85
}}

Provide only the JSON response, no additional text."""
    
    def _parse_analysis_response(self, response_text: str, video_id: str) -> VideoAnalysisResult:
        """Parse Llama's analysis response"""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            return VideoAnalysisResult(
                video_id=video_id,
                content_category=data.get('content_category', 'unknown'),
                confidence_score=data.get('confidence_score', 0.0),
                key_topics=data.get('key_topics', []),
                action_items=data.get('action_items', []),
                quality_score=data.get('quality_score', 0.0),
                processing_time=0.0,  # Will be set by caller
                model_used='llama-3.1-8b-instruct',
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            # Return fallback result
            return VideoAnalysisResult(
                video_id=video_id,
                content_category='unknown',
                confidence_score=0.0,
                key_topics=[],
                action_items=[],
                quality_score=0.0,
                processing_time=0.0,
                model_used='llama-3.1-8b-instruct',
                timestamp=datetime.now().isoformat()
            )
    
    async def assess_video_quality(self, analysis_result: VideoAnalysisResult, transcript: str) -> float:
        """Assess video quality using Llama + quality agent"""
        try:
            # Use quality agent if available
            if self.quality_agent and hasattr(self.quality_agent, 'assess_actionability'):
                quality_result = self.quality_agent.assess_actionability(
                    analysis_result.action_items,
                    [{"text": transcript}],
                    {"video_id": analysis_result.video_id}
                )
                return quality_result.get('overall_score', analysis_result.quality_score)
            
            # Fallback to Llama-based assessment
            prompt = f"""Rate the quality and actionability of this video content on a scale of 0-100.

Content Category: {analysis_result.content_category}
Key Topics: {', '.join(analysis_result.key_topics)}
Action Items: {len(analysis_result.action_items)} items

Consider:
- Clarity of instructions
- Practical applicability
- Technical accuracy
- Implementation difficulty

Provide only a number between 0-100:"""
            
            response = self.llm(
                prompt,
                max_tokens=10,
                temperature=0.1,
                stop=["\n", "User:", "Human:", "Assistant:"]
            )
            
            try:
                score = float(response['choices'][0]['text'].strip())
                return max(0, min(100, score))  # Clamp to 0-100
            except ValueError:
                return analysis_result.quality_score
                
        except Exception as e:
            logger.error(f"Error assessing video quality: {e}")
            return analysis_result.quality_score
    
    async def generate_implementation_plan(self, action_items: List[Dict[str, Any]], video_id: str) -> Dict[str, Any]:
        """Generate detailed implementation plan using Llama"""
        try:
            if self.action_implementer:
                return await self.action_implementer.create_implementation_plan(action_items, video_id)
            
            # Fallback Llama-based plan generation
            prompt = f"""Create a detailed implementation plan for the following action items from video {video_id}:

Actions: {json.dumps(action_items, indent=2)}

Generate a structured plan with:
1. Prerequisites
2. Step-by-step implementation
3. Required tools/resources
4. Testing/validation steps
5. Troubleshooting tips

Format as JSON with these sections."""
            
            response = self.llm(
                prompt,
                max_tokens=1024,
                temperature=0.3,
                stop=["\n\n", "User:", "Human:", "Assistant:"]
            )
            
            plan_text = response['choices'][0]['text'].strip()
            
            # Try to parse JSON, fallback to structured text
            try:
                json_start = plan_text.find('{')
                json_end = plan_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    return json.loads(plan_text[json_start:json_end])
            except:
                pass
            
            # Return structured text if JSON parsing fails
            return {
                "video_id": video_id,
                "plan": plan_text,
                "generated_by": "llama-3.1-8b-instruct",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating implementation plan: {e}")
            return {
                "video_id": video_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def learn_from_video(self, analysis_result: VideoAnalysisResult, transcript: str) -> List[LearningInsight]:
        """Extract learning insights from processed video"""
        try:
            prompt = f"""Analyze this video content and extract 2-3 key learning insights that could improve future video processing.

Content: {analysis_result.content_category}
Topics: {', '.join(analysis_result.key_topics)}
Quality Score: {analysis_result.quality_score}

What patterns, techniques, or approaches from this video could be applied to:
1. Better content categorization
2. Improved action generation
3. Enhanced quality assessment
4. More effective implementation planning

Provide insights in this JSON format:
{{
    "insights": [
        {{
            "type": "categorization|action_generation|quality_assessment|implementation",
            "description": "What we learned",
            "confidence": 0.95,
            "applicable_videos": ["similar_category_videos"]
        }}
    ]
}}"""
            
            response = self.llm(
                prompt,
                max_tokens=512,
                temperature=0.4,
                stop=["\n\n", "User:", "Human:", "Assistant:"]
            )
            
            insights_text = response['choices'][0]['text'].strip()
            
            # Parse insights
            try:
                json_start = insights_text.find('{')
                json_end = insights_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    data = json.loads(insights_text[json_start:json_end])
                    insights = []
                    
                    for insight_data in data.get('insights', []):
                        insight = LearningInsight(
                            insight_type=insight_data.get('type', 'general'),
                            description=insight_data.get('description', ''),
                            confidence=insight_data.get('confidence', 0.0),
                            applicable_videos=insight_data.get('applicable_videos', []),
                            timestamp=datetime.now().isoformat()
                        )
                        insights.append(insight)
                    
                    self.learning_insights.extend(insights)
                    return insights
                    
            except Exception as e:
                logger.error(f"Failed to parse learning insights: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error learning from video: {e}")
            return []
    
    def _update_performance_metrics(self, processing_time: float):
        """Update agent performance metrics"""
        self.total_videos_processed += 1
        self.average_processing_time = (
            (self.average_processing_time * (self.total_videos_processed - 1) + processing_time) / 
            self.total_videos_processed
        )
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        return {
            "total_videos_processed": self.total_videos_processed,
            "average_processing_time": self.average_processing_time,
            "model_path": self.model_path,
            "learning_insights_count": len(self.learning_insights),
            "last_updated": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.llm:
            del self.llm
        if self.embedding_model:
            del self.embedding_model
        logger.info("Llama Background Agent shutdown complete")


# MCP Tool Integration
class LlamaAgentMCPTool:
    """MCP tool wrapper for Llama Background Agent"""
    
    def __init__(self, agent: LlamaBackgroundAgent):
        self.agent = agent
    
    async def analyze_video(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool: Analyze video content"""
        result = await self.agent.analyze_video_content(transcript, metadata)
        return {
            "video_id": result.video_id,
            "category": result.content_category,
            "quality_score": result.quality_score,
            "action_items": result.action_items,
            "processing_time": result.processing_time
        }
    
    async def assess_quality(self, actions: List[Dict], transcript: str) -> Dict[str, Any]:
        """MCP tool: Assess video quality"""
        score = await self.agent.assess_video_quality(
            VideoAnalysisResult(
                video_id="mcp_tool",
                content_category="unknown",
                confidence_score=0.0,
                key_topics=[],
                action_items=actions,
                quality_score=0.0,
                processing_time=0.0,
                model_used="llama-3.1-8b-instruct",
                timestamp=datetime.now().isoformat()
            ),
            transcript
        )
        return {"quality_score": score}
    
    async def get_stats(self) -> Dict[str, Any]:
        """MCP tool: Get agent statistics"""
        return await self.agent.get_performance_stats()


# Factory function for easy integration
async def create_llama_background_agent(model_path: Optional[str] = None) -> LlamaBackgroundAgent:
    """Create and initialize a Llama Background Agent"""
    agent = LlamaBackgroundAgent(model_path)
    if await agent.initialize():
        return agent
    else:
        raise RuntimeError("Failed to initialize Llama Background Agent")


if __name__ == "__main__":
    # Test the agent
    async def test():
        try:
            agent = await create_llama_background_agent()
            print("✅ Llama Background Agent initialized successfully!")
            
            # Test analysis
            test_transcript = "This is a tutorial on building a web application using React and Node.js. We'll cover component architecture, state management, and API integration."
            test_metadata = {"video_id": "test123", "title": "React Tutorial", "duration": "15:30"}
            
            result = await agent.analyze_video_content(test_transcript, test_metadata)
            print(f"Analysis result: {result}")
            
            await agent.shutdown()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    asyncio.run(test())
