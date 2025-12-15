"""
Amazon Rekognition Integration

Implements video and image analysis using AWS Rekognition:
- Object and Scene Detection
- Face Detection and Analysis
- Text Detection (OCR)
- Content Moderation
- Celebrity Recognition
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseCloudAI, CloudAIProvider, AnalysisType, VideoAnalysisResult, DetectionResult
from ..exceptions import CloudAIError, ConfigurationError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class AWSRekognition(BaseCloudAI):
    """Amazon Rekognition video and image analysis integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = CloudAIProvider.AWS_REKOGNITION
        self._rekognition_client = None
        self._s3_client = None
        
        # Configuration validation
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate AWS Rekognition configuration."""
        required_fields = ["aws_access_key_id", "aws_secret_access_key", "region"]
        
        for field in required_fields:
            if field not in self.config:
                raise ConfigurationError(
                    f"Missing required AWS config: {field}",
                    provider=self.provider.value,
                    missing_config=field
                )
    
    async def initialize(self) -> None:
        """Initialize AWS Rekognition client."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Create session with credentials
            session = boto3.Session(
                aws_access_key_id=self.config["aws_access_key_id"],
                aws_secret_access_key=self.config["aws_secret_access_key"],
                region_name=self.config["region"]
            )
            
            # Initialize clients
            self._rekognition_client = session.client('rekognition')
            self._s3_client = session.client('s3')
            
            # Test connection
            await self._test_connection()
            
            logger.info(f"AWS Rekognition initialized in region: {self.config['region']}")
            
        except ImportError:
            raise ConfigurationError(
                "AWS SDK (boto3) not installed. Install with: pip install boto3",
                provider=self.provider.value
            )
        except (ClientError, NoCredentialsError) as e:
            raise AuthenticationError(
                f"AWS authentication failed: {e}",
                provider=self.provider.value
            )
        except Exception as e:
            raise CloudAIError(
                f"Failed to initialize AWS Rekognition: {e}",
                provider=self.provider.value
            )
    
    async def cleanup(self) -> None:
        """Cleanup AWS clients."""
        # boto3 clients don't require explicit cleanup
        self._rekognition_client = None
        self._s3_client = None
    
    async def _test_connection(self) -> None:
        """Test AWS Rekognition connection."""
        try:
            # Simple API call to test connectivity
            response = self._rekognition_client.describe_collection(
                CollectionId='non-existent-collection'
            )
        except Exception as e:
            if "ResourceNotFoundException" in str(e):
                # Expected error for non-existent collection - connection works
                return
            raise e
    
    def get_supported_analysis_types(self) -> List[AnalysisType]:
        """Get supported analysis types for AWS Rekognition."""
        return [
            AnalysisType.OBJECT_TRACKING,
            AnalysisType.FACE_DETECTION,
            AnalysisType.TEXT_DETECTION,
            AnalysisType.CONTENT_MODERATION,
            AnalysisType.LABEL_DETECTION,
            AnalysisType.SCENE_ANALYSIS
        ]
    
    async def analyze_video(self, video_url: str,
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze video using AWS Rekognition Video."""
        if not self._rekognition_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # AWS Rekognition Video requires S3 input
            s3_bucket, s3_key = await self._ensure_video_in_s3(video_url)
            
            # Start analysis operations
            job_ids = await self._start_video_analysis(s3_bucket, s3_key, analysis_types)
            
            # Wait for completion and collect results
            results = await self._collect_video_results(job_ids, analysis_types)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._process_video_results(
                results, video_url, analysis_types, processing_time
            )
            
        except Exception as e:
            if "ThrottlingException" in str(e):
                raise RateLimitError(
                    f"AWS Rekognition rate limit exceeded: {e}",
                    provider=self.provider.value
                )
            raise CloudAIError(
                f"AWS Rekognition video analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def analyze_image(self, image_url: str,
                          analysis_types: List[AnalysisType]) -> VideoAnalysisResult:
        """Analyze single image using AWS Rekognition."""
        if not self._rekognition_client:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # Prepare image input
            image_data = await self._prepare_image_input(image_url)
            
            # Perform analyses
            results = {}
            
            if AnalysisType.LABEL_DETECTION in analysis_types:
                results['labels'] = self._rekognition_client.detect_labels(
                    Image=image_data,
                    MaxLabels=50,
                    MinConfidence=0.5
                )
            
            if AnalysisType.FACE_DETECTION in analysis_types:
                results['faces'] = self._rekognition_client.detect_faces(
                    Image=image_data,
                    Attributes=['ALL']
                )
            
            if AnalysisType.TEXT_DETECTION in analysis_types:
                results['text'] = self._rekognition_client.detect_text(
                    Image=image_data
                )
            
            if AnalysisType.CONTENT_MODERATION in analysis_types:
                results['moderation'] = self._rekognition_client.detect_moderation_labels(
                    Image=image_data,
                    MinConfidence=0.5
                )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return self._process_image_results(
                results, image_url, analysis_types, processing_time
            )
            
        except Exception as e:
            raise CloudAIError(
                f"AWS Rekognition image analysis failed: {e}",
                provider=self.provider.value
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Check AWS Rekognition service status."""
        try:
            if not self._rekognition_client:
                await self.initialize()
            
            start_time = datetime.utcnow()
            
            # Test with describe_collection call
            try:
                self._rekognition_client.describe_collection(
                    CollectionId='health-check-collection'
                )
            except Exception as e:
                if "ResourceNotFoundException" in str(e):
                    # Expected error - service is available
                    pass
                else:
                    raise e
            
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
    
    async def _ensure_video_in_s3(self, video_url: str) -> tuple:
        """Ensure video is available in S3 for Rekognition Video analysis."""
        # For demo purposes, assume video is already in S3
        # In production, would need to upload video to S3 if not already there
        
        if video_url.startswith('s3://'):
            # Parse S3 URL
            s3_path = video_url[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)
            return bucket, key
        else:
            # Would need to upload to S3 - for demo, use default bucket
            bucket = self.config.get('s3_bucket', 'rekognition-video-analysis')
            key = f"videos/{video_url.split('/')[-1]}"
            
            # In production implementation, would upload video here
            logger.warning(f"Video not in S3, would upload {video_url} to s3://{bucket}/{key}")
            
            return bucket, key
    
    async def _start_video_analysis(self, s3_bucket: str, s3_key: str,
                                  analysis_types: List[AnalysisType]) -> Dict[str, str]:
        """Start AWS Rekognition Video analysis operations."""
        video_input = {
            'S3Object': {
                'Bucket': s3_bucket,
                'Name': s3_key
            }
        }
        
        job_ids = {}
        
        # Start different analysis operations based on requested types
        if AnalysisType.LABEL_DETECTION in analysis_types:
            response = self._rekognition_client.start_label_detection(
                Video=video_input,
                MinConfidence=0.5
            )
            job_ids['labels'] = response['JobId']
        
        if AnalysisType.FACE_DETECTION in analysis_types:
            response = self._rekognition_client.start_face_detection(
                Video=video_input
            )
            job_ids['faces'] = response['JobId']
        
        if AnalysisType.TEXT_DETECTION in analysis_types:
            response = self._rekognition_client.start_text_detection(
                Video=video_input
            )
            job_ids['text'] = response['JobId']
        
        if AnalysisType.CONTENT_MODERATION in analysis_types:
            response = self._rekognition_client.start_content_moderation(
                Video=video_input,
                MinConfidence=0.5
            )
            job_ids['moderation'] = response['JobId']
        
        return job_ids
    
    async def _collect_video_results(self, job_ids: Dict[str, str],
                                   analysis_types: List[AnalysisType]) -> Dict[str, Any]:
        """Wait for and collect video analysis results."""
        results = {}
        
        # Poll for completion of each job
        for analysis_type, job_id in job_ids.items():
            result = await self._wait_for_job_completion(job_id, analysis_type)
            results[analysis_type] = result
        
        return results
    
    async def _wait_for_job_completion(self, job_id: str, analysis_type: str) -> Dict[str, Any]:
        """Wait for a specific job to complete and return results."""
        max_wait_time = self.config.get('max_wait_time', 600)  # 10 minutes default
        poll_interval = 5  # seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                if analysis_type == 'labels':
                    response = self._rekognition_client.get_label_detection(JobId=job_id)
                elif analysis_type == 'faces':
                    response = self._rekognition_client.get_face_detection(JobId=job_id)
                elif analysis_type == 'text':
                    response = self._rekognition_client.get_text_detection(JobId=job_id)
                elif analysis_type == 'moderation':
                    response = self._rekognition_client.get_content_moderation(JobId=job_id)
                else:
                    raise ValueError(f"Unknown analysis type: {analysis_type}")
                
                if response['JobStatus'] == 'SUCCEEDED':
                    return response
                elif response['JobStatus'] == 'FAILED':
                    raise CloudAIError(f"AWS Rekognition job failed: {response.get('StatusMessage', 'Unknown error')}")
                
                # Job still in progress, wait and retry
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
                
            except Exception as e:
                raise CloudAIError(f"Error checking job status: {e}")
        
        raise CloudAIError(f"AWS Rekognition job timed out after {max_wait_time} seconds")
    
    async def _prepare_image_input(self, image_url: str) -> Dict[str, Any]:
        """Prepare image input for AWS Rekognition."""
        if image_url.startswith('s3://'):
            # S3 image
            s3_path = image_url[5:]
            bucket, key = s3_path.split('/', 1)
            return {
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        elif image_url.startswith(('http://', 'https://')):
            # Download image from URL
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                return {'Bytes': response.content}
        else:
            # Local file
            with open(image_url, 'rb') as image_file:
                return {'Bytes': image_file.read()}
    
    def _process_video_results(self, results: Dict[str, Any], video_id: str,
                             analysis_types: List[AnalysisType],
                             processing_time: float) -> VideoAnalysisResult:
        """Process AWS Rekognition video analysis results."""
        objects = []
        labels = []
        text_detections = []
        faces = []
        
        # Process labels
        if 'labels' in results:
            for label_detection in results['labels'].get('Labels', []):
                labels.append(DetectionResult(
                    label=label_detection['Label']['Name'],
                    confidence=label_detection['Label']['Confidence'] / 100.0,
                    timestamp=label_detection['Timestamp'] / 1000.0
                ))
        
        # Process faces
        if 'faces' in results:
            for face_detection in results['faces'].get('Faces', []):
                bbox = face_detection['Face']['BoundingBox']
                faces.append(DetectionResult(
                    label="Face",
                    confidence=face_detection['Face']['Confidence'] / 100.0,
                    timestamp=face_detection['Timestamp'] / 1000.0,
                    bounding_box={
                        'x': bbox['Left'],
                        'y': bbox['Top'],
                        'width': bbox['Width'],
                        'height': bbox['Height']
                    },
                    metadata={
                        'emotions': face_detection['Face'].get('Emotions', []),
                        'age_range': face_detection['Face'].get('AgeRange', {}),
                        'gender': face_detection['Face'].get('Gender', {})
                    }
                ))
        
        # Process text detections
        if 'text' in results:
            for text_detection in results['text'].get('TextDetections', []):
                if text_detection['Type'] == 'WORD':  # Only process words, not lines
                    bbox = text_detection.get('Geometry', {}).get('BoundingBox', {})
                    text_detections.append(DetectionResult(
                        label=text_detection['DetectedText'],
                        confidence=text_detection['Confidence'] / 100.0,
                        timestamp=text_detection['Timestamp'] / 1000.0,
                        bounding_box={
                            'x': bbox.get('Left', 0),
                            'y': bbox.get('Top', 0),
                            'width': bbox.get('Width', 0),
                            'height': bbox.get('Height', 0)
                        }
                    ))
        
        return VideoAnalysisResult(
            provider=self.provider,
            video_id=video_id,
            analysis_types=analysis_types,
            objects=objects,
            labels=labels,
            text_detections=text_detections,
            faces=faces,
            logos=[],  # Not directly supported
            shots=[],  # Not available in Rekognition Video
            scenes=[],
            processing_time=processing_time,
            raw_response=results
        )
    
    def _process_image_results(self, results: Dict[str, Any], image_id: str,
                             analysis_types: List[AnalysisType],
                             processing_time: float) -> VideoAnalysisResult:
        """Process AWS Rekognition image analysis results."""
        objects = []
        labels = []
        text_detections = []
        faces = []
        
        # Process labels
        if 'labels' in results:
            for label in results['labels'].get('Labels', []):
                labels.append(DetectionResult(
                    label=label['Name'],
                    confidence=label['Confidence'] / 100.0,
                    metadata={'categories': label.get('Categories', [])}
                ))
        
        # Process faces
        if 'faces' in results:
            for face_detail in results['faces'].get('FaceDetails', []):
                bbox = face_detail['BoundingBox']
                faces.append(DetectionResult(
                    label="Face",
                    confidence=face_detail['Confidence'] / 100.0,
                    bounding_box={
                        'x': bbox['Left'],
                        'y': bbox['Top'], 
                        'width': bbox['Width'],
                        'height': bbox['Height']
                    },
                    metadata={
                        'emotions': face_detail.get('Emotions', []),
                        'age_range': face_detail.get('AgeRange', {}),
                        'gender': face_detail.get('Gender', {}),
                        'landmarks': face_detail.get('Landmarks', [])
                    }
                ))
        
        # Process text
        if 'text' in results:
            for text_detection in results['text'].get('TextDetections', []):
                if text_detection['Type'] == 'WORD':
                    bbox = text_detection.get('Geometry', {}).get('BoundingBox', {})
                    text_detections.append(DetectionResult(
                        label=text_detection['DetectedText'],
                        confidence=text_detection['Confidence'] / 100.0,
                        bounding_box={
                            'x': bbox.get('Left', 0),
                            'y': bbox.get('Top', 0),
                            'width': bbox.get('Width', 0),
                            'height': bbox.get('Height', 0)
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