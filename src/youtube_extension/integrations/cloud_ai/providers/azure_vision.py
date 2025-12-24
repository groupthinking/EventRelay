"""
Microsoft Azure AI Vision Integration

Implements video and image analysis using Azure AI Vision services:
- OCR (Optical Character Recognition)  
- Image Analysis
- Video Analysis
- Custom Vision (if configured)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64

from ..base import BaseCloudAI, CloudAIProvider, AnalysisType, VideoAnalysisResult, DetectionResult
from ..exceptions import CloudAIError, ConfigurationError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class AzureVision(BaseCloudAI):
    """Microsoft Azure AI Vision integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = CloudAIProvider.AZURE_VISION
        self._vision_client = None
        self._video_indexer_client = None
        
        # Configuration validation
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate Azure AI Vision configuration."""
        required_fields = ["subscription_key", "endpoint"]
        
        for field in required_fields:
            if field not in self.config:
                raise ConfigurationError(
                    f"Missing required Azure config: {field}",
                    provider=self.provider.value,
                    missing_config=field
                )
    
    async def initialize(self) -> None:
        """Initialize Azure AI Vision clients."""
        try:
            # Import Azure Cognitive Services libraries
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
            from msrest.authentication import CognitiveServicesCredentials
            
            # Initialize Computer Vision client
            credentials = CognitiveServicesCredentials(self.config["subscription_key"])
            self._vision_client = ComputerVisionClient(
                self.config["endpoint"], 
                credentials
            )
            
            # Test connection
            await self._test_connection()
            
            logger.info(f"Azure AI Vision initialized with endpoint: {self.config['endpoint']}")
            
        except ImportError as e:
            raise ConfigurationError(
                f"Azure Cognitive Services SDK not installed: {e}. Install with: pip install azure-cognitiveservices-vision-computervision",
                provider=self.provider.value
            )
        except Exception as e:
            raise AuthenticationError(
                f"Azure AI Vision authentication failed: {e}",
                provider=self.provider.value
            )
    
    async def cleanup(self) -> None:
        """Cleanup Azure clients."""
        # Azure clients don't require explicit cleanup
        self._vision_client = None
        self._video_indexer_client = None
    
    async def _test_connection(self) -> None:
        """Test Azure AI Vision connection."""
        try:
            # Test with list models call
            models = self._vision_client.list_models()
            logger.info(f"Azure AI Vision connection test successful. Available models: {len(models.models_property)}")
        except Exception as e:
            raise AuthenticationError(f"Azure connection test failed: {e}")
    
    def get_supported_analysis_types(self) -> List[AnalysisType]:
        """Get supported analysis types for Azure AI Vision."""
        return [
            AnalysisType.OCR,
            AnalysisType.LABEL_DETECTION,
            AnalysisType.OBJECT_TRACKING,
            AnalysisType.TEXT_DETECTION,
            AnalysisType.FACE_DETECTION,
            AnalysisType.SCENE_ANALYSIS
        ]
    
    async def analyze_video(self, video_url: str,
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze video using Azure AI Vision."""
        if not self._vision_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # Azure Computer Vision doesn't have direct video analysis
            # For video analysis, we'd typically use Azure Video Indexer
            # For this implementation, we'll extract frames and analyze them
            
            frames = await self._extract_video_frames(video_url, max_frames=10)
            frame_results = []
            
            for i, frame_data in enumerate(frames):
                try:
                    frame_result = await self._analyze_frame(
                        frame_data, analysis_types, timestamp=i * 5.0  # Assume 5 second intervals
                    )
                    frame_results.append(frame_result)
                except Exception as e:
                    logger.warning(f"Failed to analyze frame {i}: {e}")
                    continue
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._aggregate_frame_results(
                frame_results, video_url, analysis_types, processing_time
            )
            
        except Exception as e:
            if "429" in str(e) or "RateLimitExceeded" in str(e):
                raise RateLimitError(
                    f"Azure AI Vision rate limit exceeded: {e}",
                    provider=self.provider.value
                )
            raise CloudAIError(
                f"Azure AI Vision video analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def analyze_image(self, image_url: str,
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze single image using Azure AI Vision."""
        if not self._vision_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            results = {}
            
            # Prepare image input
            image_stream = await self._prepare_image_input(image_url)
            
            # Perform different analyses based on requested types
            if AnalysisType.OCR in analysis_types or AnalysisType.TEXT_DETECTION in analysis_types:
                results['ocr'] = await self._perform_ocr(image_url, image_stream)
            
            if any(t in analysis_types for t in [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING, AnalysisType.SCENE_ANALYSIS]):
                results['analyze'] = await self._analyze_image_content(image_url, image_stream)
            
            if AnalysisType.FACE_DETECTION in analysis_types:
                results['faces'] = await self._detect_faces(image_url, image_stream)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._process_image_results(
                results, image_url, analysis_types, processing_time
            )
            
        except Exception as e:
            raise CloudAIError(
                f"Azure AI Vision image analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Check Azure AI Vision service status."""
        try:
            if not self._vision_client:
                await self.initialize()
            
            start_time = datetime.utcnow()
            
            # Test with list models call
            models = self._vision_client.list_models()
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "available_models": len(models.models_property),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _extract_video_frames(self, video_url: str, max_frames: int = 10) -> List[bytes]:
        """Extract frames from video for analysis."""
        # Placeholder implementation - in production would use FFmpeg or similar
        # For now, return empty list (video analysis not fully implemented)
        logger.warning("Video frame extraction not implemented - returning empty frames")
        return []
    
    async def _analyze_frame(self, frame_data: bytes, analysis_types: List[AnalysisType], 
                           timestamp: float) -> Dict[str, Any]:
        """Analyze a single video frame."""
        # Convert frame to format suitable for Azure API
        import io
        frame_stream = io.BytesIO(frame_data)
        
        results = {}
        
        if AnalysisType.OCR in analysis_types:
            results['ocr'] = await self._perform_ocr_stream(frame_stream)
        
        if AnalysisType.LABEL_DETECTION in analysis_types:
            results['analyze'] = await self._analyze_image_content_stream(frame_stream)
        
        results['timestamp'] = timestamp
        return results
    
    async def _prepare_image_input(self, image_url: str) -> Optional[bytes]:
        """Prepare image input for Azure AI Vision."""
        if image_url.startswith(('http://', 'https://')):
            # For URL input, Azure can analyze directly
            return None
        else:
            # For local files, read content
            with open(image_url, 'rb') as image_file:
                return image_file.read()
    
    async def _perform_ocr(self, image_url: str, image_stream: Optional[bytes]) -> Dict[str, Any]:
        """Perform OCR using Azure Read API."""
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        import time
        
        # Start OCR operation
        if image_stream:
            # Use stream for local files
            import io
            read_response = self._vision_client.read_in_stream(
                io.BytesIO(image_stream), 
                raw=True
            )
        else:
            # Use URL for remote images
            read_response = self._vision_client.read(image_url, raw=True)
        
        # Get operation location
        operation_location = read_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]
        
        # Wait for operation completion
        max_wait_time = 30  # seconds
        elapsed = 0
        while elapsed < max_wait_time:
            result = self._vision_client.get_read_result(operation_id)
            if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                break
            time.sleep(1)
            elapsed += 1
        
        if result.status == OperationStatusCodes.succeeded:
            return {"read_result": result.analyze_result}
        else:
            raise CloudAIError(f"OCR operation failed with status: {result.status}")
    
    async def _perform_ocr_stream(self, image_stream) -> Dict[str, Any]:
        """Perform OCR on image stream."""
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        import time
        
        read_response = self._vision_client.read_in_stream(image_stream, raw=True)
        
        operation_location = read_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]
        
        # Wait for completion
        while True:
            result = self._vision_client.get_read_result(operation_id)
            if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
                break
            time.sleep(1)
        
        return {"read_result": result.analyze_result}
    
    async def _analyze_image_content(self, image_url: str, image_stream: Optional[bytes]) -> Dict[str, Any]:
        """Analyze image content for objects, categories, etc."""
        from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
        
        # Define features to analyze
        features = [
            VisualFeatureTypes.categories,
            VisualFeatureTypes.tags,
            VisualFeatureTypes.description,
            VisualFeatureTypes.objects,
            VisualFeatureTypes.brands
        ]
        
        if image_stream:
            import io
            result = self._vision_client.analyze_image_in_stream(
                io.BytesIO(image_stream),
                visual_features=features
            )
        else:
            result = self._vision_client.analyze_image(
                image_url,
                visual_features=features
            )
        
        return {"analyze_result": result}
    
    async def _analyze_image_content_stream(self, image_stream) -> Dict[str, Any]:
        """Analyze image content from stream."""
        from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
        
        features = [
            VisualFeatureTypes.categories,
            VisualFeatureTypes.tags,
            VisualFeatureTypes.objects
        ]
        
        result = self._vision_client.analyze_image_in_stream(
            image_stream,
            visual_features=features
        )
        
        return {"analyze_result": result}
    
    async def _detect_faces(self, image_url: str, image_stream: Optional[bytes]) -> Dict[str, Any]:
        """Detect faces in image."""
        if image_stream:
            import io
            result = self._vision_client.analyze_image_in_stream(
                io.BytesIO(image_stream),
                visual_features=[VisualFeatureTypes.faces]
            )
        else:
            from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
            result = self._vision_client.analyze_image(
                image_url,
                visual_features=[VisualFeatureTypes.faces]
            )
        
        return {"faces_result": result}
    
    def _aggregate_frame_results(self, frame_results: List[Dict[str, Any]], 
                               video_id: str, analysis_types: List[AnalysisType],
                               processing_time: float) -> VideoAnalysisResult:
        """Aggregate results from multiple video frames."""
        all_objects = []
        all_labels = []
        all_text = []
        all_faces = []
        
        for frame_result in frame_results:
            timestamp = frame_result.get('timestamp', 0)
            
            # Process OCR results
            if 'ocr' in frame_result:
                ocr_result = frame_result['ocr'].get('read_result', {})
                for page in ocr_result.get('read_results', []):
                    for line in page.get('lines', []):
                        all_text.append(DetectionResult(
                            label=line['text'],
                            confidence=1.0,  # Azure doesn't provide confidence for OCR
                            timestamp=timestamp,
                            bounding_box=self._convert_azure_bbox(line.get('bounding_box', []))
                        ))
            
            # Process analyze results
            if 'analyze' in frame_result:
                analyze_result = frame_result['analyze'].get('analyze_result')
                
                # Tags/Labels
                for tag in getattr(analyze_result, 'tags', []):
                    all_labels.append(DetectionResult(
                        label=tag.name,
                        confidence=tag.confidence,
                        timestamp=timestamp
                    ))
                
                # Objects
                for obj in getattr(analyze_result, 'objects', []):
                    all_objects.append(DetectionResult(
                        label=obj.object_property,
                        confidence=obj.confidence,
                        timestamp=timestamp,
                        bounding_box={
                            'x': obj.rectangle.x / analyze_result.metadata.width,
                            'y': obj.rectangle.y / analyze_result.metadata.height,
                            'width': obj.rectangle.w / analyze_result.metadata.width,
                            'height': obj.rectangle.h / analyze_result.metadata.height
                        }
                    ))
                
                # Faces
                for face in getattr(analyze_result, 'faces', []):
                    all_faces.append(DetectionResult(
                        label="Face",
                        confidence=1.0,
                        timestamp=timestamp,
                        bounding_box={
                            'x': face.face_rectangle.left / analyze_result.metadata.width,
                            'y': face.face_rectangle.top / analyze_result.metadata.height,
                            'width': face.face_rectangle.width / analyze_result.metadata.width,
                            'height': face.face_rectangle.height / analyze_result.metadata.height
                        },
                        metadata={
                            'age': face.age,
                            'gender': face.gender
                        }
                    ))
        
        return VideoAnalysisResult(
            provider=self.provider,
            video_id=video_id,
            analysis_types=analysis_types,
            objects=all_objects,
            labels=all_labels,
            text_detections=all_text,
            faces=all_faces,
            logos=[],
            shots=[],
            scenes=[],
            processing_time=processing_time,
            raw_response={"frame_results": frame_results}
        )
    
    def _process_image_results(self, results: Dict[str, Any], image_id: str,
                             analysis_types: List[AnalysisType],
                             processing_time: float) -> VideoAnalysisResult:
        """Process Azure AI Vision image analysis results."""
        objects = []
        labels = []
        text_detections = []
        faces = []
        
        # Process OCR results
        if 'ocr' in results:
            ocr_result = results['ocr'].get('read_result', {})
            for page in ocr_result.get('read_results', []):
                for line in page.get('lines', []):
                    text_detections.append(DetectionResult(
                        label=line['text'],
                        confidence=1.0,
                        bounding_box=self._convert_azure_bbox(line.get('bounding_box', []))
                    ))
        
        # Process analyze results
        if 'analyze' in results:
            analyze_result = results['analyze'].get('analyze_result')
            
            # Tags/Labels
            for tag in getattr(analyze_result, 'tags', []):
                labels.append(DetectionResult(
                    label=tag.name,
                    confidence=tag.confidence
                ))
            
            # Objects
            for obj in getattr(analyze_result, 'objects', []):
                if hasattr(analyze_result, 'metadata') and analyze_result.metadata:
                    width = analyze_result.metadata.width
                    height = analyze_result.metadata.height
                    objects.append(DetectionResult(
                        label=obj.object_property,
                        confidence=obj.confidence,
                        bounding_box={
                            'x': obj.rectangle.x / width,
                            'y': obj.rectangle.y / height,
                            'width': obj.rectangle.w / width,
                            'height': obj.rectangle.h / height
                        }
                    ))
        
        # Process face results
        if 'faces' in results:
            faces_result = results['faces'].get('faces_result')
            for face in getattr(faces_result, 'faces', []):
                if hasattr(faces_result, 'metadata') and faces_result.metadata:
                    width = faces_result.metadata.width
                    height = faces_result.metadata.height
                    faces.append(DetectionResult(
                        label="Face",
                        confidence=1.0,
                        bounding_box={
                            'x': face.face_rectangle.left / width,
                            'y': face.face_rectangle.top / height,
                            'width': face.face_rectangle.width / width,
                            'height': face.face_rectangle.height / height
                        },
                        metadata={
                            'age': face.age,
                            'gender': face.gender
                        }
                    ))
        
        return VideoAnalysisResult(
            provider=self.provider,
            video_id=image_id,
            analysis_types=analysis_types,
            objects=objects,
            labels=labels,
            text_detections=text_detections,
            faces=faces,
            logos=[],
            shots=[],
            scenes=[],
            processing_time=processing_time,
            raw_response=results
        )
    
    def _convert_azure_bbox(self, bbox_array: List[float]) -> Dict[str, float]:
        """Convert Azure bounding box array to standard format."""
        if len(bbox_array) >= 8:
            # Azure returns [x1, y1, x2, y2, x3, y3, x4, y4]
            x_coords = [bbox_array[i] for i in range(0, len(bbox_array), 2)]
            y_coords = [bbox_array[i] for i in range(1, len(bbox_array), 2)]
            
            return {
                'x': min(x_coords),
                'y': min(y_coords),
                'width': max(x_coords) - min(x_coords),
                'height': max(y_coords) - min(y_coords)
            }
        
        return {'x': 0, 'y': 0, 'width': 0, 'height': 0}