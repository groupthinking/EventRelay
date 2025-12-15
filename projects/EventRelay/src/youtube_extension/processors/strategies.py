#!/usr/bin/env python3
"""
Video Processing Strategies
===========================

This module defines the different strategies for video processing,
consolidated from the previous `optimized_video_processor`,
`parallel_video_processor`, and `enhanced_extractor` modules.
"""

import asyncio
import json
import logging
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re
import httpx

# Video processing imports
from youtube_extension.utils import extract_video_id
try:
    from google.cloud import videointelligence
    HAS_VIDEO_DEPS = True
except ImportError as e:
    HAS_VIDEO_DEPS = False
    logging.error(f"Video dependencies not available: {e}")

# AI processing imports
try:
    import google.generativeai as genai
    HAS_AI_DEPS = True
except ImportError:
    HAS_AI_DEPS = False
    logging.warning("AI dependencies (google-generativeai) not available")

# Data processing
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [VideoExtractor] %(message)s'
)
logger = logging.getLogger(__name__)

# Simple cache implementation for optimized strategy
_cache = {}

async def cache_get(key: str) -> Optional[Dict[str, Any]]:
    """Simple in-memory cache get operation"""
    return _cache.get(key)

async def cache_set(key: str, value: Dict[str, Any], ttl: int = 3600, tags: List[str] = None) -> None:
    """Simple in-memory cache set operation"""
    _cache[key] = value
    # In production, implement proper TTL and tag management

class VideoSource(Enum):
    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    LOCAL_FILE = "local"
    URL = "url"

class ProcessingStage(Enum):
    EXTRACTION = "extraction"
    TRANSCRIPTION = "transcription"
    ANALYSIS = "analysis"
    TRANSFER = "transfer"
    COMPLETE = "complete"

@dataclass
class VideoMetadata:
    """Comprehensive video metadata structure"""
    video_id: str
    title: str
    description: str
    duration: int
    upload_date: str
    uploader: str
    view_count: int
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    tags: List[str] = None
    thumbnail_url: str = ""
    language: str = "en"
    source: VideoSource = VideoSource.YOUTUBE

@dataclass
class TranscriptSegment:
    """Individual transcript segment with timing"""
    text: str
    start: float
    duration: float
    end: float = None
    
    def __post_init__(self):
        if self.end is None:
            self.end = self.start + self.duration

@dataclass
class VideoContent:
    """Complete video content package"""
    metadata: VideoMetadata
    transcript: List[TranscriptSegment]
    summary: Optional[str] = None
    key_points: List[str] = None
    topics: List[str] = None
    sentiment: Optional[str] = None
    processing_stage: ProcessingStage = ProcessingStage.EXTRACTION
    processing_time: float = 0.0
    error_log: List[str] = None

from abc import ABC, abstractmethod

# A simple registry for the strategies
_processor_strategies = {}

def register_strategy(name: str):
    """A decorator to register a new processing strategy."""
    def decorator(cls):
        _processor_strategies[name] = cls
        return cls
    return decorator

def get_strategy(name: str):
    """Retrieves a processing strategy from the registry."""
    if name not in _processor_strategies:
        raise ValueError(f"Unknown processing strategy: {name}")
    return _processor_strategies[name]

class ProcessorStrategy(ABC):
    """
    Abstract base class for a video processing strategy.
    """
    @abstractmethod
    async def process_video(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a single video and return the results.
        """
        pass

    async def process_batch(self, video_urls: List[str], options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Process a batch of videos.
        The default implementation processes them concurrently.
        """
        results = await asyncio.gather(
            *[self.process_video(url, options) for url in video_urls]
        )
        return results

@register_strategy("optimized")
class OptimizedStrategy(ProcessorStrategy):
    """
    A high-performance video processing strategy that uses parallelism,
    caching, and other optimizations.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.processing_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processed': 0
        }
        # Initialize enhanced strategy for delegation
        self._enhanced_strategy = None
    async def process_video(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process video with all optimizations enabled
        """
        start_time = time.time()
        processing_id = hashlib.md5(f"{video_url}_{time.time()}".encode()).hexdigest()[:8]
        
        logger.info(f"🎯 Processing video (optimized): {video_url[:50]}... [ID: {processing_id}]")
        
        try:
            # Check cache first
            cache_key = f"optimized_video:{hashlib.md5(video_url.encode()).hexdigest()}"
            cached_result = await cache_get(cache_key)

            if cached_result and self.config.get('enable_intelligent_caching', True):
                self.processing_stats['cache_hits'] += 1
                logger.info(f"✅ Cache hit for video processing [ID: {processing_id}]")
                return cached_result

            self.processing_stats['cache_misses'] += 1

            # Initialize enhanced strategy if not already done
            if self._enhanced_strategy is None:
                self._enhanced_strategy = EnhancedStrategy(self.config)

            # Use enhanced strategy for actual processing
            result = await self._enhanced_strategy.process_video(video_url, options)

            # Add optimization metadata
            if result:
                result['optimization_applied'] = True
                result['processing_id'] = processing_id

            # Cache successful results
            if result and not result.get('error_log'):
                await cache_set(cache_key, result, ttl=3600, tags=["video_processing"])

            processing_time = time.time() - start_time
            self.processing_stats['total_processed'] += 1

            logger.info(f"✅ Video processed in {processing_time:.2f}s [ID: {processing_id}]")

            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Video processing failed after {processing_time:.2f}s: {e} [ID: {processing_id}]")
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': processing_time,
                'processing_id': processing_id
            }

@register_strategy("parallel")
class ParallelStrategy(ProcessorStrategy):
    """
    A video processing strategy that uses a task queue and a pool of workers
    to process videos in parallel.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.max_workers = self.config.get("max_workers", 4)
        self.semaphore = asyncio.Semaphore(self.max_workers)
        # Use enhanced strategy for actual processing
        self._enhanced_strategy = None

    async def process_video(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a single video with resource limiting."""
        async with self.semaphore:
            # Initialize enhanced strategy if not already done
            if self._enhanced_strategy is None:
                self._enhanced_strategy = EnhancedStrategy(self.config)

            start_time = time.time()
            processing_id = hashlib.md5(f"{video_url}_{time.time()}".encode()).hexdigest()[:8]

            logger.info(f"🔄 Processing video (parallel): {video_url[:50]}... [ID: {processing_id}] [Workers: {self.max_workers}]")

            try:
                result = await self._enhanced_strategy.process_video(video_url, options)

                # Add parallel processing metadata
                if result:
                    result['parallel_processed'] = True
                    result['processing_id'] = processing_id
                    result['max_workers'] = self.max_workers

                processing_time = time.time() - start_time
                logger.info(f"✅ Parallel video processed in {processing_time:.2f}s [ID: {processing_id}]")

                return result

            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"❌ Parallel video processing failed after {processing_time:.2f}s: {e} [ID: {processing_id}]")

                return {
                    'success': False,
                    'error': str(e),
                    'processing_time': processing_time,
                    'processing_id': processing_id,
                    'parallel_processed': True
                }

    async def process_batch(self, video_urls: List[str], options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Process a batch of videos in parallel with controlled concurrency."""
        logger.info(f"🚀 Starting parallel batch processing: {len(video_urls)} videos, max {self.max_workers} workers")

        start_time = time.time()

        # Process all videos concurrently with semaphore limiting
        tasks = [self.process_video(url, options) for url in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception processing video {video_urls[i]}: {result}")
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'video_url': video_urls[i],
                    'parallel_processed': True
                })
            else:
                processed_results.append(result)

        total_time = time.time() - start_time
        successful = sum(1 for r in processed_results if not r.get('error'))

        logger.info(f"✅ Parallel batch completed: {successful}/{len(video_urls)} successful in {total_time:.2f}s")

        return processed_results

@register_strategy("enhanced")
class EnhancedStrategy(ProcessorStrategy):
    """
    An enhanced video processing strategy that extracts metadata,
    transcript, and performs AI analysis.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        if HAS_VIDEO_DEPS:
            self.video_client = videointelligence.VideoIntelligenceServiceClient()
        if HAS_AI_DEPS:
            gemini_api_key = self.config.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("Gemini API key is not configured.")
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
    async def process_video(self, video_url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete video processing pipeline"""
        start_time = time.time()
        
        try:
            # Extract video ID
            video_id = extract_video_id(video_url)
            if not video_id:
                raise ValueError(f"Could not extract video ID from {video_url}")
            
            logger.info(f"Processing video: {video_id}")
            
            # Extract metadata
            metadata = await self.extract_video_metadata(video_id)
            
            # Extract transcript
            transcript = await self.extract_transcript(video_id, options.get("languages"))
            
            # Analyze content
            analysis = await self.analyze_content(transcript)
            
            # Create video content object
            content = VideoContent(
                metadata=metadata,
                transcript=transcript,
                summary=analysis.get('summary'),
                key_points=analysis.get('key_points', []),
                topics=analysis.get('topics', []),
                sentiment=analysis.get('sentiment'),
                processing_stage=ProcessingStage.COMPLETE,
                processing_time=time.time() - start_time
            )
            
            logger.info(f"Successfully processed video {video_id} in {content.processing_time:.2f}s")
            return asdict(content)
            
        except Exception as e:
            logger.info(f"Video processing failed for {video_url}: {e}")
            
            # Return partial content with error
            content = VideoContent(
                metadata=VideoMetadata(
                    video_id=video_id or "unknown",
                    title="Processing Failed",
                    description="",
                    duration=0,
                    upload_date="",
                    uploader="",
                    view_count=0
                ),
                transcript=[],
                processing_stage=ProcessingStage.EXTRACTION,
                processing_time=time.time() - start_time,
                error_log=[str(e)]
            )
            
            return asdict(content)

    async def extract_video_metadata(self, video_id: str) -> VideoMetadata:
        """Extract comprehensive video metadata using Vertex AI"""
        if not HAS_VIDEO_DEPS:
            raise ValueError("Video dependencies not available")

        video_uri = f"gs://youtube_videos/{video_id}.mp4"  # Assuming videos are in GCS

        features = [
            videointelligence.Feature.LABEL_DETECTION,
            videointelligence.Feature.SHOT_CHANGE_DETECTION,
            videointelligence.Feature.EXPLICIT_CONTENT_DETECTION,
        ]

        request = videointelligence.AnnotateVideoRequest(
            input_uri=video_uri,
            features=features,
        )

        operation = self.video_client.annotate_video(request=request)
        result = operation.result(timeout=90)
        
        annotation_results = result.annotation_results[0]
        
        # This is a simplified mapping. A real implementation would need to
        # extract more details from the annotation results.
        metadata = VideoMetadata(
            video_id=video_id,
            title=Path(video_uri).stem,
            description="",
            duration=int(annotation_results.shot_annotations[-1].end_time_offset.total_seconds()) if annotation_results.shot_annotations else 0,
            upload_date="",
            uploader="",
            view_count=0,
            tags=[label.entity.description for label in annotation_results.segment_label_annotations],
        )
        return metadata

    async def extract_transcript(self, video_id: str, languages: List[str] = None) -> List[TranscriptSegment]:
        """Extract transcript using Vertex AI Video Intelligence"""
        if not HAS_VIDEO_DEPS:
            raise ValueError("Video dependencies not available")

        video_uri = f"gs://youtube_videos/{video_id}.mp4"  # Assuming videos are in GCS

        video_context = videointelligence.VideoContext(
            speech_transcription_config=videointelligence.SpeechTranscriptionConfig(
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
        )

        request = videointelligence.AnnotateVideoRequest(
            input_uri=video_uri,
            features=[videointelligence.Feature.SPEECH_TRANSCRIPTION],
            video_context=video_context,
        )

        operation = self.video_client.annotate_video(request=request)
        result = operation.result(timeout=180)

        segments = []
        for result in result.annotation_results:
            for transcription in result.speech_transcriptions:
                for alternative in transcription.alternatives:
                    for i, word in enumerate(alternative.words):
                        segments.append(
                            TranscriptSegment(
                                text=word.word,
                                start=word.start_time.total_seconds(),
                                duration=(word.end_time - word.start_time).total_seconds(),
                            )
                        )
        return segments

    async def analyze_content(self, transcript: List[TranscriptSegment]) -> Dict[str, Any]:
        """Analyze video content using Gemini"""
        if not HAS_AI_DEPS:
            logger.warning("AI components not available for content analysis")
            return {}
        
        full_text = " ".join([segment.text for segment in transcript])
        
        prompt = f"""
        Analyze the following video transcript and provide a summary, key points, topics, and sentiment.
        
        Transcript:
        {full_text}
        
        Format your response as a JSON object with the following keys:
        - "summary": A brief summary of the video content.
        - "key_points": A list of key points.
        - "topics": A list of topics discussed.
        - "sentiment": The overall sentiment of the video (e.g., "positive", "negative", "neutral").
        """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {"error": str(e)}

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text using simple heuristics"""
        sentences = text.split('.')
        key_points = []
        
        # Look for sentences with key indicators
        indicators = ['important', 'key', 'main', 'primary', 'essential', 'crucial', 'significant']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(indicator in sentence.lower() for indicator in indicators):
                key_points.append(sentence)
        
        return key_points[:5]  # Limit to top 5

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics using simple keyword frequency"""
        # Simple topic extraction - in production, use more sophisticated NLP
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter common words
        stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said', 'what', 'when', 'where', 'more', 'some', 'like', 'into', 'time', 'very', 'make', 'than', 'many', 'over', 'such', 'only', 'know', 'just', 'first', 'also', 'after', 'back', 'other', 'well', 'come', 'could', 'would', 'should', 'think', 'people', 'really', 'going', 'about', 'because', 'through', 'before', 'being', 'between', 'during', 'without', 'around', 'something', 'everything'}
        
        filtered_words = [word for word in words if word not in stop_words and len(word) > 4]
        
        # Count frequency
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top topics
        sorted_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [topic[0] for topic in sorted_topics[:10]]