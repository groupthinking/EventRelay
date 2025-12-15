#!/usr/bin/env python3
"""
Real AI Processing Service
=========================

Multi-provider AI processing service with OpenAI, Anthropic, and Google Gemini integration.
Provides intelligent video content analysis, summarization, and action generation.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import httpx

# Import our cost monitor
from .api_cost_monitor import cost_monitor, track_api_call, check_rate_limit_decorator

# AI Service Clients
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Configure logging
logger = logging.getLogger(__name__)

class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    AUTO = "auto"

class ProcessingType(Enum):
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    ACTIONS = "actions"
    LEARNING_PATH = "learning_path"
    CATEGORIZATION = "categorization"

@dataclass
class AIProcessingRequest:
    """AI processing request structure"""
    content: str
    processing_type: ProcessingType
    provider: AIProvider = AIProvider.AUTO
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    video_id: Optional[str] = None
    context: Dict[str, Any] = None

@dataclass
class AIProcessingResult:
    """AI processing result structure"""
    provider: str
    model: str
    processing_type: str
    result: Dict[str, Any]
    tokens_used: int
    cost: float
    processing_time: float
    timestamp: str
    success: bool = True
    error_message: Optional[str] = None

class RealAIProcessorService:
    """
    Multi-provider AI processing service
    
    Features:
    - OpenAI GPT-4/GPT-3.5 integration with streaming
    - Anthropic Claude integration with tool use
    - Google Gemini integration with multimodal support
    - Intelligent provider selection and fallbacks
    - Cost-aware processing with optimization
    - Comprehensive error handling and retries
    - Specialized prompts for video content analysis
    """
    
    def __init__(self):
        """Initialize AI processing service"""
        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        
        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Initialize available clients
        self._init_clients()
        
        # Provider preferences for different tasks
        self.provider_preferences = {
            ProcessingType.ANALYSIS: [AIProvider.GEMINI, AIProvider.OPENAI, AIProvider.ANTHROPIC],
            ProcessingType.SUMMARY: [AIProvider.ANTHROPIC, AIProvider.OPENAI, AIProvider.GEMINI],
            ProcessingType.ACTIONS: [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GEMINI],
            ProcessingType.LEARNING_PATH: [AIProvider.ANTHROPIC, AIProvider.GEMINI, AIProvider.OPENAI],
            ProcessingType.CATEGORIZATION: [AIProvider.GEMINI, AIProvider.OPENAI, AIProvider.ANTHROPIC]
        }
        
        # Model configurations
        self.model_configs = {
            AIProvider.OPENAI: {
                'default': 'gpt-4o-mini',
                'models': {
                    'gpt-4o': {'max_tokens': 4096, 'cost_tier': 'high'},
                    'gpt-4o-mini': {'max_tokens': 16384, 'cost_tier': 'low'},
                    'gpt-3.5-turbo': {'max_tokens': 4096, 'cost_tier': 'low'}
                }
            },
            AIProvider.ANTHROPIC: {
                'default': 'claude-3-5-sonnet-20241022',
                'models': {
                    'claude-3-5-sonnet-20241022': {'max_tokens': 8192, 'cost_tier': 'high'},
                    'claude-3-haiku-20240307': {'max_tokens': 4096, 'cost_tier': 'low'}
                }
            },
            AIProvider.GEMINI: {
                'default': 'gemini-1.5-flash',
                'models': {
                    'gemini-1.5-pro': {'max_tokens': 8192, 'cost_tier': 'high'},
                    'gemini-1.5-flash': {'max_tokens': 8192, 'cost_tier': 'low'}
                }
            }
        }
        
        logger.info(f"🤖 AI Processor initialized with providers: {self._get_available_providers()}")
    
    def _init_clients(self):
        """Initialize AI service clients"""
        if HAS_OPENAI and self.openai_api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            
        if HAS_ANTHROPIC and self.anthropic_api_key:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
            
        if HAS_GEMINI and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_client = genai
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available AI providers"""
        providers = []
        if self.openai_client:
            providers.append("openai")
        if self.anthropic_client:
            providers.append("anthropic")
        if self.gemini_client:
            providers.append("gemini")
        return providers
    
    def _select_optimal_provider(self, processing_type: ProcessingType, content_length: int) -> AIProvider:
        """Select optimal AI provider based on task type and content"""
        preferences = self.provider_preferences.get(processing_type, [AIProvider.OPENAI])
        
        # Check which providers are available and select the first preference
        for provider in preferences:
            if provider == AIProvider.OPENAI and self.openai_client:
                return provider
            elif provider == AIProvider.ANTHROPIC and self.anthropic_client:
                return provider
            elif provider == AIProvider.GEMINI and self.gemini_client:
                return provider
        
        # Fallback to any available provider
        available = self._get_available_providers()
        if available:
            return AIProvider(available[0])
        
        raise Exception("No AI providers available")
    
    def _get_processing_prompt(self, processing_type: ProcessingType, content: str, context: Dict = None) -> str:
        """Get specialized prompt for different processing types"""
        
        if processing_type == ProcessingType.ANALYSIS:
            return f"""
Analyze the following video content and provide a comprehensive analysis:

Video Content:
{content}

Please provide analysis in the following JSON structure:
{{
    "main_topics": ["topic1", "topic2", "topic3"],
    "key_concepts": ["concept1", "concept2", "concept3"],
    "learning_objectives": ["objective1", "objective2"],
    "difficulty_level": "beginner|intermediate|advanced",
    "estimated_duration": "X minutes",
    "content_type": "tutorial|educational|entertainment|news|review",
    "target_audience": "audience description",
    "technical_depth": 1-10,
    "practical_examples": ["example1", "example2"],
    "prerequisites": ["prerequisite1", "prerequisite2"],
    "related_topics": ["related1", "related2"]
}}

Focus on educational value and actionable insights.
"""

        elif processing_type == ProcessingType.SUMMARY:
            return f"""
Create a comprehensive summary of this video content:

Video Content:
{content}

Please provide a summary in the following JSON structure:
{{
    "executive_summary": "Brief 2-3 sentence overview",
    "key_points": ["point1", "point2", "point3"],
    "detailed_summary": "Comprehensive paragraph summary",
    "main_takeaways": ["takeaway1", "takeaway2"],
    "action_items": ["action1", "action2"],
    "quotes_highlights": ["important quote 1", "important quote 2"],
    "timeline_breakdown": [
        {{"timestamp": "0:00", "topic": "Introduction"}},
        {{"timestamp": "2:30", "topic": "Main concept"}}
    ]
}}

Focus on clarity and practical value.
"""

        elif processing_type == ProcessingType.ACTIONS:
            return f"""
Generate specific, actionable steps based on this video content:

Video Content:
{content}

Please provide actionable steps in the following JSON structure:
{{
    "immediate_actions": [
        {{"action": "action description", "time_required": "X minutes", "difficulty": "easy|medium|hard"}},
        {{"action": "action description", "time_required": "X minutes", "difficulty": "easy|medium|hard"}}
    ],
    "learning_path": [
        {{"step": 1, "title": "Step title", "description": "What to do", "resources": ["resource1"]}},
        {{"step": 2, "title": "Step title", "description": "What to do", "resources": ["resource1"]}}
    ],
    "practice_exercises": [
        {{"exercise": "exercise description", "expected_outcome": "what you'll learn"}}
    ],
    "tools_needed": ["tool1", "tool2"],
    "estimated_completion_time": "X hours/days",
    "success_metrics": ["how to measure success"],
    "common_pitfalls": ["pitfall1", "how to avoid it"]
}}

Focus on specific, measurable, achievable actions.
"""

        elif processing_type == ProcessingType.LEARNING_PATH:
            return f"""
Create a personalized learning path based on this video content:

Video Content:
{content}

Please provide a learning path in the following JSON structure:
{{
    "learning_path": {{
        "title": "Learning Path Title",
        "description": "What this path will teach",
        "total_duration": "X weeks/months",
        "difficulty_progression": "beginner → intermediate → advanced",
        "modules": [
            {{
                "module": 1,
                "title": "Module Title",
                "duration": "X days",
                "objectives": ["objective1", "objective2"],
                "activities": ["activity1", "activity2"],
                "assessments": ["quiz", "project"],
                "resources": ["resource1", "resource2"]
            }}
        ],
        "prerequisites": ["prerequisite1"],
        "learning_outcomes": ["outcome1", "outcome2"],
        "career_applications": ["application1", "application2"],
        "next_steps": ["advanced topic1", "related skill1"]
    }}
}}

Focus on progressive skill building and practical application.
"""

        elif processing_type == ProcessingType.CATEGORIZATION:
            return f"""
Categorize and classify this video content:

Video Content:
{content}

Please provide categorization in the following JSON structure:
{{
    "primary_category": "main category",
    "subcategories": ["sub1", "sub2"],
    "content_tags": ["tag1", "tag2", "tag3"],
    "skill_level": "beginner|intermediate|advanced|expert",
    "content_format": "tutorial|lecture|demo|discussion|review",
    "domain": "technology|business|education|science|arts|other",
    "language_complexity": 1-10,
    "technical_depth": 1-10,
    "engagement_type": "passive|interactive|hands-on",
    "time_investment": "quick|moderate|substantial",
    "practical_application": "immediately|short-term|long-term",
    "target_demographics": ["professional", "student", "hobbyist"],
    "related_keywords": ["keyword1", "keyword2"]
}}

Focus on accurate classification for content discovery.
"""
        
        return content
    
    @check_rate_limit_decorator('openai')
    async def _process_with_openai(self, request: AIProcessingRequest) -> AIProcessingResult:
        """Process content using OpenAI"""
        try:
            model = request.model or self.model_configs[AIProvider.OPENAI]['default']
            prompt = self._get_processing_prompt(request.processing_type, request.content, request.context)
            
            start_time = datetime.now(timezone.utc)
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert video content analyzer. Provide detailed, accurate analysis in the requested JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature,
                response_format={"type": "json_object"}
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Extract tokens and calculate cost
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Track usage
            await track_api_call(
                service="openai",
                endpoint="chat/completions",
                tokens=tokens_used,
                model=model,
                output_tokens=output_tokens,
                request_type=request.processing_type.value,
                video_id=request.video_id
            )
            
            # Calculate cost
            cost = cost_monitor.calculate_cost("openai", model, input_tokens, output_tokens)
            
            # Parse result
            try:
                result_data = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                result_data = {"raw_response": response.choices[0].message.content}
            
            result = AIProcessingResult(
                provider="openai",
                model=model,
                processing_type=request.processing_type.value,
                result=result_data,
                tokens_used=tokens_used,
                cost=cost,
                processing_time=processing_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True
            )
            
            logger.info(f"✅ OpenAI processing complete: {model} - {tokens_used} tokens - ${cost:.4f}")
            return result
            
        except Exception as e:
            error_msg = f"OpenAI processing failed: {str(e)}"
            logger.error(error_msg)
            
            return AIProcessingResult(
                provider="openai",
                model=request.model or "gpt-4o-mini",
                processing_type=request.processing_type.value,
                result={},
                tokens_used=0,
                cost=0.0,
                processing_time=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                error_message=error_msg
            )
    
    @check_rate_limit_decorator('anthropic')
    async def _process_with_anthropic(self, request: AIProcessingRequest) -> AIProcessingResult:
        """Process content using Anthropic Claude"""
        try:
            model = request.model or self.model_configs[AIProvider.ANTHROPIC]['default']
            prompt = self._get_processing_prompt(request.processing_type, request.content, request.context)
            
            start_time = datetime.now(timezone.utc)
            
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Extract tokens and calculate cost
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Track usage
            await track_api_call(
                service="anthropic",
                endpoint="messages",
                tokens=tokens_used,
                model=model,
                output_tokens=output_tokens,
                request_type=request.processing_type.value,
                video_id=request.video_id
            )
            
            # Calculate cost
            cost = cost_monitor.calculate_cost("anthropic", model, input_tokens, output_tokens)
            
            # Parse result
            content = response.content[0].text
            try:
                result_data = json.loads(content)
            except json.JSONDecodeError:
                result_data = {"raw_response": content}
            
            result = AIProcessingResult(
                provider="anthropic",
                model=model,
                processing_type=request.processing_type.value,
                result=result_data,
                tokens_used=tokens_used,
                cost=cost,
                processing_time=processing_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True
            )
            
            logger.info(f"✅ Anthropic processing complete: {model} - {tokens_used} tokens - ${cost:.4f}")
            return result
            
        except Exception as e:
            error_msg = f"Anthropic processing failed: {str(e)}"
            logger.error(error_msg)
            
            return AIProcessingResult(
                provider="anthropic",
                model=request.model or "claude-3-5-sonnet-20241022",
                processing_type=request.processing_type.value,
                result={},
                tokens_used=0,
                cost=0.0,
                processing_time=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                error_message=error_msg
            )
    
    @check_rate_limit_decorator('google')
    async def _process_with_gemini(self, request: AIProcessingRequest) -> AIProcessingResult:
        """Process content using Google Gemini"""
        try:
            model_name = request.model or self.model_configs[AIProvider.GEMINI]['default']
            prompt = self._get_processing_prompt(request.processing_type, request.content, request.context)
            
            start_time = datetime.now(timezone.utc)
            
            model = genai.GenerativeModel(model_name)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=request.max_tokens or 2048,
                    temperature=request.temperature
                )
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Estimate tokens (Gemini doesn't provide exact counts)
            estimated_tokens = len(prompt.split()) + len(response.text.split())
            
            # Track usage
            await track_api_call(
                service="google",
                endpoint="generate_content",
                tokens=estimated_tokens,
                model=model_name,
                request_type=request.processing_type.value,
                video_id=request.video_id
            )
            
            # Calculate cost
            cost = cost_monitor.calculate_cost("google", model_name, estimated_tokens)
            
            # Parse result
            try:
                result_data = json.loads(response.text)
            except json.JSONDecodeError:
                result_data = {"raw_response": response.text}
            
            result = AIProcessingResult(
                provider="gemini",
                model=model_name,
                processing_type=request.processing_type.value,
                result=result_data,
                tokens_used=estimated_tokens,
                cost=cost,
                processing_time=processing_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=True
            )
            
            logger.info(f"✅ Gemini processing complete: {model_name} - {estimated_tokens} tokens - ${cost:.4f}")
            return result
            
        except Exception as e:
            error_msg = f"Gemini processing failed: {str(e)}"
            logger.error(error_msg)
            
            return AIProcessingResult(
                provider="gemini",
                model=request.model or "gemini-1.5-flash",
                processing_type=request.processing_type.value,
                result={},
                tokens_used=0,
                cost=0.0,
                processing_time=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                error_message=error_msg
            )
    
    async def process_content(self, request: AIProcessingRequest) -> AIProcessingResult:
        """
        Process content using the best available AI provider
        
        Args:
            request: AI processing request
            
        Returns:
            Processing result with analysis, cost, and metadata
        """
        try:
            # Select provider
            if request.provider == AIProvider.AUTO:
                provider = self._select_optimal_provider(
                    request.processing_type, 
                    len(request.content)
                )
            else:
                provider = request.provider
            
            # Route to appropriate processor
            if provider == AIProvider.OPENAI and self.openai_client:
                return await self._process_with_openai(request)
            elif provider == AIProvider.ANTHROPIC and self.anthropic_client:
                return await self._process_with_anthropic(request)
            elif provider == AIProvider.GEMINI and self.gemini_client:
                return await self._process_with_gemini(request)
            else:
                # Try fallbacks
                for fallback_provider in self._get_available_providers():
                    try:
                        fallback_request = AIProcessingRequest(
                            content=request.content,
                            processing_type=request.processing_type,
                            provider=AIProvider(fallback_provider),
                            model=request.model,
                            max_tokens=request.max_tokens,
                            temperature=request.temperature,
                            video_id=request.video_id,
                            context=request.context
                        )
                        return await self.process_content(fallback_request)
                    except Exception as e:
                        logger.warning(f"Fallback {fallback_provider} failed: {e}")
                        continue
                
                raise Exception("All AI providers failed")
                
        except Exception as e:
            error_msg = f"AI processing completely failed: {str(e)}"
            logger.error(error_msg)
            
            return AIProcessingResult(
                provider="none",
                model="none",
                processing_type=request.processing_type.value,
                result={"error": error_msg},
                tokens_used=0,
                cost=0.0,
                processing_time=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
                error_message=error_msg
            )
    
    async def analyze_video_content(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive video content analysis using multiple AI processing types
        
        Args:
            video_data: Complete video data from YouTube API
            
        Returns:
            Comprehensive AI analysis results
        """
        try:
            video_id = video_data.get('video_id', '')
            metadata = video_data.get('metadata', {})
            transcript = video_data.get('transcript', {})
            
            # Prepare content for analysis
            content_parts = []
            
            # Add metadata
            content_parts.append(f"Title: {metadata.get('title', 'Unknown')}")
            content_parts.append(f"Description: {metadata.get('description', '')[:1000]}")  # Limit description
            content_parts.append(f"Duration: {metadata.get('duration', 'Unknown')}")
            content_parts.append(f"Channel: {metadata.get('channel_title', 'Unknown')}")
            
            # Add transcript if available
            full_text = transcript.get('full_text', '')
            if full_text:
                # Limit transcript to avoid token limits
                content_parts.append(f"Transcript: {full_text[:8000]}")
            
            combined_content = '\n'.join(content_parts)
            
            # Run multiple analysis types concurrently
            analysis_tasks = []
            
            # Content analysis
            analysis_tasks.append(
                self.process_content(AIProcessingRequest(
                    content=combined_content,
                    processing_type=ProcessingType.ANALYSIS,
                    video_id=video_id
                ))
            )
            
            # Summary generation
            analysis_tasks.append(
                self.process_content(AIProcessingRequest(
                    content=combined_content,
                    processing_type=ProcessingType.SUMMARY,
                    video_id=video_id
                ))
            )
            
            # Action items generation
            analysis_tasks.append(
                self.process_content(AIProcessingRequest(
                    content=combined_content,
                    processing_type=ProcessingType.ACTIONS,
                    video_id=video_id
                ))
            )
            
            # Categorization
            analysis_tasks.append(
                self.process_content(AIProcessingRequest(
                    content=combined_content,
                    processing_type=ProcessingType.CATEGORIZATION,
                    video_id=video_id
                ))
            )
            
            # Execute all analyses
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Compile results
            ai_analysis = {
                'video_id': video_id,
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'content_analysis': None,
                'summary': None,
                'actions': None,
                'categorization': None,
                'total_cost': 0.0,
                'total_tokens': 0,
                'processing_providers': [],
                'success': True,
                'errors': []
            }
            
            # Process results
            result_types = ['content_analysis', 'summary', 'actions', 'categorization']
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    ai_analysis['errors'].append(f"{result_types[i]}: {str(result)}")
                    continue
                
                if isinstance(result, AIProcessingResult) and result.success:
                    ai_analysis[result_types[i]] = result.result
                    ai_analysis['total_cost'] += result.cost
                    ai_analysis['total_tokens'] += result.tokens_used
                    if result.provider not in ai_analysis['processing_providers']:
                        ai_analysis['processing_providers'].append(result.provider)
                else:
                    ai_analysis['errors'].append(f"{result_types[i]}: Processing failed")
            
            # Determine overall success
            successful_analyses = sum(1 for i in range(4) if ai_analysis[result_types[i]] is not None)
            ai_analysis['success'] = successful_analyses >= 2  # At least 50% success rate
            
            logger.info(f"🤖 Video AI analysis complete for {video_id}")
            logger.info(f"   - Successful analyses: {successful_analyses}/4")
            logger.info(f"   - Total cost: ${ai_analysis['total_cost']:.4f}")
            logger.info(f"   - Providers used: {', '.join(ai_analysis['processing_providers'])}")
            
            return ai_analysis
            
        except Exception as e:
            logger.error(f"Error in video content analysis: {e}")
            return {
                'video_id': video_data.get('video_id', ''),
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'success': False,
                'error': str(e),
                'total_cost': 0.0,
                'total_tokens': 0
            }

# Global service instance
ai_processor = None

def get_ai_processor() -> RealAIProcessorService:
    """Get or create AI processor service instance"""
    global ai_processor
    if ai_processor is None:
        ai_processor = RealAIProcessorService()
    return ai_processor

async def analyze_video_with_ai(video_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for video AI analysis"""
    processor = get_ai_processor()
    return await processor.analyze_video_content(video_data)

if __name__ == "__main__":
    # Test the AI processor
    async def test_ai_processor():
        processor = RealAIProcessorService()
        
        test_content = """
        This is a sample video about machine learning fundamentals.
        The video covers linear regression, decision trees, and neural networks.
        It's aimed at beginners and includes practical Python examples.
        Duration: 15 minutes.
        """
        
        request = AIProcessingRequest(
            content=test_content,
            processing_type=ProcessingType.ANALYSIS,
            provider=AIProvider.AUTO
        )
        
        result = await processor.process_content(request)
        print(f"Analysis Result:")
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")
        print(f"Cost: ${result.cost:.4f}")
        print(f"Result: {json.dumps(result.result, indent=2)}")
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_processor())