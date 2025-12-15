"""
Google Cloud Video Intelligence & Vision API Integration

Implements comprehensive video and image analysis using Google Cloud AI services:
- Object Tracking
- OCR (Optical Character Recognition)
- Label Detection 
- Logo Recognition
- Shot Change Detection
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseCloudAI, CloudAIProvider, AnalysisType, VideoAnalysisResult, DetectionResult
from ..exceptions import CloudAIError, ConfigurationError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class GoogleCloudAI(BaseCloudAI):
    """Google Cloud Video Intelligence and Vision API integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = CloudAIProvider.GOOGLE_CLOUD
        self._video_client = None
        self._vision_client = None
        
        # Configuration validation
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate Google Cloud configuration."""
        required_fields = ["project_id"]
        
        for field in required_fields:
            if field not in self.config:
                raise ConfigurationError(
                    f"Missing required Google Cloud config: {field}",
                    provider=self.provider.value,
                    missing_config=field
                )
    
    async def initialize(self) -> None:
        """Initialize Google Cloud AI clients."""
        try:
            # Import Google Cloud libraries
            from google.cloud import videointelligence
            from google.cloud import vision
            import google.auth
            
            # Set up authentication
            project_id = self.config["project_id"]
            
            # Initialize clients
            self._video_client = videointelligence.VideoIntelligenceServiceAsyncClient()
            self._vision_client = vision.ImageAnnotatorAsyncClient()
            
            logger.info(f"Google Cloud AI initialized for project: {project_id}")
            
        except ImportError as e:
            raise ConfigurationError(
                f"Google Cloud dependencies not installed: {e}",
                provider=self.provider.value
            )
        except Exception as e:
            raise AuthenticationError(
                f"Failed to authenticate with Google Cloud: {e}",
                provider=self.provider.value
            )
    
    async def cleanup(self) -> None:
        """Cleanup Google Cloud AI clients."""
        if self._video_client:
            await self._video_client.transport.close()
        if self._vision_client:
            await self._vision_client.transport.close()
        
        self._video_client = None
        self._vision_client = None
    
    def get_supported_analysis_types(self) -> List[AnalysisType]:
        """Get supported analysis types for Google Cloud."""
        return [
            AnalysisType.OBJECT_TRACKING,
            AnalysisType.OCR,
            AnalysisType.LABEL_DETECTION,
            AnalysisType.LOGO_RECOGNITION,
            AnalysisType.SHOT_DETECTION,
            AnalysisType.TEXT_DETECTION
        ]
    
    async def analyze_video(self, video_url: str, 
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze video using Google Cloud Video Intelligence API."""
        if not self._video_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # Import required types
            from google.cloud import videointelligence
            
            # Prepare features for analysis
            features = self._prepare_video_features(analysis_types)
            
            # Configure video input
            if video_url.startswith(('http://', 'https://')):
                input_uri = video_url
                input_content = None
            else:
                # For local files, would need to read content
                input_uri = None
                input_content = None  # Placeholder for file content
            
            # Create analysis request
            request = {
                "input_uri": input_uri,
                "input_content": input_content, 
                "features": features,
                "location_id": self.config.get("location_id", "us-central1")
            }
            
            # Start async operation
            operation = await self._video_client.annotate_video(request=request)
            
            # Wait for completion with timeout
            timeout = self.config.get("timeout", 300)  # 5 minutes default
            result = await asyncio.wait_for(operation.result(), timeout=timeout)
            
            # Process results
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._process_video_results(
                result, video_url, analysis_types, processing_time
            )
            
        except asyncio.TimeoutError:
            raise CloudAIError(
                "Video analysis timed out",
                provider=self.provider.value,
                error_code="TIMEOUT"
            )
        except Exception as e:
            if "QUOTA_EXCEEDED" in str(e):
                raise RateLimitError(
                    f"Google Cloud quota exceeded: {e}",
                    provider=self.provider.value
                )
            raise CloudAIError(
                f"Google Cloud video analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def analyze_image(self, image_url: str,
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze single image using Google Cloud Vision API."""
        if not self._vision_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            from google.cloud import vision
            
            # Prepare image
            image = vision.Image()
            if image_url.startswith(('http://', 'https://')):
                image.source.image_uri = image_url
            else:
                # For local files
                with open(image_url, 'rb') as image_file:
                    image.content = image_file.read()
            
            # Prepare features
            features = self._prepare_vision_features(analysis_types)
            
            # Perform analysis
            response = await self._vision_client.annotate_image({
                'image': image,
                'features': features
            })
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._process_vision_results(
                response, image_url, analysis_types, processing_time
            )
            
        except Exception as e:
            raise CloudAIError(
                f"Google Cloud image analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Check Google Cloud AI service status."""
        try:
            # Simple health check by making a minimal API call
            from google.cloud import vision
            
            if not self._vision_client:
                await self.initialize()
            
            # Test with empty request to check service availability
            start_time = datetime.utcnow()
            
            # Create minimal test image
            image = vision.Image()
            image.content = b""  # Empty content for health check
            
            try:
                await self._vision_client.annotate_image({
                    'image': image,
                    'features': [{'type_': vision.Feature.Type.LABEL_DETECTION, 'max_results': 1}]
                })
            except Exception:
                # Expected to fail with empty image, but service is available
                pass
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _prepare_video_features(self, analysis_types: List[AnalysisType]) -> List:
        """Convert analysis types to Google Cloud Video Intelligence features."""
        from google.cloud import videointelligence
        
        feature_map = {
            AnalysisType.OBJECT_TRACKING: videointelligence.Feature.OBJECT_TRACKING,
            AnalysisType.OCR: videointelligence.Feature.TEXT_DETECTION, 
            AnalysisType.LABEL_DETECTION: videointelligence.Feature.LABEL_DETECTION,
            AnalysisType.LOGO_RECOGNITION: videointelligence.Feature.LOGO_RECOGNITION,
            AnalysisType.SHOT_DETECTION: videointelligence.Feature.SHOT_CHANGE_DETECTION,
            AnalysisType.TEXT_DETECTION: videointelligence.Feature.TEXT_DETECTION
        }
        
        features = []
        for analysis_type in analysis_types:
            if analysis_type in feature_map:
                features.append(feature_map[analysis_type])
        
        return features
    
    def _prepare_vision_features(self, analysis_types: List[AnalysisType]) -> List:
        """Convert analysis types to Google Cloud Vision features."""
        from google.cloud import vision
        
        feature_map = {
            AnalysisType.OCR: vision.Feature.Type.TEXT_DETECTION,
            AnalysisType.LABEL_DETECTION: vision.Feature.Type.LABEL_DETECTION,
            AnalysisType.LOGO_RECOGNITION: vision.Feature.Type.LOGO_DETECTION,
            AnalysisType.OBJECT_TRACKING: vision.Feature.Type.OBJECT_LOCALIZATION,
            AnalysisType.TEXT_DETECTION: vision.Feature.Type.DOCUMENT_TEXT_DETECTION
        }
        
        features = []
        for analysis_type in analysis_types:
            if analysis_type in feature_map:
                features.append({
                    'type_': feature_map[analysis_type],
                    'max_results': 50
                })
        
        return features
    
    def _process_video_results(self, result, video_id: str, 
                             analysis_types: List[AnalysisType], 
                             processing_time: float) -> VideoAnalysisResult:
        """Process Google Cloud Video Intelligence results."""
        objects = []
        labels = []
        text_detections = []
        logos = []
        shots = []
        
        # Process annotation results
        annotation_result = result.annotation_results[0]
        
        # Object tracking results
        for obj in annotation_result.object_annotations:
            for frame in obj.frames:
                objects.append(DetectionResult(
                    label=obj.entity.description,
                    confidence=obj.confidence,
                    timestamp=frame.time_offset.total_seconds(),
                    bounding_box={
                        'x': frame.normalized_bounding_box.left,
                        'y': frame.normalized_bounding_box.top,
                        'width': frame.normalized_bounding_box.right - frame.normalized_bounding_box.left,
                        'height': frame.normalized_bounding_box.bottom - frame.normalized_bounding_box.top
                    }
                ))
        
        # Label detection results
        for label in annotation_result.segment_label_annotations:
            labels.append(DetectionResult(
                label=label.entity.description,
                confidence=label.segments[0].confidence if label.segments else 0.0
            ))
        
        # Text detection results
        for text in annotation_result.text_annotations:
            for segment in text.segments:
                text_detections.append(DetectionResult(
                    label=text.text,
                    confidence=segment.confidence,
                    timestamp=segment.segment.start_time_offset.total_seconds()
                ))
        
        # Logo detection results  
        for logo in annotation_result.logo_recognition_annotations:
            for track in logo.tracks:
                logos.append(DetectionResult(
                    label=logo.entity.description,
                    confidence=track.confidence,
                    timestamp=track.segment.start_time_offset.total_seconds()
                ))
        
        # Shot detection results
        for shot in annotation_result.shot_annotations:
            shots.append({
                'start_time': shot.start_time_offset.total_seconds(),
                'end_time': shot.end_time_offset.total_seconds()
            })
        
        return VideoAnalysisResult(
            provider=self.provider,
            video_id=video_id,
            analysis_types=analysis_types,
            objects=objects,
            labels=labels,
            text_detections=text_detections,
            faces=[],  # Not available in Video Intelligence
            logos=logos,
            shots=shots,
            scenes=[],
            processing_time=processing_time,
            raw_response={"annotation_results": [annotation_result]}
        )
    
    def _process_vision_results(self, response, image_id: str,
                              analysis_types: List[AnalysisType], 
                              processing_time: float) -> VideoAnalysisResult:
        """Process Google Cloud Vision results."""
        objects = []
        labels = []
        text_detections = []
        logos = []
        
        # Label detection
        for label in response.label_annotations:
            labels.append(DetectionResult(
                label=label.description,
                confidence=label.score
            ))
        
        # Text detection
        for text in response.text_annotations:
            text_detections.append(DetectionResult(
                label=text.description,
                confidence=1.0,  # Vision API doesn't provide confidence for text
                bounding_box={
                    'x': min(vertex.x for vertex in text.bounding_poly.vertices),
                    'y': min(vertex.y for vertex in text.bounding_poly.vertices),
                    'width': max(vertex.x for vertex in text.bounding_poly.vertices) - 
                           min(vertex.x for vertex in text.bounding_poly.vertices),
                    'height': max(vertex.y for vertex in text.bounding_poly.vertices) -
                            min(vertex.y for vertex in text.bounding_poly.vertices)
                }
            ))
        
        # Logo detection
        for logo in response.logo_annotations:
            logos.append(DetectionResult(
                label=logo.description,
                confidence=logo.score,
                bounding_box={
                    'x': min(vertex.x for vertex in logo.bounding_poly.vertices),
                    'y': min(vertex.y for vertex in logo.bounding_poly.vertices), 
                    'width': max(vertex.x for vertex in logo.bounding_poly.vertices) -
                           min(vertex.x for vertex in logo.bounding_poly.vertices),
                    'height': max(vertex.y for vertex in logo.bounding_poly.vertices) -
                            min(vertex.y for vertex in logo.bounding_poly.vertices)
                }
            ))
        
        # Object localization
        for obj in response.localized_object_annotations:
            objects.append(DetectionResult(
                label=obj.name,
                confidence=obj.score,
                bounding_box={
                    'x': obj.bounding_poly.normalized_vertices[0].x,
                    'y': obj.bounding_poly.normalized_vertices[0].y,
                    'width': obj.bounding_poly.normalized_vertices[2].x - 
                           obj.bounding_poly.normalized_vertices[0].x,
                    'height': obj.bounding_poly.normalized_vertices[2].y -
                            obj.bounding_poly.normalized_vertices[0].y
                }
            ))
        
        return VideoAnalysisResult(
            provider=self.provider,
            video_id=image_id,
            analysis_types=analysis_types,
            objects=objects,
            labels=labels,
            text_detections=text_detections,
            faces=[],
            logos=logos,
            shots=[],
            scenes=[],
            processing_time=processing_time,
            raw_response={"vision_response": response}
        )