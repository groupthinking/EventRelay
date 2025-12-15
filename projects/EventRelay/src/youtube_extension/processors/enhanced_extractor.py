#!/usr/bin/env python3
"""
Enhanced Video Extractor with Integrated Processing Pipeline
Combines extraction and transfer processes from multiple video processing approaches
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re
import httpx

from youtube_extension.utils import extract_video_id, parse_duration_to_seconds

# Video processing imports
try:
    from youtube_transcript_api import get_transcript
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript, NoTranscriptFound
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import yt_dlp
    HAS_VIDEO_DEPS = True
except ImportError as e:
    HAS_VIDEO_DEPS = False
    logging.error(f"Video dependencies not available: {e}")

# AI processing imports
try:
    import openai
    from transformers import pipeline
    import torch
    HAS_AI_DEPS = True
except ImportError:
    HAS_AI_DEPS = False
    logging.warning("AI dependencies not available")

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

class EnhancedVideoExtractor:
    """
    Enhanced video extractor integrating multiple processing approaches
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.youtube_api_key = self.config.get('youtube_api_key') or os.getenv('YOUTUBE_API_KEY')
        self.openai_api_key = self.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        
        # Initialize YouTube API client
        if self.youtube_api_key and HAS_VIDEO_DEPS:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API: {e}")
                self.youtube = None
        else:
            self.youtube = None
        
        # Initialize AI components
        if HAS_AI_DEPS and self.openai_api_key:
            openai.api_key = self.openai_api_key
            try:
                self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", use_safetensors=True)
                self.sentiment_analyzer = pipeline("sentiment-analysis", use_safetensors=True)
            except Exception as e:
                logger.error(f"Failed to initialize AI pipelines: {e}")
                self.summarizer = None
                self.sentiment_analyzer = None
        else:
            self.summarizer = None
            self.sentiment_analyzer = None
    
    async def extract_video_metadata(self, video_id: str) -> VideoMetadata:
        """Extract comprehensive video metadata"""
        if not self.youtube:
            # Add a clear error message if the API key is missing
            if not self.youtube_api_key:
                raise ValueError("YouTube API key is not set. Please set the YOUTUBE_API_KEY environment variable.")
            raise ValueError("YouTube API not available")
        
        try:
            response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()
            
            if not response['items']:
                raise ValueError(f"Video {video_id} not found")
            
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item['contentDetails']
            
            # Parse duration (PT format)
            duration_str = content_details['duration']
            duration = parse_duration_to_seconds(duration_str)
            
            metadata = VideoMetadata(
                video_id=video_id,
                title=snippet['title'],
                description=snippet['description'],
                duration=duration,
                upload_date=snippet['publishedAt'],
                uploader=snippet['channelTitle'],
                view_count=int(statistics.get('viewCount', 0)),
                like_count=int(statistics.get('likeCount', 0)),
                comment_count=int(statistics.get('commentCount', 0)),
                tags=snippet.get('tags', []),
                thumbnail_url=snippet['thumbnails']['high']['url'],
                language=snippet.get('defaultLanguage', 'en'),
                source=VideoSource.YOUTUBE
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata for {video_id}: {e}")
            raise
    
    async def extract_transcript(self, video_id: str, languages: List[str] = None) -> List[TranscriptSegment]:
        """Extract transcript using the new youtube-caption-extractor service"""
        if not HAS_VIDEO_DEPS:
            raise ValueError("Video dependencies not available")

        languages = languages or ['en']
        lang_code = languages[0]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:3000/api/captions",
                    json={"videoInput": video_id, "lang": lang_code},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    raise ValueError(f"Caption extraction failed: {data.get('error', 'Unknown error')}")

                subtitles = data.get("data", {}).get("subtitles", [])
                if not subtitles:
                    raise NoTranscriptFound(f"No transcript found for video {video_id} with language {lang_code}")

                segments = []
                for item in subtitles:
                    segments.append(TranscriptSegment(
                        text=item['text'].strip(),
                        start=float(item['start']),
                        duration=float(item['dur'])
                    ))
                
                return segments

        except httpx.RequestError as e:
            logger.error(f"HTTP request to caption extractor failed: {e}")
            raise ValueError(f"Could not connect to the caption extractor service at http://localhost:3000.")
        except Exception as e:
            logger.error(f"Failed to extract transcript for {video_id}: {e}")
            raise
    
    async def analyze_content(self, transcript: List[TranscriptSegment]) -> Dict[str, Any]:
        """Analyze video content using AI"""
        if not self.summarizer or not self.sentiment_analyzer:
            logger.warning("AI components not available for content analysis")
            return {}
        
        # Combine transcript text
        full_text = " ".join([segment.text for segment in transcript])
        
        analysis = {}
        
        try:
            # Generate summary
            if len(full_text) > 1000:  # Only summarize if text is substantial
                summary_result = self.summarizer(full_text, max_length=150, min_length=50, do_sample=False)
                analysis['summary'] = summary_result[0]['summary_text']
            else:
                analysis['summary'] = full_text[:200] + "..." if len(full_text) > 200 else full_text
            
            # Analyze sentiment
            sentiment_result = self.sentiment_analyzer(full_text[:512])  # Limit for model
            analysis['sentiment'] = sentiment_result[0]['label'].lower()
            analysis['sentiment_score'] = sentiment_result[0]['score']
            
            # Extract key topics (simple keyword extraction)
            analysis['key_points'] = self._extract_key_points(full_text)
            analysis['topics'] = self._extract_topics(full_text)
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
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
    
    async def process_video(self, video_url: str, languages: List[str] = None) -> VideoContent:
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
            transcript = await self.extract_transcript(video_id, languages)
            
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
            return content
            
        except Exception as e:
            logger.error(f"Video processing failed for {video_url}: {e}")
            
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
            
            return content
    
    async def batch_process_videos(self, video_urls: List[str], max_concurrent: int = 3) -> List[VideoContent]:
        """Process multiple videos concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(url):
            async with semaphore:
                return await self.process_video(url)
        
        tasks = [process_single(url) for url in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {video_urls[i]}: {result}")
                # Create error content
                error_content = VideoContent(
                    metadata=VideoMetadata(
                        video_id="error",
                        title=f"Error processing {video_urls[i]}",
                        description="",
                        duration=0,
                        upload_date="",
                        uploader="",
                        view_count=0
                    ),
                    transcript=[],
                    error_log=[str(result)]
                )
                processed_results.append(error_content)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def export_content(self, content: VideoContent, format: str = "json", output_path: str = None) -> str:
        """Export processed content in various formats"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"video_content_{content.metadata.video_id}_{timestamp}"
        
        if format.lower() == "json":
            output_file = f"{output_path}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(content), f, indent=2, ensure_ascii=False, default=str)
        
        elif format.lower() == "markdown":
            output_file = f"{output_path}.md"
            markdown_content = self._generate_markdown(content)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        elif format.lower() == "csv":
            output_file = f"{output_path}.csv"
            df = pd.DataFrame([asdict(segment) for segment in content.transcript])
            df.to_csv(output_file, index=False)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Content exported to {output_file}")
        return output_file
    
    def _generate_markdown(self, content: VideoContent) -> str:
        """Generate markdown representation of video content"""
        md = f"""# {content.metadata.title}

## Video Information
- **Video ID**: {content.metadata.video_id}
- **Uploader**: {content.metadata.uploader}
- **Duration**: {content.metadata.duration // 60}:{content.metadata.duration % 60:02d}
- **Upload Date**: {content.metadata.upload_date}
- **Views**: {content.metadata.view_count:,}
- **Processing Time**: {content.processing_time:.2f}s

## Description
{content.metadata.description[:500]}...

## Summary
{content.summary or 'No summary available'}

## Key Points
"""
        
        if content.key_points:
            for point in content.key_points:
                md += f"- {point}\n"
        else:
            md += "No key points extracted.\n"
        
        md += "\n## Topics\n"
        if content.topics:
            md += ", ".join(content.topics)
        else:
            md += "No topics identified."
        
        md += f"\n\n## Sentiment\n{content.sentiment or 'Not analyzed'}\n"
        
        md += "\n## Transcript\n"
        for i, segment in enumerate(content.transcript):
            timestamp = f"{int(segment.start // 60)}:{int(segment.start % 60):02d}"
            md += f"**[{timestamp}]** {segment.text}\n\n"
        
        return md

# Example usage and testing
async def main():
    """Example usage of the enhanced video extractor"""
    
    # Initialize extractor
    extractor = EnhancedVideoExtractor()
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Compliance-safe test video
    
    try:
        # Process single video
        content = await extractor.process_video(test_url)
        
        # Export in different formats
        extractor.export_content(content, "json")
        extractor.export_content(content, "markdown")
        
        print(f"Successfully processed: {content.metadata.title}")
        print(f"Duration: {content.metadata.duration}s")
        print(f"Transcript segments: {len(content.transcript)}")
        
    except Exception as e:
        print(f"Processing failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())