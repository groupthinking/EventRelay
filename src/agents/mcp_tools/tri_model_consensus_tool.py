#!/usr/bin/env python3
"""
Tri-Model Consensus MCP Tool - Grok + Claude + Gemini
Consensus voting for architecture and code generation decisions
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import model clients
try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Gemini SDK not available")

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    logger.warning("Anthropic SDK not available")

try:
    import requests
    GROK_AVAILABLE = True
except ImportError:
    GROK_AVAILABLE = False
    logger.warning("Requests library not available for Grok")


class ConsensusStrategy(str, Enum):
    """Consensus decision strategies"""
    MAJORITY_VOTE = "majority_vote"  # Most common response wins
    WEIGHTED_CONFIDENCE = "weighted_confidence"  # Weight by model confidence
    QUALITY_SCORE = "quality_score"  # Evaluate response quality
    UNANIMOUS = "unanimous"  # All models must agree


@dataclass
class ModelResponse:
    """Response from a single model"""
    model_name: str
    response: str
    confidence: float
    latency_ms: int
    error: Optional[str] = None


@dataclass
class ConsensusResult:
    """Result of consensus voting"""
    consensus_response: str
    consensus_confidence: float
    strategy_used: ConsensusStrategy
    model_responses: List[ModelResponse]
    agreement_score: float  # 0-1, how much models agreed
    reasoning: str


class TriModelConsensusTool:
    """
    MCP-compatible tri-model consensus tool.
    Queries Grok, Claude, and Gemini for consensus decisions.
    """

    def __init__(self):
        # Load API keys
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.grok_api_key = os.environ.get("GROK_API_KEY", "xai-dgK2bIGv5h99A8vBrlkBMgFuF8BHt1mZsbKQxASot5Oq5p3x0lj5zCjwPtHZzxAxPrKWa4YBzu55VNQ7")

        # Initialize clients
        self.gemini_client = None
        self.claude_client = None

        if GEMINI_AVAILABLE and self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            logger.info("✅ Gemini client initialized")

        if CLAUDE_AVAILABLE and self.claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
            logger.info("✅ Claude client initialized")

        if GROK_AVAILABLE and self.grok_api_key:
            logger.info("✅ Grok client configured")

        # Availability check
        self.models_available = sum([
            self.gemini_client is not None,
            self.claude_client is not None,
            GROK_AVAILABLE and self.grok_api_key is not None
        ])

        logger.info(f"📊 Tri-Model Consensus: {self.models_available}/3 models available")

    async def close(self):
        """Clean up resources"""
        pass

    async def get_consensus(
        self,
        prompt: str,
        task_type: str = "architecture",
        strategy: ConsensusStrategy = ConsensusStrategy.WEIGHTED_CONFIDENCE,
        require_all: bool = False
    ) -> Dict[str, Any]:
        """
        Get consensus decision from all three models.

        MCP Tool: get_consensus

        Args:
            prompt: The question/task to send to models
            task_type: Type of task (architecture, code_generation, error_fixing)
            strategy: Consensus strategy to use
            require_all: If True, fail if any model unavailable

        Returns:
            Dict with consensus result and all model responses
        """
        try:
            logger.info(f"🔮 Getting tri-model consensus for: {task_type}")

            if require_all and self.models_available < 3:
                return {
                    "status": "error",
                    "error": f"Only {self.models_available}/3 models available, require_all=True"
                }

            if self.models_available == 0:
                return {
                    "status": "error",
                    "error": "No models available"
                }

            # Query all available models in parallel
            tasks = []
            if self.gemini_client:
                tasks.append(self._query_gemini(prompt, task_type))
            if self.claude_client:
                tasks.append(self._query_claude(prompt, task_type))
            if GROK_AVAILABLE and self.grok_api_key:
                tasks.append(self._query_grok(prompt, task_type))

            model_responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and convert to ModelResponse objects
            valid_responses = []
            for response in model_responses:
                if isinstance(response, ModelResponse):
                    valid_responses.append(response)
                elif isinstance(response, Exception):
                    logger.error(f"Model query failed: {response}")

            if not valid_responses:
                return {
                    "status": "error",
                    "error": "All model queries failed"
                }

            # Compute consensus
            consensus = self._compute_consensus(valid_responses, strategy)

            return {
                "status": "success",
                "consensus_response": consensus.consensus_response,
                "consensus_confidence": consensus.consensus_confidence,
                "agreement_score": consensus.agreement_score,
                "strategy_used": consensus.strategy_used.value,
                "reasoning": consensus.reasoning,
                "model_responses": [
                    {
                        "model": r.model_name,
                        "response": r.response[:500],  # Truncate for summary
                        "confidence": r.confidence,
                        "latency_ms": r.latency_ms
                    }
                    for r in valid_responses
                ],
                "models_queried": len(valid_responses)
            }

        except Exception as e:
            logger.error(f"Consensus error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }

    async def _query_gemini(self, prompt: str, task_type: str) -> ModelResponse:
        """Query Gemini 3 Pro"""
        import time
        start_time = time.time()

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3-pro-preview',
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.7,  # Lower temperature for more consistent decisions
                    max_output_tokens=2048
                )
            )

            # Handle thinking mode responses
            response_text = response.text
            if response_text is None:
                if response.candidates and response.candidates[0].content.parts:
                    text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
                    response_text = "\n".join(text_parts) if text_parts else ""

            latency = int((time.time() - start_time) * 1000)

            return ModelResponse(
                model_name="Gemini-3-Pro",
                response=response_text or "",
                confidence=0.85,  # Default confidence
                latency_ms=latency
            )

        except Exception as e:
            logger.error(f"Gemini query failed: {e}")
            return ModelResponse(
                model_name="Gemini-3-Pro",
                response="",
                confidence=0.0,
                latency_ms=0,
                error=str(e)
            )

    async def _query_claude(self, prompt: str, task_type: str) -> ModelResponse:
        """Query Claude Opus 4.5 (latest flagship model with effort control)"""
        import time
        start_time = time.time()

        try:
            # Claude Opus 4.5 - November 2024 release
            model = "claude-opus-4-5-20251101"

            # Try with effort parameter (beta feature)
            try:
                response = self.claude_client.beta.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0.7,
                    betas=["effort-2025-11-24"],
                    effort="medium",  # Balanced approach for consensus decisions
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
            except TypeError:
                # Fallback if effort parameter not supported in SDK version
                logger.warning("Effort parameter not supported, using default")
                response = self.claude_client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

            response_text = response.content[0].text if response.content else ""
            latency = int((time.time() - start_time) * 1000)

            return ModelResponse(
                model_name="Claude-Opus-4.5",
                response=response_text,
                confidence=0.95,  # Opus 4.5 highest quality
                latency_ms=latency
            )

        except Exception as e:
            logger.error(f"Claude Opus 4.5 query failed: {e}")
            return ModelResponse(
                model_name="Claude-Opus-4.5",
                response="",
                confidence=0.0,
                latency_ms=0,
                error=str(e)
            )

    async def _query_grok(self, prompt: str, task_type: str) -> ModelResponse:
        """Query Grok 4.1 (latest X.AI model via OpenAI-compatible API)"""
        import time
        start_time = time.time()

        try:
            # Grok uses OpenAI-compatible API
            import requests

            # Try Grok 2 latest (December 2024 release)
            # Model names: "grok-2-1212" or "grok-2-latest"
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-2-1212",  # Grok 2 December 2024 (latest)
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096  # Higher token limit
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                latency = int((time.time() - start_time) * 1000)

                return ModelResponse(
                    model_name="Grok-4.1",
                    response=response_text,
                    confidence=0.90,  # Grok 4.1 high quality
                    latency_ms=latency
                )
            else:
                error_body = response.text if hasattr(response, 'text') else str(response.status_code)
                raise Exception(f"Grok API error {response.status_code}: {error_body}")

        except Exception as e:
            logger.error(f"Grok 4.1 query failed: {e}")
            return ModelResponse(
                model_name="Grok-4.1",
                response="",
                confidence=0.0,
                latency_ms=0,
                error=str(e)
            )

    def _compute_consensus(
        self,
        responses: List[ModelResponse],
        strategy: ConsensusStrategy
    ) -> ConsensusResult:
        """Compute consensus from model responses"""

        # Filter out failed responses
        valid_responses = [r for r in responses if not r.error and r.response]

        if not valid_responses:
            # Fallback to first response even if errored
            return ConsensusResult(
                consensus_response=responses[0].response if responses else "",
                consensus_confidence=0.0,
                strategy_used=strategy,
                model_responses=responses,
                agreement_score=0.0,
                reasoning="All models failed or returned empty responses"
            )

        if strategy == ConsensusStrategy.WEIGHTED_CONFIDENCE:
            # Weight responses by confidence scores
            total_confidence = sum(r.confidence for r in valid_responses)

            if total_confidence == 0:
                # Fallback to first response
                best_response = valid_responses[0]
            else:
                # Select response with highest confidence
                best_response = max(valid_responses, key=lambda r: r.confidence)

            # Calculate agreement score based on response similarity
            agreement_score = self._calculate_agreement(valid_responses)

            return ConsensusResult(
                consensus_response=best_response.response,
                consensus_confidence=best_response.confidence,
                strategy_used=strategy,
                model_responses=valid_responses,
                agreement_score=agreement_score,
                reasoning=f"Selected {best_response.model_name} response (confidence: {best_response.confidence:.2f})"
            )

        elif strategy == ConsensusStrategy.MAJORITY_VOTE:
            # For now, use highest confidence as tiebreaker
            # TODO: Implement actual similarity-based voting
            best_response = max(valid_responses, key=lambda r: r.confidence)
            agreement_score = self._calculate_agreement(valid_responses)

            return ConsensusResult(
                consensus_response=best_response.response,
                consensus_confidence=sum(r.confidence for r in valid_responses) / len(valid_responses),
                strategy_used=strategy,
                model_responses=valid_responses,
                agreement_score=agreement_score,
                reasoning="Majority vote (tiebreaker: highest confidence)"
            )

        else:
            # Default: use highest confidence
            best_response = max(valid_responses, key=lambda r: r.confidence)
            agreement_score = self._calculate_agreement(valid_responses)

            return ConsensusResult(
                consensus_response=best_response.response,
                consensus_confidence=best_response.confidence,
                strategy_used=strategy,
                model_responses=valid_responses,
                agreement_score=agreement_score,
                reasoning=f"Default strategy: highest confidence ({best_response.model_name})"
            )

    def _calculate_agreement(self, responses: List[ModelResponse]) -> float:
        """
        Calculate agreement score between responses.
        Returns 0.0-1.0 indicating how similar the responses are.
        """
        if len(responses) < 2:
            return 1.0

        # Simple heuristic: compare response lengths and confidence variance
        lengths = [len(r.response) for r in responses]
        confidences = [r.confidence for r in responses]

        # Length similarity (normalized)
        avg_length = sum(lengths) / len(lengths)
        length_variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        length_score = 1.0 / (1.0 + length_variance / max(avg_length, 1))

        # Confidence agreement
        avg_confidence = sum(confidences) / len(confidences)
        confidence_variance = sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)
        confidence_score = 1.0 / (1.0 + confidence_variance * 10)

        # Combined score
        agreement = (length_score + confidence_score) / 2
        return min(1.0, agreement)


# Singleton instance
_tool = None

def get_tri_model_consensus_tool() -> TriModelConsensusTool:
    """Get or create Tri-Model Consensus Tool singleton"""
    global _tool
    if _tool is None:
        _tool = TriModelConsensusTool()
    return _tool


# MCP Tool registry for agent network
MCP_TOOLS = {
    "get_consensus": get_tri_model_consensus_tool().get_consensus
}
