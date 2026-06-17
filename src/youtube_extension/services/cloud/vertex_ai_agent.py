#!/usr/bin/env python3
"""
Vertex AI Agent Builder Service
================================

Integrates with Vertex AI Agent Builder for advanced agent reasoning.
Replaces direct Gemini API calls with managed agent inference.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

try:
    from google.cloud import aiplatform
    from vertexai.preview import reasoning_engines
    from vertexai.generative_models import GenerativeModel, Part, Content
    import vertexai
    VERTEX_AI_AVAILABLE = True
except ImportError:
    aiplatform = None
    reasoning_engines = None
    GenerativeModel = None
    Part = None
    Content = None
    vertexai = None
    VERTEX_AI_AVAILABLE = False
    logging.warning("Vertex AI not available - install: pip install google-cloud-aiplatform")


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for Vertex AI Agent"""
    model_name: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_MODEL", "gemini-3.5-flash")
    )
    temperature: float = 0.4
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 8192
    response_schema: Optional[Dict[str, Any]] = None
    tools: Optional[List[Any]] = None
    safety_settings: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from Vertex AI Agent"""
    text: str
    metadata: Dict[str, Any]
    thinking_process: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class VertexAIAgentService:
    """
    Service for managing Vertex AI Agent Builder integration.

    Provides:
    - Agent-based reasoning via Vertex AI
    - Multi-turn conversations
    - Tool integration
    - Structured output generation
    - Thinking process tracking
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        agent_config: Optional[AgentConfig] = None,
    ):
        """
        Initialize Vertex AI Agent service.

        Args:
            project_id: GCP project ID (defaults to env GOOGLE_CLOUD_PROJECT)
            location: GCP region for Vertex AI
            agent_config: Agent configuration
        """
        if not VERTEX_AI_AVAILABLE:
            raise ImportError(
                "Vertex AI not available. Install: pip install google-cloud-aiplatform"
            )

        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location
        self.agent_config = agent_config or AgentConfig()

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Initialize model
        self.model: Optional[GenerativeModel] = None
        self._initialize_model()

        logger.info(
            f"VertexAIAgentService initialized: "
            f"project={self.project_id}, location={self.location}, "
            f"model={self.agent_config.model_name}"
        )

    def _initialize_model(self) -> None:
        """Initialize Generative Model with configuration"""
        generation_config = {
            "temperature": self.agent_config.temperature,
            "top_p": self.agent_config.top_p,
            "top_k": self.agent_config.top_k,
            "max_output_tokens": self.agent_config.max_output_tokens,
        }

        if self.agent_config.response_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = self.agent_config.response_schema

        self.model = GenerativeModel(
            model_name=self.agent_config.model_name,
            generation_config=generation_config,
            safety_settings=self.agent_config.safety_settings,
            tools=self.agent_config.tools,
        )

        logger.info(f"Initialized Vertex AI model: {self.agent_config.model_name}")

    async def process_text(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process text with Vertex AI agent.

        Args:
            prompt: User prompt/query
            context: Additional context
            system_instruction: System-level instructions

        Returns:
            AgentResponse with results
        """
        # Build full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nQuery:\n{prompt}"

        # Create content
        contents = [Content(role="user", parts=[Part.from_text(full_prompt)])]

        # Generate response
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                contents,
                stream=False
            )

            # Extract text
            text = response.text if hasattr(response, 'text') else ""

            # Extract metadata
            metadata = {
                'model': self.agent_config.model_name,
                'prompt_tokens': response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                'candidates_count': len(response.candidates) if hasattr(response, 'candidates') else 0,
            }

            # Extract usage
            usage = None
            if hasattr(response, 'usage_metadata'):
                usage = {
                    'prompt_tokens': response.usage_metadata.prompt_token_count,
                    'completion_tokens': response.usage_metadata.candidates_token_count,
                    'total_tokens': response.usage_metadata.total_token_count,
                }

            # Extract finish reason
            finish_reason = None
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = str(response.candidates[0].finish_reason)

            return AgentResponse(
                text=text,
                metadata=metadata,
                finish_reason=finish_reason,
                usage=usage,
            )

        except Exception as e:
            logger.error(f"Error processing text with Vertex AI: {e}")
            raise

    async def analyze_video(
        self,
        video_url: str,
        prompt: str,
        analysis_type: str = "comprehensive",
    ) -> AgentResponse:
        """
        Analyze video content using Vertex AI agent.

        Args:
            video_url: YouTube video URL or GCS URI
            prompt: Analysis prompt
            analysis_type: Type of analysis (comprehensive, summary, technical)

        Returns:
            AgentResponse with analysis
        """
        # Build analysis prompt
        if analysis_type == "comprehensive":
            full_prompt = f"""Analyze the following video comprehensively:

Video: {video_url}

Provide a detailed analysis covering:
1. Main topics and themes
2. Key insights and takeaways
3. Content structure and flow
4. Technical quality
5. Educational value

{prompt}
"""
        elif analysis_type == "summary":
            full_prompt = f"""Provide a concise summary of this video:

Video: {video_url}

{prompt}
"""
        else:  # technical
            full_prompt = f"""Perform technical analysis of this video:

Video: {video_url}

Analyze:
- Video quality metrics
- Audio clarity
- Scene composition
- Editing techniques

{prompt}
"""

        return await self.process_text(full_prompt)

    async def analyze_transcript(
        self,
        transcript: str,
        video_metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Analyze video transcript using Vertex AI agent.

        Args:
            transcript: Video transcript text
            video_metadata: Optional video metadata

        Returns:
            AgentResponse with analysis
        """
        # Build context from metadata
        context = ""
        if video_metadata:
            context = f"""Video Metadata:
- Title: {video_metadata.get('title', 'N/A')}
- Channel: {video_metadata.get('channel', 'N/A')}
- Duration: {video_metadata.get('duration', 'N/A')}
- Views: {video_metadata.get('views', 'N/A')}
"""

        prompt = f"""{context}

Transcript:
{transcript}

Analyze this video transcript and provide:
1. Main topics and key points
2. Speaker insights and expertise level
3. Educational value and clarity
4. Action items or recommendations
5. Overall quality assessment
"""

        return await self.process_text(prompt, context=context)

    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from prompt.

        Args:
            prompt: User prompt
            schema: JSON schema for output

        Returns:
            Structured data matching schema
        """
        # Update model config with schema
        original_config = self.agent_config
        self.agent_config.response_schema = schema
        self._initialize_model()

        try:
            response = await self.process_text(prompt)
            # Parse JSON response
            result = json.loads(response.text)
            return result

        finally:
            # Restore original config
            self.agent_config = original_config
            self._initialize_model()

    async def batch_process(
        self,
        prompts: List[str],
        max_concurrent: int = 5,
    ) -> List[AgentResponse]:
        """
        Process multiple prompts concurrently.

        Args:
            prompts: List of prompts
            max_concurrent: Maximum concurrent requests

        Returns:
            List of AgentResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(prompt: str) -> AgentResponse:
            async with semaphore:
                return await self.process_text(prompt)

        tasks = [process_with_semaphore(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing prompt {i}: {result}")
            else:
                responses.append(result)

        logger.info(f"Batch processed {len(responses)}/{len(prompts)} prompts successfully")
        return responses

    async def create_chat_session(self) -> Any:
        """
        Create a multi-turn chat session.

        Returns:
            Chat session object
        """
        return self.model.start_chat()

    def get_embeddings_model(self, model_name: str = "text-embedding-004") -> Any:
        """
        Get text embeddings model (Google Embedded 2).

        Args:
            model_name: Embedding model name

        Returns:
            Embedding model instance
        """
        from vertexai.language_models import TextEmbeddingModel

        model = TextEmbeddingModel.from_pretrained(model_name)
        logger.info(f"Initialized embeddings model: {model_name}")
        return model

    async def generate_embeddings(
        self,
        texts: List[str],
        model_name: str = "text-embedding-004",
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> List[List[float]]:
        """
        Generate embeddings for text using Google Embedded 2.

        Args:
            texts: List of texts to embed
            model_name: Embedding model name
            task_type: Task type (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)

        Returns:
            List of embedding vectors
        """
        model = self.get_embeddings_model(model_name)

        # Generate embeddings
        embeddings = await asyncio.to_thread(
            model.get_embeddings,
            texts,
            task_type=task_type
        )

        vectors = [emb.values for emb in embeddings]
        logger.info(f"Generated {len(vectors)} embeddings")
        return vectors


# Singleton instance
_vertex_ai_service: Optional[VertexAIAgentService] = None


def get_vertex_ai_service() -> VertexAIAgentService:
    """Get or create singleton Vertex AI service instance"""
    global _vertex_ai_service

    if _vertex_ai_service is None:
        _vertex_ai_service = VertexAIAgentService()

    return _vertex_ai_service
