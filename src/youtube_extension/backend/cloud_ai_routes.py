"""
Cloud AI API Routes

FastAPI routes for cloud AI video analysis services.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ..integrations.cloud_ai import (
    CloudAIIntegrator,
    AnalysisType,
    CloudAIProvider,
    VideoAnalysisResult,
    CloudAIError,
    RateLimitError,
    ConfigurationError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-ai", tags=["cloud-ai"])


class VideoAnalysisRequest(BaseModel):
    """Request model for video analysis."""
    video_url: str = Field(..., description="YouTube video URL or video ID")
    analysis_types: List[str] = Field(
        default=["label_detection", "object_tracking"],
        description="Types of analysis to perform"
    )
    preferred_provider: Optional[str] = Field(
        default=None,
        description="Preferred cloud AI provider"
    )
    use_fallback: bool = Field(
        default=True,
        description="Whether to use fallback providers on failure"
    )


class VideoAnalysisResponse(BaseModel):
    """Response model for video analysis."""
    video_id: str
    provider: str
    processing_time: float
    analysis_types: List[str]
    objects: List[Dict[str, Any]]
    labels: List[Dict[str, Any]]
    text_detections: List[Dict[str, Any]]
    faces: List[Dict[str, Any]]
    logos: List[Dict[str, Any]]
    shots: List[Dict[str, Any]]
    scenes: List[Dict[str, Any]]
    cost_estimate: Optional[float]


class BatchAnalysisRequest(BaseModel):
    """Request model for batch video analysis."""
    video_urls: List[str] = Field(..., description="List of YouTube video URLs")
    analysis_types: List[str] = Field(
        default=["label_detection"],
        description="Types of analysis to perform"
    )
    preferred_provider: Optional[str] = None
    batch_size: int = Field(default=5, ge=1, le=20)


class ProviderStatusResponse(BaseModel):
    """Response model for provider status."""
    providers: Dict[str, Dict[str, Any]]
    available_providers: List[str]
    enabled_providers: List[str]


def get_cloud_ai_config() -> Dict[str, Any]:
    """Get cloud AI configuration from environment or settings."""
    import os
    
    return {
        "google_cloud": {
            "enabled": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
            "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
            "location_id": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        },
        "aws_rekognition": {
            "enabled": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region": os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        },
        "azure_vision": {
            "enabled": bool(os.getenv("AZURE_COGNITIVE_SERVICES_KEY")),
            "subscription_key": os.getenv("AZURE_COGNITIVE_SERVICES_KEY"),
            "endpoint": os.getenv("AZURE_COGNITIVE_SERVICES_ENDPOINT")
        },
        "apple_fastvlm": {
            "enabled": bool(os.getenv("APPLE_FASTVLM_MODEL_PATH", True)),  # Always available
            "model_path": os.getenv("APPLE_FASTVLM_MODEL_PATH", "/tmp/mock_model")
        }
    }


def parse_analysis_types(analysis_types: List[str]) -> List[AnalysisType]:
    """Convert string analysis types to AnalysisType enum."""
    type_mapping = {
        "object_tracking": AnalysisType.OBJECT_TRACKING,
        "ocr": AnalysisType.OCR,
        "label_detection": AnalysisType.LABEL_DETECTION,
        "logo_recognition": AnalysisType.LOGO_RECOGNITION,
        "shot_detection": AnalysisType.SHOT_DETECTION,
        "face_detection": AnalysisType.FACE_DETECTION,
        "text_detection": AnalysisType.TEXT_DETECTION,
        "content_moderation": AnalysisType.CONTENT_MODERATION,
        "scene_analysis": AnalysisType.SCENE_ANALYSIS
    }
    
    result = []
    for type_str in analysis_types:
        if type_str in type_mapping:
            result.append(type_mapping[type_str])
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown analysis type: {type_str}. Available types: {list(type_mapping.keys())}"
            )
    
    return result


def parse_provider(provider_str: Optional[str]) -> Optional[CloudAIProvider]:
    """Convert string provider to CloudAIProvider enum."""
    if not provider_str:
        return None
    
    provider_mapping = {
        "google_cloud": CloudAIProvider.GOOGLE_CLOUD,
        "aws_rekognition": CloudAIProvider.AWS_REKOGNITION,
        "azure_vision": CloudAIProvider.AZURE_VISION,
        "apple_fastvlm": CloudAIProvider.APPLE_FASTVLM
    }
    
    if provider_str in provider_mapping:
        return provider_mapping[provider_str]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider_str}. Available providers: {list(provider_mapping.keys())}"
        )


def format_analysis_result(result: VideoAnalysisResult) -> VideoAnalysisResponse:
    """Convert VideoAnalysisResult to API response format."""
    return VideoAnalysisResponse(
        video_id=result.video_id,
        provider=result.provider.value,
        processing_time=result.processing_time,
        analysis_types=[t.value for t in result.analysis_types],
        objects=[
            {
                "label": obj.label,
                "confidence": obj.confidence,
                "timestamp": obj.timestamp,
                "bounding_box": obj.bounding_box,
                "metadata": obj.metadata
            }
            for obj in result.objects
        ],
        labels=[
            {
                "label": lbl.label,
                "confidence": lbl.confidence,
                "metadata": lbl.metadata
            }
            for lbl in result.labels
        ],
        text_detections=[
            {
                "text": txt.label,
                "confidence": txt.confidence,
                "timestamp": txt.timestamp,
                "bounding_box": txt.bounding_box
            }
            for txt in result.text_detections
        ],
        faces=[
            {
                "confidence": face.confidence,
                "timestamp": face.timestamp,
                "bounding_box": face.bounding_box,
                "metadata": face.metadata
            }
            for face in result.faces
        ],
        logos=[
            {
                "label": logo.label,
                "confidence": logo.confidence,
                "timestamp": logo.timestamp,
                "bounding_box": logo.bounding_box
            }
            for logo in result.logos
        ],
        shots=result.shots,
        scenes=result.scenes,
        cost_estimate=result.cost_estimate
    )


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status():
    """Get status of all cloud AI providers."""
    try:
        config = get_cloud_ai_config()
        
        async with CloudAIIntegrator(config) as ai:
            provider_status = await ai.get_provider_status()
            
            return ProviderStatusResponse(
                providers=provider_status,
                available_providers=[
                    provider for provider, status in provider_status.items()
                    if status.get("available", False)
                ],
                enabled_providers=list(ai.providers.keys())
            )
            
    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider status: {str(e)}")


@router.post("/analyze/video", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest):
    """Analyze a single video using cloud AI services."""
    try:
        # Parse request parameters
        analysis_types = parse_analysis_types(request.analysis_types)
        preferred_provider = parse_provider(request.preferred_provider)
        
        # Get configuration and initialize integrator
        config = get_cloud_ai_config()
        
        async with CloudAIIntegrator(config) as ai:
            # Analyze video
            result = await ai.analyze_video(
                video_url=request.video_url,
                analysis_types=analysis_types,
                preferred_provider=preferred_provider,
                use_fallback=request.use_fallback
            )
            
            # Format and return response
            return format_analysis_result(result)
            
    except CloudAIError as e:
        logger.error(f"Cloud AI analysis failed: {e}")
        raise HTTPException(status_code=503, detail=f"AI analysis failed: {str(e)}")
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {str(e)}")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during video analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch")
async def analyze_batch_videos(request: BatchAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze multiple videos in batch (background processing)."""
    try:
        analysis_types = parse_analysis_types(request.analysis_types)
        preferred_provider = parse_provider(request.preferred_provider)
        
        # Start background task for batch processing
        task_id = f"batch_{hash(tuple(request.video_urls))}"
        
        background_tasks.add_task(
            process_batch_videos,
            request.video_urls,
            analysis_types,
            preferred_provider,
            request.batch_size,
            task_id
        )
        
        return {
            "message": f"Batch analysis started for {len(request.video_urls)} videos",
            "task_id": task_id,
            "video_count": len(request.video_urls),
            "batch_size": request.batch_size
        }
        
    except Exception as e:
        logger.error(f"Failed to start batch analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.post("/analyze/multi-provider", response_model=List[VideoAnalysisResponse])
async def analyze_video_multi_provider(request: VideoAnalysisRequest):
    """Analyze video using multiple providers for comparison."""
    try:
        analysis_types = parse_analysis_types(request.analysis_types)
        config = get_cloud_ai_config()
        
        async with CloudAIIntegrator(config) as ai:
            # Get results from all available providers
            results = await ai.multi_provider_analysis(
                video_url=request.video_url,
                analysis_types=analysis_types
            )
            
            # Format results
            formatted_results = [format_analysis_result(result) for result in results]
            
            return formatted_results
            
    except Exception as e:
        logger.error(f"Multi-provider analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-provider analysis failed: {str(e)}")


@router.get("/analysis-types")
async def get_available_analysis_types():
    """Get list of available analysis types."""
    return {
        "analysis_types": [
            {
                "name": analysis_type.value,
                "description": _get_analysis_type_description(analysis_type)
            }
            for analysis_type in AnalysisType
        ]
    }


@router.get("/providers")
async def get_available_providers():
    """Get list of available cloud AI providers."""
    return {
        "providers": [
            {
                "name": provider.value,
                "description": _get_provider_description(provider)
            }
            for provider in CloudAIProvider
        ]
    }


async def process_batch_videos(video_urls: List[str], analysis_types: List[AnalysisType],
                             preferred_provider: Optional[CloudAIProvider], 
                             batch_size: int, task_id: str):
    """Background task for batch video processing."""
    logger.info(f"Starting batch processing task {task_id} for {len(video_urls)} videos")
    
    try:
        config = get_cloud_ai_config()
        results = []
        
        async with CloudAIIntegrator(config) as ai:
            # Process in batches
            for i in range(0, len(video_urls), batch_size):
                batch = video_urls[i:i+batch_size]
                
                for video_url in batch:
                    try:
                        result = await ai.analyze_video(
                            video_url=video_url,
                            analysis_types=analysis_types,
                            preferred_provider=preferred_provider,
                            use_fallback=True
                        )
                        results.append(format_analysis_result(result))
                        
                    except Exception as e:
                        logger.error(f"Failed to analyze video {video_url}: {e}")
                        continue
                
                # Brief pause between batches
                if i + batch_size < len(video_urls):
                    import asyncio
                    await asyncio.sleep(1)
        
        # Store results (in production, save to database or cache)
        logger.info(f"Batch processing task {task_id} completed. Processed {len(results)}/{len(video_urls)} videos")
        
        # In production, you would save results to a database or cache
        # and provide an endpoint to retrieve them by task_id
        
    except Exception as e:
        logger.error(f"Batch processing task {task_id} failed: {e}")


def _get_analysis_type_description(analysis_type: AnalysisType) -> str:
    """Get description for analysis type."""
    descriptions = {
        AnalysisType.OBJECT_TRACKING: "Detect and track objects throughout the video",
        AnalysisType.OCR: "Extract text from video frames using optical character recognition",
        AnalysisType.LABEL_DETECTION: "Identify objects, scenes, and concepts in the video",
        AnalysisType.LOGO_RECOGNITION: "Detect and identify brand logos",
        AnalysisType.SHOT_DETECTION: "Identify scene changes and camera cuts",
        AnalysisType.FACE_DETECTION: "Detect and analyze faces in the video",
        AnalysisType.TEXT_DETECTION: "Detect text overlays and captions",
        AnalysisType.CONTENT_MODERATION: "Identify potentially inappropriate content",
        AnalysisType.SCENE_ANALYSIS: "Analyze and describe video scenes"
    }
    return descriptions.get(analysis_type, "Unknown analysis type")


def _get_provider_description(provider: CloudAIProvider) -> str:
    """Get description for cloud AI provider."""
    descriptions = {
        CloudAIProvider.GOOGLE_CLOUD: "Google Cloud Video Intelligence & Vision API",
        CloudAIProvider.AWS_REKOGNITION: "Amazon Rekognition video and image analysis",
        CloudAIProvider.AZURE_VISION: "Microsoft Azure AI Vision services",
        CloudAIProvider.APPLE_FASTVLM: "Apple FastVLM vision language model"
    }
    return descriptions.get(provider, "Unknown provider")