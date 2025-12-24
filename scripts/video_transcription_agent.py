#!/usr/bin/env python3
"""
Video Transcription Agent
Specialized agent for extracting accurate transcripts from video content
with robust fallback mechanisms and quality validation.
"""

import re
import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import subprocess
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TranscriptSegment:
    """Represents a single transcript segment with timing information."""
    text: str
    start: float
    duration: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "duration": self.duration
        }

@dataclass
class VideoAnalysis:
    """Complete video analysis results."""
    video_id: str
    url: str
    title: Optional[str]
    duration: Optional[float]
    transcript: List[TranscriptSegment]
    language: str
    category: str
    key_topics: List[str]
    format_type: str
    audio_quality: str
    extraction_method: str
    processing_time: float
    success: bool
    error_message: Optional[str]

class VideoTranscriptionAgent:
    """
    Expert Video Transcription Agent with multi-method extraction
    and robust fallback mechanisms.
    """
    
    def __init__(self):
        self.youtube_transcript_api = None
        self.yt_dlp_available = False
        self._setup_dependencies()
    
    def _setup_dependencies(self):
        """Setup and verify dependencies."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.youtube_transcript_api = YouTubeTranscriptApi
            logger.info("YouTube Transcript API loaded successfully")
        except ImportError:
            logger.warning("YouTube Transcript API not available")
        
        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
            self.yt_dlp_available = True
            logger.info("yt-dlp available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("yt-dlp not available")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/live/([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _method_1_transcript_api(self, video_id: str) -> Tuple[Optional[List[Dict]], str]:
        """Primary method: Direct YouTube Transcript API extraction."""
        if not self.youtube_transcript_api:
            return None, "YouTube Transcript API not available"
        
        try:
            # Try auto-generated captions first
            transcript = self.youtube_transcript_api.get_transcript(video_id)
            return transcript, "transcript_api_auto"
        except Exception as e1:
            try:
                # Try manual captions
                transcript = self.youtube_transcript_api.get_transcript(video_id, languages=['en'])
                return transcript, "transcript_api_manual"
            except Exception as e2:
                try:
                    # Try all available languages
                    transcript_list = self.youtube_transcript_api.list_transcripts(video_id)
                    for transcript_info in transcript_list:
                        try:
                            transcript = transcript_info.fetch()
                            return transcript, f"transcript_api_{transcript_info.language_code}"
                        except:
                            continue
                except Exception as e3:
                    return None, f"All transcript API methods failed: {str(e3)}"
        
        return None, "No transcripts available via API"
    
    def _method_2_yt_dlp(self, video_id: str) -> Tuple[Optional[List[Dict]], str]:
        """Secondary method: yt-dlp fallback extraction."""
        if not self.yt_dlp_available:
            return None, "yt-dlp not available"
        
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Try to extract subtitles with yt-dlp
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--write-sub',
                '--sub-format', 'json3',
                '--skip-download',
                '--quiet',
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Look for generated subtitle files
                import glob
                import os
                
                subtitle_files = glob.glob(f"*.{video_id}*.json3")
                if subtitle_files:
                    with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                        subtitle_data = json.load(f)
                    
                    # Convert to transcript format
                    transcript = []
                    if 'events' in subtitle_data:
                        for event in subtitle_data['events']:
                            if 'segs' in event:
                                text = ''.join([seg.get('utf8', '') for seg in event['segs']])
                                if text.strip():
                                    transcript.append({
                                        'text': text.strip(),
                                        'start': event.get('tStartMs', 0) / 1000.0,
                                        'duration': event.get('dDurationMs', 0) / 1000.0
                                    })
                    
                    # Clean up downloaded files
                    for file in subtitle_files:
                        try:
                            os.remove(file)
                        except:
                            pass
                    
                    return transcript, "yt_dlp_subtitles"
            
            return None, f"yt-dlp failed: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            return None, "yt-dlp timeout"
        except Exception as e:
            return None, f"yt-dlp error: {str(e)}"
    
    def _validate_transcript(self, transcript: List[Dict]) -> bool:
        """Validate transcript quality and authenticity."""
        if not transcript:
            return False
        
        # Check minimum segment count
        if len(transcript) < 3:
            return False
        
        # Check minimum total content length
        total_text = ' '.join([seg.get('text', '') for seg in transcript])
        if len(total_text.strip()) < 50:
            return False
        
        # Check for proper timestamp formatting
        for seg in transcript:
            if 'start' not in seg or not isinstance(seg.get('start'), (int, float)):
                return False
            if seg.get('start', 0) < 0:
                return False
        
        return True
    
    def _analyze_content(self, transcript: List[TranscriptSegment], title: str = "") -> Dict[str, Any]:
        """Analyze transcript content for category, topics, and themes."""
        full_text = ' '.join([seg.text for seg in transcript]).lower()
        
        # Category detection based on keywords
        categories = {
            'education': ['learn', 'tutorial', 'explain', 'how to', 'lesson', 'teach', 'guide'],
            'entertainment': ['funny', 'comedy', 'laugh', 'entertainment', 'fun', 'joke'],
            'music': ['music', 'song', 'sing', 'album', 'artist', 'lyrics', 'beat'],
            'technology': ['tech', 'software', 'computer', 'app', 'code', 'programming'],
            'business': ['business', 'entrepreneur', 'money', 'invest', 'market', 'sales'],
            'cooking': ['cook', 'recipe', 'ingredient', 'kitchen', 'food', 'meal'],
            'fitness': ['workout', 'exercise', 'fitness', 'gym', 'health', 'training'],
            'gaming': ['game', 'gaming', 'play', 'player', 'level', 'boss', 'score'],
            'news': ['news', 'report', 'breaking', 'update', 'announce', 'recent'],
            'lifestyle': ['life', 'daily', 'routine', 'habit', 'personal', 'tips']
        }
        
        category_scores = {}
        for cat, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in full_text)
            if score > 0:
                category_scores[cat] = score
        
        detected_category = max(category_scores, key=category_scores.get) if category_scores else 'general'
        
        # Extract key topics (frequent meaningful words)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', full_text)
        word_freq = {}
        for word in words:
            if word not in ['this', 'that', 'with', 'have', 'will', 'they', 'them', 'were', 'been', 'from', 'what', 'when', 'where']:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        key_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        key_topics = [topic[0] for topic in key_topics]
        
        return {
            'category': detected_category,
            'key_topics': key_topics,
            'category_confidence': category_scores.get(detected_category, 0)
        }
    
    def _detect_format_type(self, url: str, duration: float = None) -> str:
        """Detect video format type based on URL and duration."""
        if '/shorts/' in url:
            return 'youtube_short'
        elif '/live/' in url:
            return 'live_stream'
        elif duration and duration > 3600:  # More than 1 hour
            return 'long_form'
        elif duration and duration < 300:  # Less than 5 minutes
            return 'short_form'
        else:
            return 'standard_video'
    
    def _assess_audio_quality(self, transcript: List[TranscriptSegment]) -> str:
        """Assess audio quality based on transcript characteristics."""
        if not transcript:
            return 'unknown'
        
        # Check for incomplete words or garbled text
        total_segments = len(transcript)
        garbled_count = 0
        
        for seg in transcript:
            text = seg.text.lower()
            # Look for signs of poor transcription
            if any(indicator in text for indicator in ['[inaudible]', '[music]', '???', '...']):
                garbled_count += 1
            # Check for very short segments (might indicate choppy audio)
            if len(text.strip()) < 10 and seg.duration < 1.0:
                garbled_count += 1
        
        garbled_ratio = garbled_count / total_segments if total_segments > 0 else 1
        
        if garbled_ratio < 0.1:
            return 'high'
        elif garbled_ratio < 0.3:
            return 'medium'
        else:
            return 'low'
    
    def process_video(self, url: str) -> VideoAnalysis:
        """
        Process a single video URL and extract comprehensive analysis.
        """
        start_time = time.time()
        
        # Extract video ID
        video_id = self.extract_video_id(url)
        if not video_id:
            return VideoAnalysis(
                video_id="",
                url=url,
                title=None,
                duration=None,
                transcript=[],
                language="unknown",
                category="unknown",
                key_topics=[],
                format_type="unknown",
                audio_quality="unknown",
                extraction_method="none",
                processing_time=time.time() - start_time,
                success=False,
                error_message="Could not extract video ID from URL"
            )
        
        logger.info(f"Processing video ID: {video_id}")
        
        # Try extraction methods in order
        raw_transcript = None
        extraction_method = "none"
        
        # Method 1: YouTube Transcript API
        logger.info("Attempting Method 1: YouTube Transcript API")
        raw_transcript, method_result = self._method_1_transcript_api(video_id)
        if raw_transcript and self._validate_transcript(raw_transcript):
            extraction_method = method_result
            logger.info(f"Success with Method 1: {method_result}")
        else:
            logger.info(f"Method 1 failed: {method_result}")
            
            # Method 2: yt-dlp fallback
            logger.info("Attempting Method 2: yt-dlp fallback")
            raw_transcript, method_result = self._method_2_yt_dlp(video_id)
            if raw_transcript and self._validate_transcript(raw_transcript):
                extraction_method = method_result
                logger.info(f"Success with Method 2: {method_result}")
            else:
                logger.info(f"Method 2 failed: {method_result}")
        
        # Process results
        if not raw_transcript or not self._validate_transcript(raw_transcript):
            return VideoAnalysis(
                video_id=video_id,
                url=url,
                title=None,
                duration=None,
                transcript=[],
                language="unknown",
                category="unknown",
                key_topics=[],
                format_type=self._detect_format_type(url),
                audio_quality="unknown",
                extraction_method=extraction_method,
                processing_time=time.time() - start_time,
                success=False,
                error_message="No valid transcript could be extracted"
            )
        
        # Convert to TranscriptSegment objects
        transcript_segments = []
        for seg in raw_transcript:
            transcript_segments.append(TranscriptSegment(
                text=seg.get('text', ''),
                start=float(seg.get('start', 0)),
                duration=float(seg.get('duration', 0))
            ))
        
        # Calculate total duration
        total_duration = max([seg.start + seg.duration for seg in transcript_segments]) if transcript_segments else 0
        
        # Analyze content
        content_analysis = self._analyze_content(transcript_segments)
        
        processing_time = time.time() - start_time
        
        return VideoAnalysis(
            video_id=video_id,
            url=url,
            title=None,  # Would need additional API call to get title
            duration=total_duration,
            transcript=transcript_segments,
            language="auto-detected",  # Would need language detection
            category=content_analysis['category'],
            key_topics=content_analysis['key_topics'],
            format_type=self._detect_format_type(url, total_duration),
            audio_quality=self._assess_audio_quality(transcript_segments),
            extraction_method=extraction_method,
            processing_time=processing_time,
            success=True,
            error_message=None
        )
    
    def process_multiple_videos(self, urls: List[str]) -> List[VideoAnalysis]:
        """Process multiple videos and return comprehensive analysis."""
        results = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing video {i}/{len(urls)}: {url}")
            result = self.process_video(url)
            results.append(result)
            
            # Add delay between requests to be respectful
            if i < len(urls):
                time.sleep(1)
        
        return results

def main():
    """Main function for testing the transcription agent."""
    agent = VideoTranscriptionAgent()
    
    # Test URLs
    test_urls = [
        "https://youtube.com/shorts/Z1XHeMgpg8A?si=W3ONafWfPrmftWmc",
        "https://youtu.be/w9u11ioHGA0?si=_cdEFmWmNkWByxR2",
        "https://www.youtube.com/live/pRpBIQwaMIw?si=tyYR9V_taaCrzi3a"
    ]
    
    print("🎬 Video Transcription Agent - Processing Videos...")
    print("=" * 60)
    
    results = agent.process_multiple_videos(test_urls)
    
    for i, result in enumerate(results, 1):
        print(f"\n📹 VIDEO {i}: {result.format_type.upper()}")
        print(f"URL: {result.url}")
        print(f"Video ID: {result.video_id}")
        print(f"Success: {'✅' if result.success else '❌'}")
        
        if result.success:
            print(f"Duration: {result.duration:.1f} seconds")
            print(f"Category: {result.category}")
            print(f"Key Topics: {', '.join(result.key_topics[:5])}")
            print(f"Audio Quality: {result.audio_quality}")
            print(f"Extraction Method: {result.extraction_method}")
            print(f"Processing Time: {result.processing_time:.2f}s")
            print(f"Transcript Segments: {len(result.transcript)}")
            
            if result.transcript:
                print("\n📝 Sample Transcript (first 3 segments):")
                for seg in result.transcript[:3]:
                    print(f"  [{seg.start:.1f}s] {seg.text[:100]}...")
        else:
            print(f"Error: {result.error_message}")
        
        print("-" * 60)

if __name__ == "__main__":
    main()