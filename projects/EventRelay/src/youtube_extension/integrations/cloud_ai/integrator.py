"""
Cloud AI Integrator

Main orchestrator for all cloud AI provider integrations.
Handles routing, fallback, and aggregation of results.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .base import BaseCloudAI, CloudAIProvider, AnalysisType, VideoAnalysisResult, DetectionResult
from .exceptions import CloudAIError, ServiceUnavailableError


logger = logging.getLogger(__name__)


class CloudAIIntegrator:
    """
    Main integrator for cloud AI services.
    
    Provides intelligent routing, fallback mechanisms, and result aggregation
    across multiple cloud AI providers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[CloudAIProvider, BaseCloudAI] = {}
        self.fallback_order = [
            CloudAIProvider.GOOGLE_CLOUD,
            CloudAIProvider.AWS_REKOGNITION, 
            CloudAIProvider.AZURE_VISION
        ]
        self._initialized = False
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def initialize(self) -> None:
        """Initialize all configured cloud AI providers."""
        if self._initialized:
            return
            
        # Dynamically import and initialize providers based on config
        await self._initialize_google_cloud()
        await self._initialize_aws_rekognition() 
        await self._initialize_azure_vision()
        
        self._initialized = True
        logger.info(f"Initialized {len(self.providers)} cloud AI providers")
    
    async def cleanup(self) -> None:
        """Cleanup all provider connections."""
        for provider in self.providers.values():
            try:
                await provider.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up provider: {e}")
        
        self.providers.clear()
        self._initialized = False
    
    async def analyze_video(self, video_url: str, 
                          analysis_types: List[AnalysisType],
                          preferred_provider: Optional[CloudAIProvider] = None,
                          use_fallback: bool = True) -> VideoAnalysisResult:
        """
        Analyze video using specified provider with fallback support.
        
        Args:
            video_url: URL or path to video
            analysis_types: List of analysis types to perform
            preferred_provider: Preferred cloud AI provider
            use_fallback: Whether to try fallback providers on failure
            
        Returns:
            Combined analysis results
        """
        if not self._initialized:
            await self.initialize()
        
        # Determine provider order
        provider_order = []
        if preferred_provider and preferred_provider in self.providers:
            provider_order.append(preferred_provider)
            
        if use_fallback:
            for provider in self.fallback_order:
                if provider not in provider_order and provider in self.providers:
                    provider_order.append(provider)
        
        last_error = None
        
        # Try providers in order
        for provider_type in provider_order:
            provider = self.providers[provider_type]
            
            # Check if provider supports required analysis types
            supported_types = provider.get_supported_analysis_types()
            available_types = [t for t in analysis_types if t in supported_types]
            
            if not available_types:
                continue
                
            try:
                logger.info(f"Analyzing video with {provider_type.value}")
                result = await provider.analyze_video(video_url, available_types)
                
                # Add provider info to result
                result.provider = provider_type
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_type.value} failed: {e}")
                continue
        
        # All providers failed
        raise CloudAIError(
            f"All providers failed to analyze video. Last error: {last_error}",
            error_code="ALL_PROVIDERS_FAILED"
        )
    
    async def multi_provider_analysis(self, video_url: str,
                                    analysis_types: List[AnalysisType]) -> List[VideoAnalysisResult]:
        """
        Analyze video using multiple providers and return aggregated results.
        
        Useful for comparing provider accuracy and getting comprehensive analysis.
        """
        if not self._initialized:
            await self.initialize()
        
        tasks = []
        
        for provider_type, provider in self.providers.items():
            # Check supported types
            supported_types = provider.get_supported_analysis_types()
            available_types = [t for t in analysis_types if t in supported_types]
            
            if available_types:
                task = self._safe_analyze(provider, video_url, available_types, provider_type)
                tasks.append(task)
        
        # Run analyses in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = []
        for result in results:
            if isinstance(result, VideoAnalysisResult):
                successful_results.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Provider analysis failed: {result}")
        
        return successful_results
    
    async def _safe_analyze(self, provider: BaseCloudAI, video_url: str,
                          analysis_types: List[AnalysisType], 
                          provider_type: CloudAIProvider) -> Optional[VideoAnalysisResult]:
        """Safely analyze video with error handling."""
        try:
            result = await provider.analyze_video(video_url, analysis_types)
            result.provider = provider_type
            return result
        except Exception as e:
            logger.error(f"Provider {provider_type.value} analysis failed: {e}")
            return None
    
    def aggregate_results(self, results: List[VideoAnalysisResult]) -> VideoAnalysisResult:
        """
        Aggregate results from multiple providers into a single comprehensive result.
        
        Combines detection results, applies confidence weighting, and resolves conflicts.
        """
        if not results:
            raise ValueError("No results to aggregate")
        
        # Use first result as base
        base_result = results[0]
        
        if len(results) == 1:
            return base_result
        
        # Aggregate detection results from all providers
        all_objects = []
        all_labels = []
        all_text = []
        all_faces = []
        all_logos = []
        
        for result in results:
            all_objects.extend(result.objects)
            all_labels.extend(result.labels)
            all_text.extend(result.text_detections)
            all_faces.extend(result.faces)
            all_logos.extend(result.logos)
        
        # Deduplicate and merge similar detections
        merged_objects = self._merge_detections(all_objects)
        merged_labels = self._merge_detections(all_labels)
        merged_text = self._merge_detections(all_text)
        merged_faces = self._merge_detections(all_faces)
        merged_logos = self._merge_detections(all_logos)
        
        # Create aggregated result
        aggregated = VideoAnalysisResult(
            provider=CloudAIProvider.GOOGLE_CLOUD,  # Mark as aggregated
            video_id=base_result.video_id,
            analysis_types=list(set().union(*[r.analysis_types for r in results])),
            objects=merged_objects,
            labels=merged_labels,
            text_detections=merged_text,
            faces=merged_faces,
            logos=merged_logos,
            shots=base_result.shots,  # Take from first provider
            scenes=base_result.scenes,
            processing_time=max(r.processing_time for r in results),
            cost_estimate=sum(r.cost_estimate or 0 for r in results),
            raw_response={"aggregated_from": [r.provider.value for r in results]}
        )
        
        return aggregated
    
    def _merge_detections(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Merge similar detection results and increase confidence for duplicates."""
        if not detections:
            return []
        
        merged = {}
        
        for detection in detections:
            key = detection.label.lower()
            
            if key in merged:
                # Average confidence scores for duplicate detections
                existing = merged[key]
                new_confidence = (existing.confidence + detection.confidence) / 2
                existing.confidence = min(new_confidence * 1.1, 1.0)  # Boost for consensus
            else:
                merged[key] = detection
        
        # Sort by confidence descending
        return sorted(merged.values(), key=lambda x: x.confidence, reverse=True)
    
    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured providers."""
        status = {}
        
        for provider_type, provider in self.providers.items():
            try:
                provider_status = await provider.get_service_status()
                status[provider_type.value] = {
                    "available": True,
                    "status": provider_status
                }
            except Exception as e:
                status[provider_type.value] = {
                    "available": False,
                    "error": str(e)
                }
        
        return status
    
    # Provider initialization methods (to be implemented based on availability)
    
    async def _initialize_google_cloud(self) -> None:
        """Initialize Google Cloud Video Intelligence if configured."""
        google_config = self.config.get("google_cloud", {})
        if google_config.get("enabled", False):
            try:
                from .providers.google_cloud import GoogleCloudAI
                provider = GoogleCloudAI(google_config)
                await provider.initialize()
                self.providers[CloudAIProvider.GOOGLE_CLOUD] = provider
                logger.info("Google Cloud AI initialized successfully")
            except ImportError:
                logger.warning("Google Cloud AI dependencies not available")
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud AI: {e}")
    
    async def _initialize_aws_rekognition(self) -> None:
        """Initialize AWS Rekognition if configured.""" 
        aws_config = self.config.get("aws_rekognition", {})
        if aws_config.get("enabled", False):
            try:
                from .providers.aws_rekognition import AWSRekognition
                provider = AWSRekognition(aws_config)
                await provider.initialize()
                self.providers[CloudAIProvider.AWS_REKOGNITION] = provider
                logger.info("AWS Rekognition initialized successfully")
            except ImportError:
                logger.warning("AWS Rekognition dependencies not available")
            except Exception as e:
                logger.error(f"Failed to initialize AWS Rekognition: {e}")
    
    async def _initialize_azure_vision(self) -> None:
        """Initialize Azure AI Vision if configured."""
        azure_config = self.config.get("azure_vision", {})  
        if azure_config.get("enabled", False):
            try:
                from .providers.azure_vision import AzureVision
                provider = AzureVision(azure_config)
                await provider.initialize()
                self.providers[CloudAIProvider.AZURE_VISION] = provider
                logger.info("Azure AI Vision initialized successfully")
            except ImportError:
                logger.warning("Azure AI Vision dependencies not available")
            except Exception as e:
                logger.error(f"Failed to initialize Azure AI Vision: {e}")
    
    async def _initialize_apple_fastvlm(self) -> None:
        """Initialize Apple FastVLM if configured."""
        apple_config = self.config.get("apple_fastvlm", {})
        if apple_config.get("enabled", False):
            try:
                from .providers.apple_fastvlm import AppleFastVLM
                provider = AppleFastVLM(apple_config)
                await provider.initialize()
                self.providers[CloudAIProvider.APPLE_FASTVLM] = provider
                logger.info("Apple FastVLM initialized successfully")
            except ImportError:
                logger.warning("Apple FastVLM dependencies not available")
            except Exception as e:
                logger.error(f"Failed to initialize Apple FastVLM: {e}")
